"""The guard must speak a fallback when a reply is cut off by the token cap."""

import pytest
from openai.types.chat import ChatCompletionChunk
from pipecat.frames.frames import TTSSpeakFrame
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.services.openrouter.llm import OpenRouterLLMService

from app.agent.llm import TRUNCATED_FALLBACK, GuardedOpenRouterLLMService


def chunk(finish_reason=None, args=None, name=None):
    tool_calls = None
    if args is not None or name is not None:
        tool_calls = [{"index": 0, "id": "t1" if name else None, "type": "function",
                       "function": {"name": name, "arguments": args}}]
    return ChatCompletionChunk.model_validate({
        "id": "c", "object": "chat.completion.chunk", "created": 0, "model": "m",
        "choices": [{"index": 0, "delta": {"tool_calls": tool_calls}, "finish_reason": finish_reason}],
    })


async def fake_stream(chunks):
    for c in chunks:
        yield c


@pytest.mark.parametrize(
    "chunks, expect_fallback",
    [
        # Cut off mid tool-call arguments, like the real call #5 failure.
        ([chunk(name="save_callback", args='{"first_name": "Ro'), chunk(finish_reason="length")], True),
        # Normal completed response: no fallback.
        ([chunk(name="end_call", args="{}"), chunk(finish_reason="tool_calls")], False),
    ],
)
async def test_fallback_on_truncation(monkeypatch, chunks, expect_fallback):
    async def fake_get(self, context):
        return fake_stream(chunks)

    monkeypatch.setattr(OpenRouterLLMService, "get_chat_completions", fake_get)
    llm = GuardedOpenRouterLLMService(api_key="test")
    pushed = []

    async def capture(frame, direction=None):
        pushed.append(frame)

    async def no_calls(calls):
        pass

    monkeypatch.setattr(llm, "push_frame", capture)
    monkeypatch.setattr(llm, "run_function_calls", no_calls)
    await llm._process_context(LLMContext())

    spoken = [f.text for f in pushed if isinstance(f, TTSSpeakFrame)]
    assert (spoken == [TRUNCATED_FALLBACK]) is expect_fallback
