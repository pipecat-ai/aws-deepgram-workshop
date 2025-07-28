import asyncio

from loguru import logger
from pipecat.frames.frames import (
    Frame,
    LLMFullResponseEndFrame,
    LLMFullResponseStartFrame,
)

# Import for the OpenAILLMContextFrame used in GreetingProcessor
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor


class TTSLockAcquireProcessor(FrameProcessor):
    """FrameProcessor that acquires a lock when it sees a LLMFullResponseStartFrame."""

    def __init__(self, lock: asyncio.Lock):
        super().__init__()
        self._lock = lock

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)

        # Acquire the lock when we see a LLMFullResponseStartFrame
        if isinstance(frame, LLMFullResponseStartFrame):
            logger.debug("!!! TTSLockAcquireProcessor: Acquiring lock")
            await self._lock.acquire()

        # Always pass the frame through
        await self.push_frame(frame, direction)


class TTSLockReleaseProcessor(FrameProcessor):
    """FrameProcessor that releases a lock when it sees a LLMFullResponseEndFrame."""

    def __init__(self, lock: asyncio.Lock):
        super().__init__()
        self._lock = lock

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)

        # Release the lock when we see a LLMFullResponseEndFrame
        if isinstance(frame, LLMFullResponseEndFrame):
            logger.debug("!!! TTSLockReleaseProcessor: Releasing lock")
            if self._lock.locked():
                self._lock.release()

        # Always pass the frame through
        await self.push_frame(frame, direction)
