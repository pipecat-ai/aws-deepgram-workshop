FROM dailyco/pipecat-base:latest

COPY ./requirements.txt requirements.txt

RUN pip install --no-cache-dir --upgrade -r requirements.txt

COPY ./strands_agent.py strands_agent.py
COPY ./utils.py utils.py
RUN mkdir -p lib
COPY ./lib/cloud.py lib/cloud.py
COPY ./lib/daily.py lib/daily.py
COPY ./lib/runner_utils.py lib/runner_utils.py
COPY ./bot.py bot.py