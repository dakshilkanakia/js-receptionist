from pipecat.frames.frames import Frame, LLMFullResponseStartFrame, LLMTextFrame
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor


class SpeechTracker(FrameProcessor):
    """Remembers whether the current LLM response already contained spoken text.

    When the model says something and calls a tool in the same response, asking it
    to respond again after the tool result makes it repeat itself. Tool handlers
    check `spoke_this_response` to skip that second response.
    """

    def __init__(self):
        super().__init__()
        self.spoke_this_response = False

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)
        if isinstance(frame, LLMFullResponseStartFrame):
            self.spoke_this_response = False
        elif isinstance(frame, LLMTextFrame) and frame.text.strip():
            self.spoke_this_response = True
        await self.push_frame(frame, direction)
