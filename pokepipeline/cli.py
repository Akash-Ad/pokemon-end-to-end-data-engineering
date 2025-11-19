"""
This file provides a command-line interface that parses arguments and runs the PokePipeline ETL.
"""
from __future__ import annotations
import argparse
from .pipeline import run_etl

def main() -> None:
    parser = argparse.ArgumentParser(description="Run the PokéPipeline ETL.")
    parser.add_argument("--limit", type=int, default=20, help="Number of Pokemon to load")
    parser.add_argument("--offset", type=int, default=0, help="Offset for pagination")
    args = parser.parse_args()

    requested, loaded = run_etl(limit=args.limit, offset=args.offset)
    print(f"requested={requested} loaded={loaded}")


if __name__ == "__main__":
    main()