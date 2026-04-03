import argparse
import asyncio
import logging
import sys

from pathlib import Path

from app import sqlite_shim  # noqa: F401 — до chromadb (старый SQLite на Linux)

from dotenv import load_dotenv

from app.pipeline import Pipeline

_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(_ENV_FILE)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def parse_args():
    parser = argparse.ArgumentParser(description="AI Sale Parsing Agent")
    parser.add_argument(
        "--config",
        default="configs/sources.yaml",
        help="Path to sources config",
    )
    parser.add_argument(
        "--processing-config",
        default="configs/processing.yaml",
        help="Path to processing config",
    )
    parser.add_argument("--parse-only", action="store_true", help="Only parse, don't load to DB")
    parser.add_argument("--load-only", action="store_true", help="Only load processed data")
    parser.add_argument("--input", default="data/processed/", help="Input dir for --load-only")
    parser.add_argument("--output", default="data/processed/", help="Output dir for --parse-only")
    parser.add_argument("--clear-collection", action="store_true", help="Clear ChromaDB collection")
    parser.add_argument("--stats", action="store_true", help="Show collection stats")
    return parser.parse_args()


async def main():
    args = parse_args()
    pipeline = Pipeline(
        sources_config=args.config,
        processing_config=args.processing_config,
    )

    if args.stats:
        await pipeline.show_stats()
        return

    if args.clear_collection:
        await pipeline.clear_collection()
        return

    if args.parse_only:
        await pipeline.run_parse_only(output_dir=args.output)
    elif args.load_only:
        await pipeline.run_load_only(input_dir=args.input)
    else:
        await pipeline.run_full()


if __name__ == "__main__":
    asyncio.run(main())
