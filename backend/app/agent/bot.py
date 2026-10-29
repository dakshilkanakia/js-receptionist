"""Voice pipeline for one call: mic audio -> STT -> LLM -> TTS -> speaker audio."""

from fastapi import WebSocket
from loguru import logger
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.frames.frames import LLMRunFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.worker import PipelineParams, PipelineWorker
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import (
    LLMContextAggregatorPair,
    LLMUserAggregatorParams,
)
from pipecat.serializers.protobuf import ProtobufFrameSerializer
from pipecat.services.deepgram.stt import DeepgramSTTService
from pipecat.services.deepgram.tts import DeepgramTTSService
from pipecat.services.openrouter.llm import OpenRouterLLMService
from pipecat.transports.websocket.fastapi import (
    FastAPIWebsocketParams,
    FastAPIWebsocketTransport,
)
from pipecat.workers.runner import WorkerRunner

from app.config import settings

# Day 1 spike prompt. Replaced on Day 2 by facts loaded from the database.
SPIKE_PROMPT = """You are the AI phone receptionist for J's Cleaners, a dry cleaner in New York City.
Your words are spoken aloud: keep replies to one or two short sentences, no lists, no symbols.
Always be honest that you are an AI.
Facts: Pants start at $13.45. A shirt on a hanger starts at $4.95. Usual turnaround is about 2 days.
If you don't know something, say you aren't sure and offer to have someone call back."""

GREETING_INSTRUCTION = (
    "Greet the caller: say you're J's Cleaners' AI assistant, that the call is transcribed, "
    "and ask how you can help. One or two sentences."
)


async def run_call(websocket: WebSocket) -> None:
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
    llm = OpenRouterLLMService(
        api_key=settings.openrouter_api_key,
        # Cap output: voice replies are short, and OpenRouter reserves credit for the
        # model's full max output (65k on Haiku) when no cap is sent.
        settings=OpenRouterLLMService.Settings(
            model=settings.llm_model, max_completion_tokens=300
        ),
    )
    tts = DeepgramTTSService(
        api_key=settings.deepgram_api_key,
        settings=DeepgramTTSService.Settings(voice=settings.tts_voice),
    )

    context = LLMContext(messages=[{"role": "system", "content": SPIKE_PROMPT}])
    user_aggregator, assistant_aggregator = LLMContextAggregatorPair(
        context,
        user_params=LLMUserAggregatorParams(vad_analyzer=SileroVADAnalyzer()),
    )

    pipeline = Pipeline(
        [
            transport.input(),
            stt,
            user_aggregator,
            llm,
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
        context.add_message({"role": "user", "content": GREETING_INSTRUCTION})
        await worker.queue_frames([LLMRunFrame()])

    @user_aggregator.event_handler("on_user_turn_stopped")
    async def on_user_turn_stopped(aggregator, strategy, message):
        logger.info(f"USER: {message.content}")

    @assistant_aggregator.event_handler("on_assistant_turn_stopped")
    async def on_assistant_turn_stopped(aggregator, message):
        logger.info(f"AGENT: {message.content}")

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        logger.info("Caller hung up")
        await runner.cancel()

    @transport.event_handler("on_session_timeout")
    async def on_session_timeout(transport, client):
        logger.info("Max call length reached")
        await runner.cancel()

    await runner.run()
