# The reports connector as a container, for the platform's Airflow (Metamorph-Knowledge-Platform/dags).
# Build from the workspace root, the directory holding every repository, so the shared packages sit where
# pyproject.toml's path sources expect them (../Metamorph-Knowledge-Platform/packages/…):
#   docker build -f Reports-Connector/Dockerfile -t metamorph/reports:dev .
# data/ is not in the image: Airflow bind-mounts the repository's data/ directory, where its reports and MinerU readings are kept.
FROM python:3.11-slim
COPY --from=ghcr.io/astral-sh/uv:0.9.27 /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH=/opt/venv/bin:$PATH
# Bundles land in a named volume that takes this directory's owner the first time it is mounted.
RUN useradd --create-home --uid 1000 connector && mkdir /bundles && chown connector /bundles

WORKDIR /workspace/Reports-Connector
COPY Metamorph-Knowledge-Platform/packages/metamorph-contract /workspace/Metamorph-Knowledge-Platform/packages/metamorph-contract
COPY Metamorph-Knowledge-Platform/packages/metamorph-market-contract /workspace/Metamorph-Knowledge-Platform/packages/metamorph-market-contract
COPY Metamorph-Knowledge-Platform/packages/metamorph-pdf-text /workspace/Metamorph-Knowledge-Platform/packages/metamorph-pdf-text
COPY Reports-Connector/pyproject.toml ./pyproject.toml
COPY Reports-Connector/uv.lock ./uv.lock
COPY Reports-Connector/README.md ./README.md
COPY Reports-Connector/src ./src
RUN uv sync --frozen --no-dev

USER connector
CMD ["reports", "--help"]
