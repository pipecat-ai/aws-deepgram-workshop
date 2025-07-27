# AWS/Deepgram Workshop Demo Project

**TLDR:**

TKTKTK AWS and Deepgram links

**AWS credentials can be found [here](#). Sign up for a Deepgram account [here](https://console.deepgram.com/signup?jump=keys). Rename `example.env` to `.env` and fill in the environment variables. For the advanced bot, edit the Dockerfile to use `bot-advanced.py` instead of `bot-basic.py`.**

> **For detailed step-by-step guides, see our [Pipecat Quickstart](https://docs.pipecat.ai/getting-started/quickstart) and [Pipecat Cloud Quickstart](https://docs.pipecat.daily.co/quickstart).**

## Prerequisites

To run the bot locally:

- Python 3.10+
- Linux, MacOS, or Windows Subsystem for Linux (WSL)

To deploy it to Pipecat Cloud:

- [Docker](https://www.docker.com) and a Docker repository (e.g., [Docker Hub](https://hub.docker.com))
- A Docker Hub account (or other container registry account)
- [Pipecat Cloud](https://pipecat.daily.co) account

To run the front-end remotely:

- A Vercel account, or somewhere you can easily deploy a React/Next.js app

> **Note**: If you haven't installed Docker yet, follow the official installation guides for your platform ([Linux](https://docs.docker.com/engine/install/), [Mac](https://docs.docker.com/desktop/setup/install/mac-install/), [Windows](https://docs.docker.com/desktop/setup/install/windows-install/)). For Docker Hub, [create a free account](https://hub.docker.com/signup) and log in via terminal with `docker login`.

## Part 1: Run a voice agent locally

First, follow these steps to get a voice agent (bot) running on your computer. You'll use a prebuilt web interface that's built into Pipecat for now, but you'll be able to build a custom UI later in the workshop.

### 1. Get the repo

Clone this repo:

```bash
git clone https://github.com/daily-co/aws-deepgram-workshop
cd aws-deepgram-workshop
```

### 2. Set up your Python environment

We recommend using a virtual environment to manage your Python dependencies.

```bash
# Create a virtual environment
python -m venv .venv

# Activate it
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install the Pipecat Cloud CLI
pip install pipecatcloud
```

### 3. Acquire required API keys

TKTKTK AWS and Deepgram links
This starter requires API keys for AWS and Deepgram. AWS credentials can be found [here](#). Sign up for a Deepgram account [here](https://console.deepgram.com/signup?jump=keys) to get your own Deepgram API key. Rename `env.example` to `.env` and add keys:

```bash
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
DAILY_API_KEY=
DEEPGRAM_API_KEY=
```

### 4. Choose your difficulty level

This workshop has two agents to choose from. If you're new to Pipecat, we recommend starting with the `basic` bot. It features a straightforward "cascading" pipeline, using Deepgram's speech-to-text, LLM inference with Claude on AWS Bedrock, and Deepgram's text-to-speech service.

If you're familiar with Pipecat's bot architecture, we've also included an `advanced` bot. It has a parallel pipeline that's running a [Strands agent](https://strandsagents.com/latest/), which can do more in-depth thinking and reasoning. The main LLM pipeline uses function calling to delegate certain questions to the Strands agent.

To choose which bot to use, rename `bot-basic.py` or `bot-advanced.py` to `bot.py`:

```bash
mv bot-basic.py bot.py
# or
mv bot-advanced.py bot.py
```

You can also leave the bot file names as-is and rename them when you build your Docker image to deploy to Pipecat Cloud. Pipecat Cloud expects a file named `bot.py`, so just change the last line of the Dockerfile to `COPY ./bot-basic.py bot.py`, for example.

The rest of this guide will assume you're using `bot.py` for your botfile.

### 5. Run the agent

You can run the bot locally using the SmallWebRTC transport:

```bash
python bot.py
```

When it's running, open a browser to `http://localhost:7860` to interact with the bot using the console from the new [Pipecat Voice UI Kit](https://github.com/pipecat-ai/voice-ui-kit). You can customize this UI later in the workshop if you want.

## Part 2: Deploy to Pipecat Cloud

Next, you'll deploy your bot to Pipecat Cloud. You'll be able to talk to your bot in a browser using the Daily WebRTC transport. If you have a Twilio phone number, you can also configure your bot to receive calls from your phone using the Twilio transport.

### 1. Build and push your Docker image

It's good to do this manually the first time to get a sense of what you're doing.

```bash
# Build the image (targeting ARM architecture for cloud deployment)
docker build --platform=linux/arm64 -t aws-deepgram-workshop:latest .

# Tag with your Docker username and version
docker tag aws-deepgram-workshop:latest YOUR_DOCKERHUB_USERNAME/aws-deepgram-workshop:0.1

# Push to Docker Hub
docker push YOUR_DOCKERHUB_USERNAME/aws-deepgram-workshop:0.1
```

For subsequent builds, you can update the values in `./build.sh` and run it.

### 2. Authenticate with Pipecat Cloud

```bash
pip install pipecatcloud
pcc auth login
```

### 3. Create a secret set for your API keys

Your agent needs the keys in your .env file, but _don't_ put the .env file in your Docker image. Instead, create a secret set from your .env file:

```bash
pcc secrets set aws-deepgram-workshop-secrets --file .env
```

### 4. Deploy to Pipecat Cloud

**Note**: Pipecat Cloud will soon require credentials for all image pulls. To prepare for this, create a pull secret:

```bash
pcc secrets image-pull-secret pull-secret https://index.docker.io/v1/
```

You can deploy with command-line options, but this repo already contains a `pcc_deploy.toml` file that you can use to deploy. Edit that file to set your image and credentials, then run:

```bash
pcc deploy
```

### 6. Start your agent

```bash
# Start a session with your agent in a Daily room
pcc agent start aws-deepgram-workshop --use-daily
```

This will return a URL, which will open a Daily Prebuilt room that you can use to interact with your running agent.

To set up Twilio integration, follow the [Pipecat Cloud instructions here](https://docs.pipecat.daily.co/pipecat-in-production/telephony/twilio-mediastreams#twilio-setup) for the Twilio configuration. Your botfile should already have the needed configuration for the Twilio transport.

## Part 3 (Optional): Customize the UI

There's a new Pipecat front-end library you can use to build your own custom UI. Check out the [Pipecat Voice UI Kit](https://github.com/pipecat-ai/voice-ui-kit) to learn more about it!

This repo also contains a partial implementation of a custom UI in the `advanced-console` directory. (We're still working out some of the export details from voice-ui-kit, so there's some duplicated code to manage imports.) You can `cd advanced-console; npm i; npm run dev` to run it locally.

It features some light customization to display the Specialist's 'thinking' and speech. Search "specialist" in the code to see the relevant components.

You can run this UI locally and connect to an agent that's also running locally using the SmallWebRTCTransport. Instructions for pointing this UI at an agent running on Pipecat Cloud are coming soon.

## Part 4: What's next?

For more details on Pipecat Cloud and its capabilities:

- [Pipecat Cloud Documentation](https://docs.pipecat.daily.co)
- [Pipecat Project Documentation](https://docs.pipecat.ai)

Join our [Discord community](https://discord.gg/dailyco) for help and discussions!
