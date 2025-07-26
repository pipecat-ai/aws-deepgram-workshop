#
# Copyright (c) 2025, Daily
#
# SPDX-License-Identifier: BSD 2-Clause License
#

import os

from dotenv import load_dotenv
from loguru import logger
from pipecat.adapters.schemas.tools_schema import ToolsSchema
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.processors.frameworks.rtvi import RTVIConfig, RTVIObserver, RTVIProcessor
from pipecat.services.aws.llm import AWSBedrockLLMService
from pipecat.services.deepgram.stt import DeepgramSTTService, LiveOptions
from pipecat.services.deepgram.tts import DeepgramTTSService
from pipecat.services.llm_service import FunctionCallParams
from pipecat.transcriptions.language import Language

# Load environment variables
load_dotenv(override=True)


async def run_bot_logic(transport, handle_sigint: bool = True):
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

    tts = DeepgramTTSService(
        api_key=os.getenv("DEEPGRAM_API_KEY"),
        voice="aura-2-arcas-en",
        sample_rate=24000,
        encoding="linear16",
    )

    llm = AWSBedrockLLMService(
        aws_region="us-west-2",
        model="anthropic.claude-3-5-haiku-20241022-v1:0",
    )

    rtvi = RTVIProcessor(config=RTVIConfig(config=[]))

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
        # This return result isn't "magic"; the LLM is smart enough to interpret it as something
        # to say to the user
        await params.result_callback(
            {
                "message": "Tell the user that you don't have access to a weather API, so to you, the weather is always 75 and sunny."
            }
        )

    llm.register_direct_function(handle_weather_questions)
    tools = ToolsSchema(standard_tools=[handle_weather_questions])

    context = OpenAILLMContext(messages, tools)
    context_aggregator = llm.create_context_aggregator(context)

    pipeline = Pipeline(
        [
            transport.input(),
            rtvi,
            stt,
            context_aggregator.user(),
            llm,
            tts,
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
            observers=[RTVIObserver(rtvi)],
        ),
    )

    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, participant):
        logger.info("First participant joined: {}", participant)
        # await transport.capture_participant_transcription(participant["id"])
        # Kick off the conversation. Claude wants a user frame first.
        messages.append(
            {
                "role": "user",
                "content": "Please say exactly this: 'Hello World! What can I do for you?'",
            }
        )
        await task.queue_frames([context_aggregator.user().get_context_frame()])

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, participant):
        logger.info("Participant left: {}", participant)
        await task.cancel()

    runner = PipelineRunner(handle_sigint=handle_sigint, force_gc=True)

    await runner.run(task)


async def bot(session_args):
    """Main bot entry point compatible with Pipecat Cloud."""

    # Get handle_sigint from session_args, default to True for Daily
    handle_sigint = getattr(session_args, "handle_sigint", True)

    if hasattr(session_args, "room_url") and hasattr(session_args, "token"):
        # Daily session arguments (cloud or local)
        from pipecat.transports.services.daily import DailyParams, DailyTransport

        transport = DailyTransport(
            session_args.room_url,
            session_args.token,
            "Pipecat Bot",
            params=DailyParams(
                audio_in_enabled=True,
                audio_out_enabled=True,
                vad_analyzer=SileroVADAnalyzer(),
            ),
        )

    elif hasattr(session_args, "webrtc_connection"):
        # WebRTC session arguments (local only, created by server.py)
        from pipecat.transports.base_transport import TransportParams
        from pipecat.transports.network.small_webrtc import SmallWebRTCTransport

        transport = SmallWebRTCTransport(
            params=TransportParams(
                audio_in_enabled=True,
                audio_out_enabled=True,
                vad_analyzer=SileroVADAnalyzer(),
            ),
            webrtc_connection=session_args.webrtc_connection,
        )

    elif hasattr(session_args, "websocket"):
        # WebSocket session arguments (for telephony providers)
        from pipecat.transports.network.fastapi_websocket import (
            FastAPIWebsocketParams,
            FastAPIWebsocketTransport,
        )

        # Create appropriate serializer based on transport type
        params = FastAPIWebsocketParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            vad_analyzer=SileroVADAnalyzer(),
            add_wav_header=False,
        )

        if session_args.transport_type == "twilio":
            from pipecat.serializers.twilio import TwilioFrameSerializer

            call_info = session_args.call_info
            params.serializer = TwilioFrameSerializer(
                stream_sid=call_info["stream_sid"],
                call_sid=call_info["call_sid"],
                account_sid=os.getenv("TWILIO_ACCOUNT_SID", ""),
                auth_token=os.getenv("TWILIO_AUTH_TOKEN", ""),
            )
        elif session_args.transport_type == "telnyx":
            from pipecat.serializers.telnyx import TelnyxFrameSerializer

            call_info = session_args.call_info
            params.serializer = TelnyxFrameSerializer(
                stream_id=call_info["stream_id"],
                call_control_id=call_info["call_control_id"],
                outbound_encoding=call_info["outbound_encoding"],
                inbound_encoding="PCMU",
            )
        elif session_args.transport_type == "plivo":
            from pipecat.serializers.plivo import PlivoFrameSerializer

            call_info = session_args.call_info
            params.serializer = PlivoFrameSerializer(
                stream_id=call_info["stream_id"],
                call_id=call_info["call_id"],
            )
        else:
            raise ValueError(
                f"Unsupported WebSocket transport type: {session_args.transport_type}"
            )

        transport = FastAPIWebsocketTransport(
            websocket=session_args.websocket, params=params
        )

    else:
        raise ValueError(f"Unknown session arguments: {session_args}")

    await run_bot_logic(transport, handle_sigint)


# Local development entry point
if __name__ == "__main__":
    from lib.cloud import main

    main()
