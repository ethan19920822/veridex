from __future__ import annotations

import argparse
import asyncio
import json

import uvicorn

from .config import settings
from .engine import initialise, run_monitor


def main() -> None:
    parser = argparse.ArgumentParser(prog="veridex")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init", help="Create database and seed sources/demo profiles")
    sub.add_parser("run", help="Run one regulatory monitoring cycle")
    serve = sub.add_parser("serve", help="Start API and internal dashboard")
    serve.add_argument("--host", default=settings.host)
    serve.add_argument("--port", default=settings.port, type=int)
    args = parser.parse_args()

    if args.command == "init":
        initialise()
        print("Veridex Alpha initialized.")
    elif args.command == "run":
        result = asyncio.run(run_monitor())
        print(json.dumps(result, indent=2, ensure_ascii=False))
    elif args.command == "serve":
        uvicorn.run("veridex.api:app", host=args.host, port=args.port, reload=False)
