# Pipecat voice agent with Deepgram, AWS Bedrock, AWS Strands, and pg_vector

This is the agent code used in the AWS Workshop [Building intelligent voice AI agents with Amazon Nova Sonic, Amazon Bedrock and Pipecat](https://catalog.workshops.aws/voice-ai-agents/en-US). Follow the instructions in that workshop to configure an AWS environment to use with this code.

## Understanding the Botfile

To learn more about the architecture of a Pipecat botfile, you can read through the [Pipecat Overview](https://docs.pipecat.ai/guides/learn/overview). The rest of this guide will use some basic Pipecat terminology that's explained in those docs.

Let's build the `agent.py` file that contains your agent.

### Starting the botfile

You'll need these imports at the top of `agent.py`. You can add them now, or refer back to this list as you add other code to the file.

```python
import argparse
import os
from datetime import datetime

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv
from loguru import logger
from pipecat.adapters.schemas.function_schema import FunctionSchema
from pipecat.adapters.schemas.tools_schema import ToolsSchema
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.vad.vad_analyzer import VADParams
from pipecat.frames.frames import LLMRunFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.runner.types import RunnerArguments
from pipecat.runner.utils import create_transport
from pipecat.services.aws.llm import AWSBedrockLLMService
from pipecat.services.aws.stt import AWSTranscribeSTTService
from pipecat.services.aws.tts import AWSPollyTTSService
from pipecat.services.aws_nova_sonic import AWSNovaSonicLLMService
from pipecat.services.deepgram.stt import DeepgramSTTService, LiveOptions
from pipecat.services.deepgram.tts import DeepgramTTSService
from pipecat.services.llm_service import FunctionCallParams
from pipecat.transcriptions.language import Language
from pipecat.transports.base_transport import BaseTransport, TransportParams
from pipecat.transports.daily.transport import DailyParams
from strands import Agent, tool
from strands.models import BedrockModel
```

Your bot uses a few different third-party services. The standard security practice is to make the API keys for those services available as environment variables. Here, we'll use a Python library to load a `.env` file with our keys:

```python

load_dotenv(override=True)

# Bedrock Knowledge Base Configuration
KNOWLEDGE_BASE_ID = os.getenv("KB_ID")
```

Rename `example.env` to `.env` and add your keys, as well as your KB_ID.

If you're using git, make sure to ignore that file in your `.gitignore` file:

```
# .gitignore

(...)
.env
```

Back in your `agent.py` file, we'll create a function called `run_bot`. This function contains the core logic of your bot. We'll use some other functions later in the file to run this function.

`run_bot` accepts two parameters: 

* The `transport` parameter describes how your bot should connect to the user. By passing in different transport objects and configurations, you can use this same `run_bot` logic through a direct WebRTC connection using a `SmallWebRTCTransport`, or through Daily's hosted WebRTC service using `DailyTransport`, or through a websocket to Twilio using a `WebsocketTransport`.
* The `runner_args` parameter includes information unique to this bot session. For example, you can use `runner_args` to greet each user by name, or even pass the bot's system prompt in through `runner_args`.

```python

async def run_bot(transport: BaseTransport, runner_args: RunnerArguments):
    logger.info("Starting Bedrock Knowledge Base Voice Agent with Strands")
```

The heart of your botfile is the **Pipeline**. This is where you define the series of processors that will receive input from the user, process it, and generate output. Let's define our pipeline now, inside the `run_bot` function:

```python
    # Build the pipeline
    pipeline = Pipeline(
        [
            transport.input(),
            stt,
            context_aggregator.user(),
            llm,
            tts,
            transport.output(),
            context_aggregator.assistant(),
        ]
    )
```

Let's look quickly at each processor in the pipeline.

The `transport.input()` is receiving media from the user and sending it through the pipeline as audio (and possibly video) frames. It's also creating other frames for things like connect/disconnect events, or when the user starts and stops speaking.

The `stt` processor is a speech-to-text service that receives the user's audio frames, sends them to a transcription service, and outputs the received transcription as TextFrames.

The `context_aggregator.user()` processor is collecting text frames from the STT processor and user started/stopped speaking frames from the transport in order to determine when the user has completed a 'turn'. Once it makes that determination, this processor emits an LLM context frame to prompt a completion from the LLM processor.

The `llm` sends LLM context frames to an LLM service and returns the responses as a stream of text frames.

The `tts` service collects text frames from the LLM and sends them to a text-to-speech service, and then outputs audio frames with the generated audio.

The `transport.output()` receives the audio frames from the TTS service and plays them for the user.

Finally, the `context_aggregator.assistant()` sees the audio and text frames after the transport has 'played' them, and aggregates them to store the bot's responses. The user and assistant context aggregators are part of the same `context_aggregator` object, which is how the user and bot turns are stored together.

If you try to run this botfile right now, you'd get an error, because none of those processors are actually defined yet. Let's add code just above here to define a few of these processors.

```python
    #just below logger.info(f"Starting Bedrock Knowledge Base Voice Agent with Strands")
    strands_agent = StrandsAgent()

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
        aws_region="us-east-1",
        model="us.anthropic.claude-3-5-haiku-20241022-v1:0",
    )

```

Our main LLM, the one in the pipeline, is the one that interacts with the user. We need to give it a way to pass queries to the Strands agent. We'll do that with a tool call. Define a `search_knowledge_base` function, and register it with the LLM:

```python
    async def search_knowledge_base(params: FunctionCallParams):
        query = params.arguments.get("query", "")

        if not query:
            await params.result_callback(
                {
                    "error": "No query provided",
                    "response": "Please provide a question or claim ID to search the knowledge base.",
                }
            )
            return

        logger.info(f"Using Strands agent for: {query}")

        try:
            response_text = strands_agent.process_query(query)

            await params.result_callback(
                {
                    "query": query,
                    "response": response_text,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "knowledge_base_id": KNOWLEDGE_BASE_ID,
                }
            )

        except Exception as e:
            logger.error(f"Error with Strands agent for {query}: {e}")
            await params.result_callback(
                {
                    "query": query,
                    "response": f"I encountered an error while searching for '{query}'. Please try again.",
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "knowledge_base_id": KNOWLEDGE_BASE_ID,
                }
            )

    llm.register_function("search_knowledge_base", search_knowledge_base)
```

Next, let's create the context aggregators. They share a `messages` list that stores the user and bot turns. For more on how this works, see Pipecat's documentation on [context management](https://docs.pipecat.ai/guides/learn/context-management).

```python
    # System instruction for knowledge base integration
    system_instruction = (
        "You are a helpful AI assistant that can help with claim lookups and general questions. "
        "For claim-related queries, use the search_knowledge_base function. "
        "When users mention numbers, treat them as claim IDs and search for them directly. "
        "Search for EXACT claim IDs only: "
        "- If they say 'claim ID 1', search for 'claim ID 1' specifically "
        "- If they say 'claim ID 1234', search for 'claim ID 1234' specifically "
        "For general questions not related to specific claims, you can answer directly without using the search function."
        "For claim estimates, costs, amounts, or any other information, always search for that specific information. "
        "Keep your responses very brief. Don't add extra information the user didn't ask for. "
        f"{AWSNovaSonicLLMService.AWAIT_TRIGGER_ASSISTANT_RESPONSE_INSTRUCTION}"
    )

    context = OpenAILLMContext(
        messages=[
            {"role": "system", "content": system_instruction},
            {
                "role": "user",
                "content": "Start by saying exactly this: 'Thanks for contacting tri-county insurance. How can I help you?",
            },
        ],
        tools=tools,
    )
    context_aggregator = llm.create_context_aggregator(context)
```

### Configuring the Strands agent

We created an instance of a StrandsAgent in the `run_bot` function, but we haven't defined that class yet. Just above the `run_bot` function, create a `StrandsAgent` class:

```python
class StrandsAgent:
    def __init__(self):
        self.session = boto3.Session(
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            region_name=os.getenv("AWS_REGION", "us-east-1"),
        )

        self.bedrock_model = BedrockModel(
            model_id="amazon.nova-lite-v1:0", boto_session=self.session
        )
        self.bedrock_client = BedrockKnowledgeBaseClient(KNOWLEDGE_BASE_ID)

        self.agent = Agent(
            tools=[self.search_knowledge_base, self.general_query],
            model=self.bedrock_model,
            system_prompt="You are a claim assistant. Search for EXACT claim IDs only. When users say 'claim ID 1', search for 'claim ID 1' specifically, not '1234'. When they say 'claim ID 1234', search for 'claim ID 1234' specifically. Use general_query for non-claim questions.",
        )

    @tool
    async def search_knowledge_base(self, query: str) -> str:
        """Search for specific claim information in knowledge base"""
        logger.info(f"Searching KnowledgeBase: {query}")
        return await self.bedrock_client.query_knowledge_base(query)

    @tool
    async def general_query(self, question: str) -> str:
        """Answer general questions directly using the model"""
        logger.info(f"Answering general question: {question}")
        try:
            # Use the Bedrock model directly for general questions
            response = await self.bedrock_model.generate_async(
                messages=[{"role": "user", "content": question}], max_tokens=200
            )
            return response.content
        except Exception as e:
            logger.error(f"Error with general query: {e}")
            return "I can help answer general questions. What would you like to know?"

    def process_query(self, user_input: str) -> str:
        """Process user input through the Strands agent"""
        try:
            response = self.agent(user_input)
            return str(response)
        except Exception as e:
            logger.error(f"Error processing query with StrandsAgent: {e}")
            return "I'm sorry, I encountered an error processing your request."


search_function = FunctionSchema(
    name="search_knowledge_base",
    description="Search the knowledge base",
    properties={"query": {"type": "string"}},
    required=["query"],
)

tools = ToolsSchema(standard_tools=[search_function])
```

In the `search_knowledge_base` function in the main LLM, we called `strands_agent.process_query()` to give the user's request to the Strands agent. In the StrandsAgent class, the `process_query` function is passing that input to an instance of the Strands library's `Agent` class. We're also defining some different tools that the Strands agent can use with the `@tool` decorator on the `general_query` and `search_knowledge_base` functions.

Speaking of `search_knowledge_base`, we're using a `BedrockKnowledgeBaseClient` in that function. We should define that class right above the `StrandsAgent` class:

```python
class BedrockKnowledgeBaseClient:
    """Client for interacting with Amazon Bedrock Knowledge Base"""

    def __init__(self, knowledge_base_id: str):
        self.knowledge_base_id = knowledge_base_id
        self.bedrock_agent_runtime = boto3.client(
            "bedrock-agent-runtime",
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            region_name=os.getenv("AWS_REGION", "us-east-1"),
        )
        logger.info(
            f"Initialized Bedrock Knowledge Base client for KB: {knowledge_base_id}"
        )

    async def query_knowledge_base(self, query: str, max_results: int = 10) -> str:
        """Query the Bedrock Knowledge Base and return formatted response"""
        try:
            logger.info(f"Querying knowledge base with: {query}")

            # Enhanced query for better claim ID matching
            enhanced_query = query
            if any(
                keyword in query.lower()
                for keyword in ["claim", "id", "number", "reference", "ticket"]
            ):
                enhanced_query = f"claim ID {query}"

            response = self.bedrock_agent_runtime.retrieve(
                knowledgeBaseId=self.knowledge_base_id,
                retrievalQuery={"text": enhanced_query},
                retrievalConfiguration={
                    "vectorSearchConfiguration": {
                        "numberOfResults": max_results,
                        "overrideSearchType": "HYBRID",  # Use both semantic and keyword search
                    }
                },
            )

            # Extract and format the results
            results = response.get("retrievalResults", [])

            if not results:
                # Try alternative query if no results found
                logger.info(f"No results found, trying alternative query: {query}")
                alt_response = self.bedrock_agent_runtime.retrieve(
                    knowledgeBaseId=self.knowledge_base_id,
                    retrievalQuery={"text": query},
                    retrievalConfiguration={
                        "vectorSearchConfiguration": {
                            "numberOfResults": max_results,
                            "overrideSearchType": "SEMANTIC",
                        }
                    },
                )
                results = alt_response.get("retrievalResults", [])

            if not results:
                return f"I couldn't find any information about '{query}' in the knowledge base. Please check if the claim ID exists or try rephrasing your question."

            # Format the response with more detail
            formatted_response = f"Found {len(results)} result(s) for your query:\n\n"

            for i, result in enumerate(results[:5], 1):  # Show top 5 results
                content = result.get("content", {}).get("text", "")
                score = result.get("score", 0)
                source = (
                    result.get("location", {})
                    .get("s3Location", {})
                    .get("uri", "Unknown source")
                )

                if content:
                    # Show full content for claim-related queries to include all notes
                    content_length = (
                        1000
                        if any(keyword in query.lower() for keyword in ["claim", "id"])
                        else 200
                    )
                    truncated_content = content[:content_length]
                    if len(content) > content_length:
                        truncated_content += "..."

                    formatted_response += f"{i}. {truncated_content}\n"
                    formatted_response += f"   (Relevance: {score:.2f})\n\n"

            return formatted_response.strip()

        except ClientError as e:
            error_msg = f"Error querying knowledge base: {e}"
            logger.error(error_msg)
            return f"I encountered an error while searching for '{query}'. Please try again or contact support if the issue persists."
        except Exception as e:
            error_msg = f"Unexpected error: {e}"
            logger.error(error_msg)
            return "I'm sorry, something went wrong while processing your request."
```

You can refer to the Amazon Knowledge Base documentation to learn more about this code.


### Finishing the Botfile

That takes care of everything except for the `transport` object in the pipeline. We'll come back to that later.

Next, we need to define a pipeline task. This is how `asyncio` runs the pipeline. Do this right after you've defined your pipeline:

```python
	# pipeline = Pipeline(...)
	
	task = PipelineTask(
        pipeline,
        params=PipelineParams(
            enable_metrics=True,
            enable_usage_metrics=True,
        ),
        observers=[RTVIObserver(rtvi)],
    )
```

We've added a special [observer](https://docs.pipecat.ai/server/utilities/observers/observer-pattern#observer-pattern) that allows the RTVI processor to send certain events to the frontend, as well as enabled metrics reporting in the `PipelineParams`.

Next, we need to add some event handlers so the pipeline knows how to handle the user connecting and disconnecting. First, when the user connects, we'll push a frame that tells the LLM to run.

```python
    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        logger.info(f"Client connected")
        # Kick off the conversation.
        messages.append({"role": "system", "content": "Say hello and briefly introduce yourself."})
        await task.queue_frames([LLMRunFrame()])
```

And when the user disconnects, we'll tell the bot to stop.

```python
    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        logger.info(f"Client disconnected")
        await task.cancel()
```

Finally, we can create a `PipelineRunner` object and actually run the pipeline.

```python
    runner = PipelineRunner(handle_sigint=runner_args.handle_sigint)

    await runner.run(task)
```

That's all the code we need for the `run_bot` function. But in order to run that function, we need to define an entrypoint function called `bot` that configures the transport and calls `run_bot`. Add this function at the bottom of your botfile, making sure it's at the top level of indentation so it's not inside the `run_bot` function.

```python
async def bot(runner_args: RunnerArguments):
    """Main bot entry point for the bot starter."""

    transport_params = {
        "daily": lambda: DailyParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            vad_analyzer=SileroVADAnalyzer(),
        ),
        "webrtc": lambda: TransportParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            vad_analyzer=SileroVADAnalyzer(),
        ),
    }

    transport = await create_transport(runner_args, transport_params)

    await run_bot(transport, runner_args)
```

The `transport_params` object describes how we want to configure the various transports that this bot supports. In this case, we'll support the DailyTransport (`daily`) and the SmallWebRTCTransport (`webrtc`). The bot starter will request a transport type in the `runner_args`, and the `create_transport` function will create a transport object that gets passed to the `run_bot` function.

When you're developing locally, your 'bot runner' is built in to pipecat. We need to add one more thing to the bottom of our botfile for local development.

```python
if __name__ == "__main__":
    from pipecat.runner.run import main

    main()
```

With this code at the bottom of the botfile, we can run `python agent.py` from the command line. The Pipecat built-in bot runner `main()` function will call the `bot()` function with some pre-configured arguments in `runner_args`, which will in turn call the `run_bot` function to actually run the bot.


## Deploying to Pipecat Cloud

You can deploy this bot to Pipecat Cloud and get production-ready infrastructure in about 5 minutes. Rename your file from `agent.py` to `bot.py`, then follow the instructions from [the Pipecat Cloud Quickstart](https://github.com/pipecat-ai/pipecat-quickstart?tab=readme-ov-file#step-2-deploy-to-production-5-min)!
