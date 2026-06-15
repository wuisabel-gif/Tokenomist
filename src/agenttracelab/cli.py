"""Command-line interface for AgentTraceLab.

Examples
--------
    agenttracelab analyze data/samples/*.json
    agenttracelab analyze data/samples --json reports.json
    agenttracelab trace data/samples --csv traces.csv
    agenttracelab formats
"""

from __future__ import annotations

import argparse
import sys

from . import __version__
from .analyzer import analyze_many
from .parsers import available_formats, load_conversations
from .report import rank_reports, render_table, reports_to_json, trace_to_csv


def _add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "paths",
        nargs="+",
        help="JSON log files, globs, or directories to load.",
    )
    parser.add_argument(
        "--format",
        dest="fmt",
        choices=available_formats(),
        default=None,
        help="Force a parser instead of auto-detecting.",
    )


def _load(args: argparse.Namespace):
    conversations = load_conversations(args.paths, fmt=args.fmt)
    if not conversations:
        print("No conversations found.", file=sys.stderr)
        raise SystemExit(2)
    return analyze_many(conversations)


def cmd_analyze(args: argparse.Namespace) -> int:
    reports = rank_reports(_load(args))
    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            fh.write(reports_to_json(reports, include_trace=args.with_trace))
        print(f"Wrote {len(reports)} report(s) to {args.json}")
    else:
        print(render_table(reports))
    return 0


def cmd_trace(args: argparse.Namespace) -> int:
    reports = _load(args)
    csv_text = trace_to_csv(reports)
    if args.csv:
        with open(args.csv, "w", encoding="utf-8") as fh:
            fh.write(csv_text)
        rows = sum(len(r.trace) for r in reports)
        print(f"Wrote {rows} trace rows to {args.csv}")
    else:
        sys.stdout.write(csv_text)
    return 0


def cmd_formats(_args: argparse.Namespace) -> int:
    for name in available_formats():
        print(name)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agenttracelab",
        description="Compare how different AI agents solve the same task.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_analyze = sub.add_parser("analyze", help="Compare agents in a table or JSON report.")
    _add_common(p_analyze)
    p_analyze.add_argument("--json", metavar="PATH", help="Write JSON report to PATH.")
    p_analyze.add_argument(
        "--with-trace",
        action="store_true",
        help="Include per-turn traces in the JSON report.",
    )
    p_analyze.set_defaults(func=cmd_analyze)

    p_trace = sub.add_parser("trace", help="Export per-turn traffic traces as CSV.")
    _add_common(p_trace)
    p_trace.add_argument("--csv", metavar="PATH", help="Write CSV to PATH (default: stdout).")
    p_trace.set_defaults(func=cmd_trace)

    p_formats = sub.add_parser("formats", help="List supported log formats.")
    p_formats.set_defaults(func=cmd_formats)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
