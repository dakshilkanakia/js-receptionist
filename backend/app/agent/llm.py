from loguru import logger
from pipecat.frames.frames import TTSSpeakFrame
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.services.openrouter.llm import OpenRouterLLMService

TRUNCATED_FALLBACK = "Sorry, I missed that. Could you say it again?"


class GuardedOpenRouterLLMService(OpenRouterLLMService):
    """OpenRouter LLM that never leaves the caller in silence after a cut-off reply.

    If a response stops because it hit the output token cap (finish_reason "length"),
    a half-written tool call can't run and nothing gets said. We log it loudly and
    ask the caller to repeat instead.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._finish_reason: str | None = None

    async def get_chat_completions(self, context: LLMContext):
        stream = await super().get_chat_completions(context)

        async def tracked():
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].finish_reason:
                    self._finish_reason = chunk.choices[0].finish_reason
                yield chunk

        return tracked()

    async def _process_context(self, context: LLMContext):
        self._finish_reason = None
        await super()._process_context(context)
        if self._finish_reason == "length":
            logger.warning(f"{self}: reply hit the output token cap and was cut off; asking caller to repeat")
            await self.push_frame(TTSSpeakFrame(TRUNCATED_FALLBACK))
