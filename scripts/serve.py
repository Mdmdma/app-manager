#!/usr/bin/env python3
"""Thin uvicorn shim for the jam server."""

import argparse
import uvicorn


def main():
    parser = argparse.ArgumentParser(description="Start the jam server")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host")
    parser.add_argument("--port", type=int, default=8001, help="Bind port")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    args = parser.parse_args()

    uvicorn.run(
        "jam.server:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
