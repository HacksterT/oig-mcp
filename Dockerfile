# Container image for remote (streamable HTTP) deployment, such as IBM Code Engine.
#
# Serves MCP at :8080/mcp with a health check at :8080/health. app.py selects
# HTTP because PORT is set below, and refuses to start without MCP_AUTH_TOKEN.
# Supply secrets at run time. None are baked into the image.

FROM docker.io/library/python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080 \
    PATH=/app/.venv/bin:$PATH \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

# Install uv from the same index as the dependencies, at a fixed version.
RUN pip install --no-cache-dir --quiet uv==0.10.12

# Install exactly what uv.lock records: no dev or eval dependencies.
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
RUN uv sync --frozen --no-dev --no-cache

# Run as an unprivileged user.
RUN useradd --system --uid 10001 --no-create-home oig
USER 10001

EXPOSE 8080

CMD ["python", "-m", "oig_mcp.app"]
