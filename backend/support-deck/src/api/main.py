"""Uvicorn entry: ``python -m src.api.main`` from the ``support-deck/`` package root."""

from __future__ import annotations

import uvicorn

from src.api.app import create_app

app = create_app()


def main() -> None:
    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=8001,
        reload=False,
    )


if __name__ == "__main__":
    main()
