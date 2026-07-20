"""Command-line interface for daily and one-off pipeline execution."""

from __future__ import annotations

import argparse
import json
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import Settings
from .database import Database
from .export import export_workbook
from .models import Video
from .pipeline import TrendPipeline
from .youtube import YouTubeClient, parse_timestamp


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="youtube-trends")
    parser.add_argument("--database", type=Path, help="SQLite database path")
    parser.add_argument("--report", type=Path, help="Excel output path")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("init", help="Create the database schema")
    subparsers.add_parser("collect", help="Discover and ingest live YouTube videos")
    subparsers.add_parser("refresh", help="Refresh statistics and save today's snapshot")
    subparsers.add_parser("snapshot", help="Snapshot statistics already in the database")
    subparsers.add_parser("analyze", help="Rebuild clusters and opportunity scores")
    subparsers.add_parser("export", help="Write the Excel report")
    fixture = subparsers.add_parser(
        "import-fixture", help="Ingest a deterministic JSON fixture"
    )
    fixture.add_argument("fixture", type=Path)
    run_all = subparsers.add_parser("run-all", help="Run the complete daily pipeline")
    run_all.add_argument(
        "--fixture",
        type=Path,
        help="Use local fixture data instead of the live API",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    settings = Settings.from_env()
    if args.database:
        settings = replace(settings, database_path=args.database)
    if args.report:
        settings = replace(settings, report_path=args.report)

    with Database(settings.database_path) as database:
        pipeline = TrendPipeline(settings, database)
        if args.command == "init":
            _print({"database": str(settings.database_path), "status": "initialized"})
        elif args.command == "collect":
            result = pipeline.collect(YouTubeClient(settings.api_key))
            _print_collection(result.accepted, result.rejected)
        elif args.command == "refresh":
            count = pipeline.refresh(YouTubeClient(settings.api_key))
            _print({"snapshots": count})
        elif args.command == "snapshot":
            _print({"snapshots": pipeline.snapshot_current()})
        elif args.command == "analyze":
            _print({"themes": pipeline.analyze()})
        elif args.command == "export":
            _print({"report": str(export_workbook(database, settings.report_path))})
        elif args.command == "import-fixture":
            result = pipeline.ingest(load_fixture(args.fixture))
            _print_collection(result.accepted, result.rejected)
        elif args.command == "run-all":
            if args.fixture:
                result = pipeline.ingest(load_fixture(args.fixture))
                pipeline.snapshot_current()
            else:
                client = YouTubeClient(settings.api_key)
                result = pipeline.collect(client)
                pipeline.refresh(client)
            theme_count = pipeline.analyze()
            report = export_workbook(database, settings.report_path)
            _print(
                {
                    "accepted": len(result.accepted),
                    "rejected": result.rejected,
                    "themes": theme_count,
                    "report": str(report),
                }
            )
    return 0


def load_fixture(path: str | Path) -> list[Video]:
    payload: list[dict[str, Any]] = json.loads(Path(path).read_text())
    videos: list[Video] = []
    for item in payload:
        item = dict(item)
        published_at = item.get("published_at")
        if isinstance(published_at, str):
            item["published_at"] = parse_timestamp(published_at)
        videos.append(Video(**item))
    return videos


def _print_collection(videos: list[Video], rejected: dict[str, int]) -> None:
    _print({"accepted": len(videos), "rejected": rejected})


def _print(value: dict[str, Any]) -> None:
    print(json.dumps(value, indent=2, default=_json_default))


def _json_default(value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)
