# AgentLeak OSS — minimal runtime image.
FROM python:3.12-slim

WORKDIR /app
COPY . /app

RUN pip install --no-cache-dir .

# Analyze a mounted trace, e.g.:
#   docker run --rm -v "$PWD/traces:/data" agentleak run --trace /data/trace.json
ENTRYPOINT ["agentleak"]
CMD ["--help"]
