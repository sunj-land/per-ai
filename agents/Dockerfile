FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY agents/pyproject.toml /app/agents/pyproject.toml
COPY agents/langgraph.json /app/agents/langgraph.json
COPY agents /app/agents

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -e /app/agents

EXPOSE 8001

CMD ["python", "-m", "agents.main"]
