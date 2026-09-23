run:
	uv run fastapi dev

mcp:
	uv run mcp dev agent/mcp_server.py:mcp

ruff:
	uv run ruff check . --fix && \
	uv run ruff format .