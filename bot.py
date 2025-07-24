#
# Copyright (c) 2025, Daily
#
# SPDX-License-Identifier: BSD 2-Clause License
#

import os
import sys

import aiohttp
from dotenv import load_dotenv
from loguru import logger
from pipecat.adapters.schemas.tools_schema import ToolsSchema
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.pipeline.parallel_pipeline import ParallelPipeline
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.services.aws.llm import AWSBedrockLLMService
from pipecat.services.deepgram.stt import DeepgramSTTService, LiveOptions
from pipecat.services.deepgram.tts import DeepgramTTSService
from pipecat.services.llm_service import FunctionCallParams
from pipecat.transcriptions.language import Language
from pipecat.transports.services.daily import DailyParams, DailyTransport
from pipecatcloud.agent import DailySessionArguments

from strands_agent import StrandsAgentProcessor, StrandsAgentRequestFrame

# Load environment variables
load_dotenv(override=True)
logger.add(sys.stderr, level="DEBUG")

# Check if we're in local development mode
LOCAL_RUN = os.getenv("LOCAL_RUN")
if LOCAL_RUN:
    import asyncio
    import webbrowser

    try:
        from local_runner import configure
    except ImportError:
        logger.error(
            "Could not import local_runner module. Local development mode may not work."
        )


async def main(transport: DailyTransport):
    """Main pipeline setup and execution function.

    Args:
        transport: The DailyTransport instance
    """

    stt = DeepgramSTTService(
        api_key=os.getenv("DEEPGRAM_API_KEY"),
        live_options=LiveOptions(
            model="nova-3-general", language=Language.EN, smart_format=True
        ),
    )

    main_tts = DeepgramTTSService(
        api_key=os.getenv("DEEPGRAM_API_KEY"),
        voice="aura-2-arcas-en",
        sample_rate=24000,
        encoding="linear16",
    )

    specialist_tts = DeepgramTTSService(
        api_key=os.getenv("DEEPGRAM_API_KEY"),
        voice="aura-2-andromeda-en",
        sample_rate=24000,
        encoding="linear16",
    )

    llm = AWSBedrockLLMService(
        aws_region="us-west-2",
        model="us.anthropic.claude-3-7-sonnet-20250219-v1:0",
    )

    messages = [
        {
            "role": "system",
            "content": "You are a helpful LLM in a WebRTC call. Your goal is to demonstrate your capabilities in a succinct way. Your output will be converted to audio so don't include special characters in your answers. Respond to what the user said in a creative and helpful way. Keep your responses VERY BRIEF. Brevity is the soul of wit. When making function calls, respond with only the function call block and no explanatory text, commentary, or narration. Do not announce what you're doing or explain why you're calling the function. Just say exactly this: 'one sec'.",
        },
    ]

    async def handle_weather_questions(params: FunctionCallParams, query: str):
        """
        Call this function if the user asks a question about the weather.

        Args:
            query (str): The user's query, e.g. "What's the weather where the Golden Gate Bridge is?".
        """

        logger.info(f"!!! handle_weather_questions: {query}")
        # Run in a background thread
        # (Otherwise the agent blocks the event loop; one effect of that is that we don't hear
        # "let me check on that" until the agent finishes)
        # loop = asyncio.get_running_loop()
        # result = await loop.run_in_executor(None, strands_agent, query)
        await strands_agent_processor.queue_frame(StrandsAgentRequestFrame(query))
        # This return result isn't "magic"; the LLM is smart enough to interpret it as something
        # to say to the user
        await params.result_callback(
            {"message": "Tell the user that the specialist will answer the question."}
        )

    llm.register_direct_function(handle_weather_questions)
    tools = ToolsSchema(standard_tools=[handle_weather_questions])

    context = OpenAILLMContext(messages, tools)
    context_aggregator = llm.create_context_aggregator(context)

    strands_agent_processor = StrandsAgentProcessor()

    pipeline = Pipeline(
        [
            ParallelPipeline(
                [
                    transport.input(),
                    stt,
                    context_aggregator.user(),
                    llm,
                    main_tts,
                ],
                [
                    strands_agent_processor,
                    specialist_tts,
                ],
            ),
            transport.output(),
            context_aggregator.assistant(),
        ]
    )

    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            allow_interruptions=True,
            enable_metrics=True,
            enable_usage_metrics=True,
            report_only_initial_ttfb=True,
        ),
    )

    @transport.event_handler("on_first_participant_joined")
    async def on_first_participant_joined(transport, participant):
        logger.info("First participant joined: {}", participant["id"])
        await transport.capture_participant_transcription(participant["id"])
        # Kick off the conversation. Claude wants a user frame first.
        messages.append(
            {
                "role": "user",
                "content": "Please say exactly this: 'Hello World! What can I do for you?'",
            }
        )
        await task.queue_frames([context_aggregator.user().get_context_frame()])

    @transport.event_handler("on_participant_left")
    async def on_participant_left(transport, participant, reason):
        logger.info("Participant left: {}", participant)
        await task.cancel()

    runner = PipelineRunner(handle_sigint=False, force_gc=True)

    await runner.run(task)


async def bot(args: DailySessionArguments):
    """Main bot entry point compatible with the FastAPI route handler.

    Args:
        room_url: The Daily room URL
        token: The Daily room token
        body: The configuration object from the request body
        session_id: The session ID for logging
    """
    logger.info(f"Bot process initialized {args.room_url} {args.token}")

    transport = DailyTransport(
        args.room_url,
        args.token,
        "Pipecat Bot",
        DailyParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            enable_transcription=False,
            vad_analyzer=SileroVADAnalyzer(),
        ),
    )

    try:
        await main(transport)
        logger.info("Bot process completed")
    except Exception as e:
        logger.exception(f"Error in bot process: {str(e)}")
        raise


# Local development
async def local_daily():
    """Daily transport for local development."""

    try:
        async with aiohttp.ClientSession() as session:
            (room_url, token) = await configure(session)
            transport = DailyTransport(
                room_url,
                token,
                "Pipecat Local Bot",
                params=DailyParams(
                    audio_in_enabled=True,
                    audio_out_enabled=True,
                    transcription_enabled=True,
                    vad_analyzer=SileroVADAnalyzer(),
                ),
            )

            logger.warning(f"Talk to your voice agent here: {room_url}")
            webbrowser.open(room_url)

            await main(transport)
    except Exception as e:
        logger.exception(f"Error in local development mode: {e}")


# Local development entry point
if LOCAL_RUN and __name__ == "__main__":
    try:
        asyncio.run(local_daily())
    except Exception as e:
        logger.exception(f"Failed to run in local mode: {e}")
