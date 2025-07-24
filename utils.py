import asyncio
from pipecat.frames.frames import Frame, TextFrame, TTSSpeakFrame
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
from loguru import logger

# Import for the OpenAILLMContextFrame used in GreetingProcessor
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContextFrame

# Define the LLM response frames if they're not already defined in the imported libraries
class LLMFullResponseStartFrame(Frame):
    """Frame indicating the start of a full LLM response."""
    pass

class LLMFullResponseEndFrame(Frame):
    """Frame indicating the end of a full LLM response."""
    pass

class GreetingProcessor(FrameProcessor):
    def __init__(self, greeting: str):
        super().__init__()
        self._greeting = greeting
        self._greeted = False

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)
        # Only gate downstream frames
        if direction != FrameDirection.DOWNSTREAM:
            await self.push_frame(frame, direction)
            return

        if self._greeted:
            await self.push_frame(frame, direction)
        else:
            # Catch the first context frame we get from the aggregator.
            # Don't let it continue down the pipeline and trigger a
            # completion; instead, tell TTS to say the predefined greeting
            if isinstance(frame, OpenAILLMContextFrame):
                logger.debug(f"!!! greeting processor got a context frame: {frame}")
                self._greeted = True
                tts_speak_frame = TTSSpeakFrame(text=self._greeting)
                await self.push_frame(tts_speak_frame, direction)
            else:
                await self.push_frame(frame, direction)


class TTSLockAcquireProcessor(FrameProcessor):
    """FrameProcessor that acquires a lock when it sees a LLMFullResponseStartFrame."""
    
    def __init__(self, lock: asyncio.Lock):
        super().__init__()
        self._lock = lock
        
    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)
        
        # Acquire the lock when we see a LLMFullResponseStartFrame
        if isinstance(frame, LLMFullResponseStartFrame):
            logger.debug("TTSLockAcquireProcessor: Acquiring lock")
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
            logger.debug("TTSLockReleaseProcessor: Releasing lock")
            if self._lock.locked():
                self._lock.release()
            
        # Always pass the frame through
        await self.push_frame(frame, direction)

