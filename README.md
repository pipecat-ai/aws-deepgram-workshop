# AWS/Deepgram Workshop Demo Project

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

## Get Started

### 1. Get the starter project

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

### 3. Authenticate with Pipecat Cloud

```bash
pcc auth login
```

### 4. Acquire required API keys

This starter requires the following API keys, which should be provided by the workshop instructor. Rename `env.example` to `.env` and add them:

```bash
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
DAILY_API_KEY=
DEEPGRAM_API_KEY=
```

### 5. Run the agent locally

You can test your agent locally before deploying to Pipecat Cloud:

```bash
pip install -r requirements.txt
```

Then, launch the bot.py script locally:

```bash
LOCAL_RUN=1 python bot.py
```

## Deploy & Run

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

### 2. Create a secret set for your API keys

Your agent needs the keys in your .env file, but _don't_ put the .env file in your Docker image. Instead, create a secret set from your .env file:

```bash
pcc secrets set aws-deepgram-workshop-secrets --file .env
```

Alternatively, you can create secrets directly via CLI:

### 3. Deploy to Pipecat Cloud

```bash
pcc deploy aws-deepgram-workshop YOUR_DOCKERHUB_USERNAME/aws-deepgram-workshop:0.1 --secrets aws-deepgram-workshop-secrets
```

> **Note (Optional)**: For a more maintainable approach, you can use the included `pcc-deploy.toml` file:
>
> ```toml
> agent_name = "aws-deepgram-workshop"
> image = "YOUR_DOCKERHUB_USERNAME/aws-deepgram-workshop:0.1"
> secret_set = "aws-deepgram-workshop-secrets"
>
> [scaling]
>     min_instances = 0
> ```
>
> Then simply run `pcc deploy` without additional arguments.

> **Note**: If your repository is private, you'll need to add credentials:
>
> ```bash
> # Create pull secret (you’ll be prompted for credentials)
> pcc secrets image-pull-secret pull-secret https://index.docker.io/v1/
>
> # Deploy with credentials
> pcc deploy aws-deepgram-workshop YOUR_DOCKERHUB_USERNAME/aws-deepgram-workshop:0.1 --credentials pull-secret
> ```

### 4. Check deployment and scaling (optional)

By default, your agent will use "scale-to-zero" configuration, which means it may have a cold start of around 10 seconds when first used. By default, idle instances are maintained for 5 minutes before being terminated when using scale-to-zero.

For more responsive testing, you can scale your deployment to keep a minimum of one instance warm:

```bash
# Ensure at least one warm instance is always available
pcc deploy  aws-deepgram-workshop YOUR_DOCKERHUB_USERNAME/aws-deepgram-workshop:0.1 --min-instances 1

# Check the status of your deployment
pcc agent status aws-deepgram-workshop
```

By default, idle instances are maintained for 5 minutes before being terminated when using scale-to-zero.

### 5. Create an API key

```bash
# Create a public API key for accessing your agent
pcc organizations keys create

# Set it as the default key to use with your agent
pcc organizations keys use
```

### 6. Start your agent

```bash
# Start a session with your agent in a Daily room
pcc agent start aws-deepgram-workshop --use-daily
```

This will return a URL, which you can use to connect to your running agent.

## Documentation

For more details on Pipecat Cloud and its capabilities:

- [Pipecat Cloud Documentation](https://docs.pipecat.daily.co)
- [Pipecat Project Documentation](https://docs.pipecat.ai)

## Support

Join our [Discord community](https://discord.gg/dailyco) for help and discussions.
