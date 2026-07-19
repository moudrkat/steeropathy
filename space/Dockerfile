# HuggingFace Space (Docker SDK): the steeropathy web UI in replay mode.
# No GPU, no model — saved runs replay from JSON; live internals need a
# local brainscope (see the repo README).
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*
RUN git clone --depth 1 https://github.com/moudrkat/steeropathy.git /app
WORKDIR /app
RUN pip install --no-cache-dir -e .

ENV PORT=7860 BIND=0.0.0.0
EXPOSE 7860
CMD ["python", "-m", "steeropathy"]
