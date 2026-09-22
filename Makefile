run:
	uv run fastapi dev

mcp:
	uv run python -m agent.mcp_server

ruff:
	uv run ruff check . --fix && \
	uv run ruff format .