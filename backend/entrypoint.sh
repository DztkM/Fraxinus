#!/bin/sh

uv run alembic upgrade head

uv run fastapi dev app/main.py --host 0.0.0.0