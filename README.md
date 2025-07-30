# AWS/Deepgram Workshop Demo Project

A Demo Pipecat-ai voice agent using Deepgram and AWS Strands. [Part 1](#part-1-run-a-voice-agent-locally) covers how to run the Pipecat voice agent locally. [Part 2](#part-2-deploy-a-voice-agent-to-pipecat-cloud) explains how to deploy the agent to Pipecat Cloud. There is also an optional [Part 3](#part-3-optional-customize-the-ui) that covers how to customize the UI.

**TLDR:**

**AWS credentials can be found [here](https://pastebin.com/wVU3Qhdz). Sign up for a Deepgram account [here](https://console.deepgram.com/signup?jump=keys). Rename `example.env` to `.env` and fill in the environment variables. For the advanced bot, edit the Dockerfile to use `bot-advanced.py` instead of `bot-basic.py`.**

> **For detailed step-by-step guides, see our [Pipecat Quickstart](https://docs.pipecat.ai/getting-started/quickstart) and [Pipecat Cloud Quickstart](https://docs.pipecat.daily.co/quickstart).**

## General Prerequisites

### 1. Clone this repo

```bash
git clone https://github.com/pipecat-ai/aws-deepgram-workshop
cd aws-deepgram-workshop
```

## Part 1: Run a voice agent locally

First, follow these steps to get a voice agent (bot) running on your computer. You'll use a prebuilt web interface that's built into Pipecat for now, but you'll be able to build a custom UI later in the workshop.

### Prerequisites

- Python 3.10+
- Linux, MacOS, or Windows Subsystem for Linux (WSL)

### 2. Set up your Python environment

We recommend using a virtual environment to manage your Python dependencies.

```bash
# Create a virtual environment
python -m venv .venv

# Activate it
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install requirements, including Pipecat Cloud CLI
pip install -r requirements.txt
```

### 3. Acquire required API keys

This starter requires API keys for AWS and Deepgram.

- [These AWS credentials](https://pastebin.com/wVU3Qhdz) are tied to several different AWS Workshop accounts with rate limiting, so choose a random set from the list.

- Sign up for a Deepgram account [here](https://console.deepgram.com/signup?jump=keys) to get your own Deepgram API key.

Rename `env.example` to `.env` and add keys:

```bash
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
DEEPGRAM_API_KEY=
```

> Optional: To use the Daily transport locally, you can also add your `DAILY_API_KEY` to the .env file.
> Note: you'll be able to use the Daily transport without a key when you deploy to Pipecat Cloud later in these instructions.

### 4. Choose your difficulty level

This workshop has two agents from which to choose: `bot-basic.py` and `bot-advanced.py`.

If you're new to Pipecat, start with the `basic` bot. It features a straightforward "cascading" pipeline, using Deepgram's speech-to-text, LLM inference with Claude on AWS Bedrock, and Deepgram's text-to-speech service.

The `advanced` bot has a parallel pipeline that's running a [Strands agent](https://strandsagents.com/latest/), which can do more in-depth thinking and reasoning. The main LLM pipeline uses function calling to delegate certain questions to the Strands agent. The Strands agent function handlers are hard-coded to try and get more consistent behavior. Try asking it "What's the weather at the Golden Gate Bridge?" to ensure that it needs to 'think' about a response.

### 5. Run the agent

Run the bot locally using the SmallWebRTC transport:

```bash
python bot-basic.py
```

or

```bash
python bot-advanced.py
```

When it's running, open a browser to `http://localhost:7860` to interact with the bot using the console from the new [Pipecat Voice UI Kit](https://github.com/pipecat-ai/voice-ui-kit). You can customize this UI later in the workshop if you want.

## Part 2: Deploy a voice agent to Pipecat Cloud

Next, you'll deploy your bot to Pipecat Cloud. You'll be able to talk to your bot in a browser using the Daily WebRTC transport. If you have a Twilio phone number, you can also configure your bot to receive calls from your phone using the Twilio transport.

### Prerequisites

- [Docker](https://www.docker.com) and a Docker repository (e.g., [Docker Hub](https://hub.docker.com))
- A Docker Hub account (or other container registry account)
- [Pipecat Cloud](https://pipecat.daily.co) account
- Optional: A Vercel account, or somewhere you can easily deploy a React/Next.js app (to run the front-end remotely)

> **Note**: If you haven't installed Docker yet, follow the official installation guides for your platform ([Linux](https://docs.docker.com/engine/install/), [Mac](https://docs.docker.com/desktop/setup/install/mac-install/), [Windows](https://docs.docker.com/desktop/setup/install/windows-install/)). For Docker Hub, [create a free account](https://hub.docker.com/signup) and log in via terminal with `docker login`.

### 0. Rename to `bot.py`

Pipecat Cloud expects the main entry to your bot to be called `bot.py`. This is done in the Dockerfile, but for simplicity rename with:

```bash
mv bot-basic.py bot.py
```

or

```bash
mv bot-advanced.py bot.py
```

> Note: `docker build` will fail if the filename is not changed.

### 1. Build and push your Docker image

It's good to do this manually the first time to get a sense of what you're doing.

> This will push to a _public_ Dockerhub repository. Ensure any changes you may have made are OK to be public.

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
pcc auth login
```

> run `pip install pipecatcloud` if `pcc: command not found`

### 3. Create a secret set for your API keys

Your agent needs the keys for AWS and Deepgram in your `.env` file, but _don't_ put the `.env` file in your Docker image. Instead, create a secret set from your `.env` file:

```bash
pcc secrets set aws-deepgram-workshop-secrets --file .env
```

### 4. Deploy to Pipecat Cloud

**Note**: Pipecat Cloud requires credentials for all image pulls. 

**Follow this guide to generate a personal access token for Docker Hub**

[Using private Docker Hub images with Pipecat Cloud](https://docs.pipecat.daily.co/agents/secrets#using-private-docker-hub-images-with-pipecat-cloud

Then create a pull secret. Use the personal access token you created, not your login password.

```bash
pcc secrets image-pull-secret pull-secret https://index.docker.io/v1/
```

Edit `pcc_deploy.toml` to set your image and credentials, then run:

```bash
pcc deploy
```

> You can override `pcc_deploy.toml` values with command-line options. See `pcc deploy --help`.

### 6. Start your agent

```bash
# Start a session with your agent in a Daily room
pcc agent start aws-deepgram-workshop --use-daily
```

This will return a URL, which will open a Daily Prebuilt room that you can use to interact with your running agent.

### 6a. Talk to your bot with a Twilio phone number

To set up Twilio integration, follow the [Pipecat Cloud instructions here](https://docs.pipecat.daily.co/pipecat-in-production/telephony/twilio-mediastreams#twilio-setup) for the Twilio configuration.

We're using a new bot() function in these botfiles, and we're still working out some last-minute issues with Twilio configuration. For now, if you want to use this bot with Twilio on Pipecat Cloud, you can refer to the [Pipecat Cloud Twilio starter](https://github.com/daily-co/pipecat-cloud-images/blob/main/pipecat-starters/twilio/bot.py) for an example of how to set up the botfile.

## Part 3 (Optional): Customize the UI

There's a new Pipecat front-end library you can use to build your own custom UI. Check out the [Pipecat Voice UI Kit](https://github.com/pipecat-ai/voice-ui-kit) to learn more about it!

This repo also contains a partial implementation of a custom UI in the `advanced-console` directory. (We're still working out some of the export details from voice-ui-kit, so there's some duplicated code to manage imports.)
To run it locally:

```bash
cd advanced-console; npm i; npm run dev
```

It features some light customization to display the Specialist's 'thinking' and speech. Search "specialist" in the code to see the relevant components.

You can run this UI locally and connect to an agent that's also running locally using the SmallWebRTCTransport. Instructions for pointing this UI at an agent running on Pipecat Cloud are coming soon.

## Reference

For more details on Pipecat Cloud and its capabilities:

- [Pipecat Cloud Documentation](https://docs.pipecat.daily.co)
- [Pipecat Project Documentation](https://docs.pipecat.ai)

Join our [Discord community](https://discord.gg/dailyco) for help and discussions!
