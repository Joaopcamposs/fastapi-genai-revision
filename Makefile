run:
	uv run fastapi dev

ruff:
	uv run ruff check . --fix && \
	uv run ruff format .