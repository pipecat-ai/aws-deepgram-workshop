import asyncio
from dataclasses import dataclass

from loguru import logger
from pipecat.frames.frames import Frame, TextFrame, TTSSpeakFrame
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
from pipecat.processors.frameworks.rtvi import RTVIServerMessageFrame
from strands import Agent, tool
from strands.models import BedrockModel


@dataclass
class StrandsAgentRequestFrame(TextFrame):
    pass


class StrandsThinkingTextFrame:
    text: str


class StrandsAgentProcessor(FrameProcessor):
    def __init__(self):
        super().__init__()
        self.agent = Agent(
            model=BedrockModel(
                model_id="us.anthropic.claude-3-7-sonnet-20250219-v1:0",
                max_tokens=64000,
            ),
            tools=[
                self.get_location_name_from_landmark,
                self.get_lat_long_from_location_name,
                self.get_current_weather_from_lat_long,
            ],
            system_prompt="""
            You are a helpful personal assistant who can look up information about places and weather.

            Your key capabilities:
            1. Look up where landmarks are located.
            2. Find latitude and longitude for a location.
            3. Look up the current weather for a specific latitude and longitude.

            Explain each step of your reasoning in clear, simple, and concise language. Your responses will be converted to audio, so avoid special characters and numbered lists.
            """,
            callback_handler=self.strands_callback_handler,
        )
        self._next_strands_message_is_last = False
        self._strands_messages_queue = asyncio.Queue()
        asyncio.create_task(self.process_strands_messages())

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)
        if isinstance(frame, StrandsAgentRequestFrame):
            logger.debug(f"!!! got a request frame: {frame}")
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(None, self.agent, frame.text)
            logger.info(f"!!! agent result: {result}")
            await self.push_frame(TTSSpeakFrame(result.message["content"][0]["text"]))

        else:
            await self.push_frame(frame, direction)

    @tool
    def get_location_name_from_landmark(self, landmark: str) -> str:
        """
        Get the location name from a landmark.

        Args:
            landmark (str): The name of the landmark, e.g. "Golden Gate Bridge".
        """
        # Simulate fetching location
        return "San Francisco, CA"

    @tool
    def get_lat_long_from_location_name(self, location: str) -> dict:
        """
        Get the latitude and longitude for a location name.

        Args:
            location (str): The city and state, e.g. "San Francisco, CA".
        """
        # Simulate fetching lat/long from a geocoding service
        return {"lat": 37.7749, "long": -122.4194}

    @tool
    def get_current_weather_from_lat_long(self, lat: float, long: float) -> dict:
        """
        Get the current weather for a specific latitude and longitude.

        Args:
            lat (float): The latitude of the location.
            long (float): The longitude of the location.
        """
        # Simulate fetching weather data from a weather service
        return {"conditions": "nice", "temperature": "75"}

    def strands_callback_handler(self, **kwargs):
        """
        Handle events from the Strands agent.
        """
        logger.debug(f"Strands callback handler: {kwargs}")

        if "event" in kwargs:
            event_obj = kwargs["event"]
            if event_obj and "messageStop" in event_obj:
                message_stop = event_obj["messageStop"]
                if message_stop and "stopReason" in message_stop:
                    stop_reason = message_stop["stopReason"]
                    if stop_reason == "end_turn":
                        self._next_strands_message_is_last = True
        elif "message" in kwargs:
            message_obj = kwargs["message"]
            if message_obj and "content" in message_obj and "role" in message_obj:
                role = message_obj["role"]
                content = message_obj["content"]
                if role == "assistant" and isinstance(content, list):
                    for content_obj in content:
                        if isinstance(content_obj, dict) and "text" in content_obj:
                            message = content_obj["text"]
                            if not self._next_strands_message_is_last:
                                self._strands_messages_queue.put_nowait(message)

    async def process_strands_messages(self):
        while True:
            message = await self._strands_messages_queue.get()
            # await self.push_frame(StrandsThinkingTextFrame(message))
            await self.push_frame(
                RTVIServerMessageFrame(
                    data={"type": "specialist-thinking", "message": message}
                )
            )
            self._strands_messages_queue.task_done()
