"""CLI entrypoint: run the gateway with uvicorn."""

from __future__ import annotations

import os


def main() -> None:
    import uvicorn

    host = os.environ.get("GATEWAY_HOST", "0.0.0.0")
    port = int(os.environ.get("GATEWAY_PORT", "8080"))
    uvicorn.run("llm_gateway.app:app", host=host, port=port)


if __name__ == "__main__":
    main()
