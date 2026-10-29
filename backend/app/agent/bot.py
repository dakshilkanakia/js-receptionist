"""Voice pipeline for one call: mic audio -> STT -> LLM -> TTS -> speaker audio."""

import aiohttp
from fastapi import WebSocket
from loguru import logger
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.frames.frames import TTSSpeakFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.worker import PipelineParams, PipelineWorker
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import (
    LLMContextAggregatorPair,
    LLMUserAggregatorParams,
)
from pipecat.serializers.protobuf import ProtobufFrameSerializer
from pipecat.services.deepgram.stt import DeepgramSTTService
from pipecat.services.deepgram.tts import DeepgramHttpTTSService
from pipecat.turns.user_mute.mute_until_first_bot_complete_user_mute_strategy import (
    MuteUntilFirstBotCompleteUserMuteStrategy,
)
from pipecat.transports.websocket.fastapi import (
    FastAPIWebsocketParams,
    FastAPIWebsocketTransport,
)
from pipecat.turns.user_start.min_words_user_turn_start_strategy import (
    MinWordsUserTurnStartStrategy,
)
from pipecat.turns.user_turn_strategies import UserTurnStrategies
from pipecat.workers.runner import WorkerRunner

from app.agent.llm import GuardedOpenRouterLLMService
from app.agent.prompt import GREETING, build_system_prompt
from app.agent.recorder import CallRecorder
from app.agent.speech_tracker import SpeechTracker
from app.agent.tools import build_tools, register_tools
from app.config import settings
from app.facts.hours import now_in
from app.facts.schema import Facts

# Reasoning off: replies are short and tools do the hard parts. With reasoning on,
# OpenRouter let Haiku spend most of the output budget thinking, which truncated a
# tool call mid-argument and left the caller in silence (and doubled latency).
LLM_EXTRA_BODY = {"reasoning": {"enabled": False}}
LLM_MAX_TOKENS = 1024


async def run_call(websocket: WebSocket, call_id: int, facts: Facts) -> None:
    rec = CallRecorder(call_id)
    transport = FastAPIWebsocketTransport(
        websocket=websocket,
        params=FastAPIWebsocketParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            add_wav_header=False,
            serializer=ProtobufFrameSerializer(),
            session_timeout=settings.max_call_seconds,
            allowed_origins=settings.allowed_origins,
        ),
    )

    stt = DeepgramSTTService(api_key=settings.deepgram_api_key)
    llm = GuardedOpenRouterLLMService(
        api_key=settings.openrouter_api_key,
        # Cap output: voice replies are short, and OpenRouter reserves credit for the
        # model's full max output (65k on Haiku) when no cap is sent.
        settings=GuardedOpenRouterLLMService.Settings(
            model=settings.llm_model,
            max_completion_tokens=LLM_MAX_TOKENS,
            extra={"extra_body": LLM_EXTRA_BODY},
        ),
    )
    # HTTP, not WebSocket, TTS: the WebSocket service queues each sentence's text
    # before its audio arrives, so after an interruption the LLM context held whole
    # sentences the caller never heard (e.g. a price total). The HTTP service streams
    # a sentence's audio first and its text after, so context matches what was heard.
    http = aiohttp.ClientSession()
    tts = DeepgramHttpTTSService(
        api_key=settings.deepgram_api_key,
        aiohttp_session=http,
        settings=DeepgramHttpTTSService.Settings(voice=settings.tts_voice),
    )

    speech = SpeechTracker()
    register_tools(llm, facts, rec, speech)
    system_prompt = build_system_prompt(facts, now_in(facts.business.timezone))
    context = LLMContext(
        messages=[{"role": "system", "content": system_prompt}],
        tools=build_tools(facts),
    )
    user_aggregator, assistant_aggregator = LLMContextAggregatorPair(
        context,
        user_params=LLMUserAggregatorParams(
            vad_analyzer=SileroVADAnalyzer(),
            # The greeting carries the AI + transcription notice and the opt-out, so the
            # caller can't interrupt it. Every later turn stays interruptible.
            user_mute_strategies=[MuteUntilFirstBotCompleteUserMuteStrategy()],
            # While Jenny is talking, it takes 3+ words to interrupt her, so "mhm",
            # "okay" or "yeah" let her finish. When she's silent, one word starts a turn.
            user_turn_strategies=UserTurnStrategies(
                start=[MinWordsUserTurnStartStrategy(min_words=3)]
            ),
        ),
    )

    pipeline = Pipeline(
        [
            transport.input(),
            stt,
            user_aggregator,
            llm,
            speech,
            tts,
            transport.output(),
            assistant_aggregator,
        ]
    )

    worker = PipelineWorker(
        pipeline,
        params=PipelineParams(enable_metrics=True, enable_usage_metrics=True),
    )
    runner = WorkerRunner(handle_sigint=False)
    await runner.add_workers(worker)

    @worker.rtvi.event_handler("on_client_ready")
    async def on_client_ready(rtvi):
        # Fixed greeting (not LLM-generated) so the AI + transcription notice is always said.
        await worker.queue_frames([TTSSpeakFrame(GREETING)])

    @user_aggregator.event_handler("on_user_turn_stopped")
    async def on_user_turn_stopped(aggregator, strategy, message):
        logger.info(f"call {call_id} USER: {message.content}")
        await rec.add_turn("user", message.content)

    @assistant_aggregator.event_handler("on_assistant_turn_stopped")
    async def on_assistant_turn_stopped(aggregator, message):
        logger.info(f"call {call_id} AGENT: {message.content}")
        await rec.add_turn("assistant", message.content, interrupted=message.interrupted)

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        logger.info("Caller hung up")
        await runner.cancel()

    @transport.event_handler("on_session_timeout")
    async def on_session_timeout(transport, client):
        logger.info("Max call length reached")
        await runner.cancel()

    try:
        await runner.run()
    finally:
        await rec.finalize()
        await http.close()
