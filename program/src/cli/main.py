"""CLI entry point and Rich console event subscriber for xray-bench."""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path
from typing import Optional

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from rich.console import Console
from rich.markup import escape
from rich.panel import Panel
from rich.table import Table

from src.config import AppConfig, load_config
from src.database import Database
from src.events import (
    BatchCompleted,
    BatchProgress,
    BatchStarted,
    Event,
    EventBus,
    GitHubSyncStatus,
    LogMessage,
    NodeEliminated,
    NodeTestingStarted,
    RoundCompleted,
    RoundProgress,
    RoundStarted,
    TestCompleted,
    TestStarted,
)
from src.geo.ip_lookup import GeoLookupService
from src.parser.fingerprint import load_blacklist
from src.parser.uri_parser import ParsedNode, parse_uri
from src.publisher.github_sync import GitHubPublisher
from src.testers.http_tester import HttpLatencyTester, fetch_nodes_from_sources
from src.testers.speed_tournament import SpeedTournamentEngine
from src.xray.binary_manager import BinaryManager


class RichEventSubscriber:
    """Subscribes to EventBus and formats clean, rich terminal output."""

    def __init__(self, console: Optional[Console] = None) -> None:
        self.console = console or Console()

    def handle_event(self, event: Event) -> None:
        """Route event to appropriate display handler."""
        if isinstance(event, LogMessage):
            color = "cyan" if event.level == "INFO" else "yellow" if event.level == "WARNING" else "red"
            self.console.print(f"[{color}][{event.level}][/{color}] {escape(event.message)}")

        elif isinstance(event, TestStarted):
            self.console.print(
                Panel.fit(
                    f"[bold green]Starting {event.mode.upper()}[/bold green]\n"
                    f"Nodes to test: [bold cyan]{event.total_nodes}[/bold cyan]",
                    title="[bold yellow]xray-bench (xBench)[/bold yellow]",
                    border_style="cyan",
                )
            )

        elif isinstance(event, BatchStarted):
            self.console.print(
                f"[dim]── Batch {event.batch_index}/{event.total_batches} ({event.batch_size} nodes) ──[/dim]"
            )

        elif isinstance(event, NodeTestingStarted):
            proto = f"[{event.protocol.upper()}]" if event.protocol else ""
            self.console.print(
                f"  [cyan]⏳ Testing [{event.current}/{event.total}]:[/cyan] "
                f"[bold white]{escape(event.node_tag)}[/bold white] "
                f"({escape(event.address)}:{event.port}) {proto}..."
            )

        elif isinstance(event, BatchProgress):
            status_symbol = "[green]✓[/green]" if event.success else "[red]✗[/red]"
            self.console.print(
                f"  {status_symbol} [{event.current}/{event.total}] {escape(event.details)}"
            )

        elif isinstance(event, BatchCompleted):
            self.console.print(
                f"  [bold]Batch {event.batch_index} done:[/bold] "
                f"[green]{event.passed_count} passed[/green], [red]{event.failed_count} failed[/red]"
            )

        elif isinstance(event, RoundStarted):
            self.console.print(
                Panel.fit(
                    f"[bold yellow]🏆 Tournament Round {event.round_num}[/bold yellow]\n"
                    f"Active pool size: [bold cyan]{event.pool_size}[/bold cyan] nodes",
                    border_style="yellow",
                )
            )

        elif isinstance(event, RoundProgress):
            symbol = "[green]✓[/green]" if event.success else "[red]✗[/red]"
            speed_str = f"{event.speed_mbps:.2f} Mbps" if event.speed_mbps > 0 else "0.00 Mbps (Failed)"
            tag_display = event.node_tag if event.node_tag else f"ID: {event.node_id[:8]}"
            self.console.print(
                f"  {symbol} [{event.completed}/{event.total}] Speed: {speed_str} ({escape(tag_display)})"
            )

        elif isinstance(event, RoundCompleted):
            self.console.print(
                f"  [bold]Round {event.round_num} Result:[/bold] "
                f"[green]{event.passed_count} survived[/green], "
                f"[yellow]{event.eliminated_count} bottom-third eliminated[/yellow], "
                f"[red]{event.failed_count} failed[/red]"
            )

        elif isinstance(event, NodeEliminated):
            self.console.print(f"  [dim yellow]↪ Eliminated ({event.node_id[:8]}): {escape(event.reason)}[/dim yellow]")

        elif isinstance(event, GitHubSyncStatus):
            if event.status == "SUCCESS":
                self.console.print(f"[bold green]✔ GitHub Sync:[/bold green] {escape(event.message)}")
                if event.url:
                    self.console.print(f"  [cyan]URL:[/cyan] {escape(event.url)}")
            elif event.status == "SKIPPED":
                self.console.print(f"[dim yellow]ℹ GitHub Sync:[/dim yellow] {escape(event.message)}")
            elif event.status == "ERROR":
                self.console.print(f"[bold red]✗ GitHub Sync Error:[/bold red] {escape(event.message)}")
            else:
                self.console.print(f"[cyan]ℹ GitHub Sync:[/cyan] {escape(event.message)}")

        elif isinstance(event, TestCompleted):
            table = Table(title="Test Execution Summary", border_style="green")
            table.add_column("Metric", style="bold cyan")
            table.add_column("Value", style="bold white")
            table.add_row("Execution Mode", event.mode)
            table.add_row("Total Initial Nodes", str(event.total_nodes))
            table.add_row("Total Passing Nodes", str(event.passed_nodes))
            table.add_row("Elapsed Time", f"{event.duration_sec:.2f} seconds")
            self.console.print(table)


async def run_http_test_cli(args: argparse.Namespace, config: AppConfig, event_bus: EventBus) -> None:
    """Execute Mode 1 CLI workflow."""
    _setup_asyncio_exception_handler()
    # Apply CLI performance overrides
    if getattr(args, "fast", False):
        config.xray.batch_size = args.batch_size or 80
        config.http_test.timeout_sec = 6.0
        config.http_test.warmup_requests = 0
        config.geo.check_google_country = False
    elif getattr(args, "batch_size", None):
        config.xray.batch_size = args.batch_size

    if getattr(args, "timeout", None):
        config.http_test.timeout_sec = args.timeout

    if getattr(args, "skip_google", False):
        config.geo.check_google_country = False

    bin_manager = BinaryManager(bin_dir=config.paths.bin_dir, event_bus=event_bus)
    xray_binary = bin_manager.ensure_binary()

    db = Database(config.paths.database_path)
    blacklist = load_blacklist(config.paths.blacklist_file)
    geo_service = GeoLookupService(
        db=db,
        cache_ttl_days=config.geo.cache_ttl_days,
        blocked_google_countries=config.geo.blocked_google_countries,
        check_google=config.geo.check_google_country,
        primary_api_url=config.geo.primary_api_url,
        backup_api_urls=config.geo.backup_api_urls,
        google_check_url=config.geo.google_check_url,
        google_fallback_url=config.geo.google_fallback_url,
        event_bus=event_bus,
    )

    source_type = args.source
    input_file = Path(args.input) if args.input else config.paths.custom_nodes_file

    nodes = await fetch_nodes_from_sources(
        source_type=source_type,
        file_path=input_file,
        subs_path=config.paths.subscriptions_file,
        blacklist=blacklist,
        event_bus=event_bus,
    )

    if getattr(args, "limit", None) and args.limit > 0:
        event_bus.log(f"Applying --limit {args.limit} to pool of {len(nodes)} nodes.", level="INFO")
        nodes = nodes[: args.limit]

    if not nodes:
        event_bus.log("No valid nodes found to test. Exiting.", level="WARNING")
        return

    tester = HttpLatencyTester(
        config=config,
        db=db,
        geo_service=geo_service,
        xray_binary=xray_binary,
        event_bus=event_bus,
    )

    passed_nodes = await tester.run(nodes)
    event_bus.log(
        f"Wrote {len(passed_nodes)} tested nodes to {config.paths.output_http_file}",
        level="INFO",
    )

    if args.push:
        publisher = GitHubPublisher(
            token=config.github.token,
            repo=config.github.repo,
            branch=config.github.branch,
            commit_prefix=config.github.commit_message_prefix,
            event_bus=event_bus,
        )
        await publisher.publish_file(config.paths.output_http_file)


async def run_speed_test_cli(args: argparse.Namespace, config: AppConfig, event_bus: EventBus) -> None:
    """Execute Mode 2 CLI workflow."""
    _setup_asyncio_exception_handler()
    if getattr(args, "batch_size", None):
        config.xray.batch_size = args.batch_size

    bin_manager = BinaryManager(bin_dir=config.paths.bin_dir, event_bus=event_bus)
    xray_binary = bin_manager.ensure_binary()

    db = Database(config.paths.database_path)
    blacklist = load_blacklist(config.paths.blacklist_file)
    geo_service = GeoLookupService(
        db=db,
        cache_ttl_days=config.geo.cache_ttl_days,
        blocked_google_countries=config.geo.blocked_google_countries,
        check_google=config.geo.check_google_country,
        primary_api_url=config.geo.primary_api_url,
        backup_api_urls=config.geo.backup_api_urls,
        google_check_url=config.geo.google_check_url,
        google_fallback_url=config.geo.google_fallback_url,
        event_bus=event_bus,
    )

    source_type = args.source
    raw_nodes: list[ParsedNode] = []

    if source_type == "http-output":
        http_out = Path(args.input or config.paths.output_http_file)
        if http_out.is_file():
            with open(http_out, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    p = parse_uri(line.strip())
                    if p:
                        raw_nodes.append(p)
        else:
            event_bus.log(
                f"HTTP output file not found: {http_out}. Run 'http-test' first or select another source.",
                level="ERROR",
            )
            return

    elif source_type == "custom":
        custom_file = Path(args.input or config.paths.custom_nodes_file)
        if custom_file.is_file():
            with open(custom_file, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    p = parse_uri(line.strip())
                    if p:
                        raw_nodes.append(p)
        else:
            event_bus.log(f"Custom file not found: {custom_file}", level="ERROR")
            return

    elif source_type == "db":
        active_records = db.get_active_nodes()
        for rec in active_records:
            p = parse_uri(rec.raw_uri)
            if p:
                raw_nodes.append(p)

    seen_ids = set()
    nodes: list[ParsedNode] = []
    for n in raw_nodes:
        if n.node_id in seen_ids or n.node_id in blacklist:
            continue
        seen_ids.add(n.node_id)
        nodes.append(n)

    if getattr(args, "limit", None) and args.limit > 0:
        event_bus.log(f"Applying --limit {args.limit} to speed tournament pool.", level="INFO")
        nodes = nodes[: args.limit]

    if not nodes:
        event_bus.log("No active nodes available for tournament test.", level="WARNING")
        return

    tournament = SpeedTournamentEngine(
        config=config,
        db=db,
        geo_service=geo_service,
        xray_binary=xray_binary,
        event_bus=event_bus,
    )

    survivors = await tournament.run_tournament(nodes)
    event_bus.log(
        f"Wrote {len(survivors)} ranked nodes to {config.paths.output_speed_file}",
        level="INFO",
    )

    if args.push:
        publisher = GitHubPublisher(
            token=config.github.token,
            repo=config.github.repo,
            branch=config.github.branch,
            commit_prefix=config.github.commit_message_prefix,
            event_bus=event_bus,
        )
        await publisher.publish_file(config.paths.output_speed_file)


def run_stats_cli(config: AppConfig, event_bus: EventBus) -> None:
    """Display intelligence database summary stats."""
    db = Database(config.paths.database_path)
    active_nodes = db.get_active_nodes()
    console = Console()

    table = Table(title="xray-bench Database Statistics", border_style="cyan")
    table.add_column("Tag", style="bold yellow", no_wrap=True)
    table.add_column("Node ID", style="dim yellow")
    table.add_column("Country / ISP", style="cyan")
    table.add_column("Score", style="bold green", justify="right")
    table.add_column("Rank", style="white", justify="right")
    table.add_column("Last Speed (Mbps)", style="magenta", justify="right")
    table.add_column("Zero Runs", style="red", justify="right")

    from src.geo.ip_lookup import format_country_with_flag
    for node in active_nodes[:25]:
        loc_disp = format_country_with_flag(node.geo_country) if node.geo_country else "XX"
        if node.google_country and node.google_country != node.geo_country:
            loc_disp += f" (or {format_country_with_flag(node.google_country)})"
        isp_disp = f"{loc_disp} - {node.isp[:15]}" if node.geo_country else "Unknown"
        speed_disp = f"{node.last_speed_mbps:.2f}" if node.last_speed_mbps is not None else "-"
        tag_disp = f"xBench-{node.seq_id:04d}" if node.seq_id > 0 else "xBench-0000"
        table.add_row(
            tag_disp,
            node.node_id[:10],
            isp_disp,
            f"{node.cumulative_score}pts",
            str(node.current_tournament_rank),
            speed_disp,
            str(node.consecutive_zero_runs),
        )

    console.print(table)
    console.print(f"[bold]Total Active (Non-Dead) Nodes in DB:[/bold] {len(active_nodes)}")


def build_parser() -> argparse.ArgumentParser:
    """Build CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="xray-bench",
        description="xray-bench: Production-grade V2Ray/Xray proxy benchmark and tournament ranking engine.",
    )
    parser.add_argument(
        "--config",
        "-c",
        type=str,
        default="config.yaml",
        help="Path to YAML configuration file (default: config.yaml)",
    )

    subparsers = parser.add_subparsers(dest="command", required=True, help="Sub-commands")

    # http-test
    p_http = subparsers.add_parser("http-test", help="Mode 1: Real HTTP connectivity and latency tester")
    p_http.add_argument(
        "--source",
        choices=["subs", "file"],
        default="subs",
        help="Node input source: 'subs' (subscriptions.txt) or 'file' (custom_nodes.txt)",
    )
    p_http.add_argument(
        "--input",
        "-i",
        type=str,
        default=None,
        help="Custom file path when --source file is selected",
    )
    p_http.add_argument(
        "--limit",
        "-n",
        type=int,
        default=None,
        help="Limit number of nodes to test (e.g. --limit 100)",
    )
    p_http.add_argument(
        "--batch-size",
        "-b",
        type=int,
        default=None,
        help="Override batch size (e.g. --batch-size 80)",
    )
    p_http.add_argument(
        "--timeout",
        "-t",
        type=float,
        default=None,
        help="HTTP ping timeout in seconds (default: 2.0s)",
    )
    p_http.add_argument(
        "--fast",
        action="store_true",
        help="Fast mode: 0 warmup requests, 2.0s timeout, batch size 80, fast GeoIP without YouTube check",
    )
    p_http.add_argument(
        "--skip-google",
        action="store_true",
        help="Skip heavy YouTube / Google Country check (rely on fast GeoIP)",
    )
    p_http.add_argument(
        "--push",
        action="store_true",
        help="Push output/nodes_http.txt to GitHub repository after completion",
    )

    # speed-test
    p_speed = subparsers.add_parser("speed-test", help="Mode 2: Iterative tournament speed test engine")
    p_speed.add_argument(
        "--source",
        choices=["http-output", "custom", "db"],
        default="http-output",
        help="Node input source: 'http-output' (nodes_http.txt), 'custom', or 'db'",
    )
    p_speed.add_argument(
        "--input",
        "-i",
        type=str,
        default=None,
        help="Custom file path when --source custom or --source http-output is selected",
    )
    p_speed.add_argument(
        "--limit",
        "-n",
        type=int,
        default=None,
        help="Limit number of nodes for speed tournament (e.g. --limit 50)",
    )
    p_speed.add_argument(
        "--batch-size",
        "-b",
        type=int,
        default=None,
        help="Override batch size for speed tournament",
    )
    p_speed.add_argument(
        "--timeout",
        "-t",
        type=float,
        default=None,
        help="Speed test download timeout in seconds (default: 5.0s)",
    )
    p_speed.add_argument(
        "--push",
        action="store_true",
        help="Push output/nodes_speed.txt to GitHub repository after completion",
    )

    # stats
    subparsers.add_parser("stats", help="Display cached node intelligence and statistics")

    return parser


def _setup_asyncio_exception_handler(loop: Optional[asyncio.AbstractEventLoop] = None) -> None:
    """Silence benign Windows IOCP connection reset errors during shutdown or cancellation."""
    try:
        if loop is None:
            loop = asyncio.get_running_loop()
        def _silent_handler(loop, context):
            exc = context.get("exception")
            msg = context.get("message", "")
            if isinstance(exc, (ConnectionResetError, ConnectionAbortedError, BrokenPipeError, OSError)):
                return
            if "closed" in msg.lower() or "overlapped" in msg.lower():
                return
            loop.default_exception_handler(context)
        loop.set_exception_handler(_silent_handler)
    except Exception:
        pass


def main() -> None:
    """Main CLI execution entry point."""
    parser = build_parser()
    args = parser.parse_args()

    config = load_config(args.config)
    event_bus = EventBus()
    subscriber = RichEventSubscriber()
    event_bus.subscribe_all(subscriber.handle_event)

    try:
        if args.command == "http-test":
            asyncio.run(run_http_test_cli(args, config, event_bus))
        elif args.command == "speed-test":
            if getattr(args, "timeout", None):
                config.speed_test.timeout_sec = args.timeout
            asyncio.run(run_speed_test_cli(args, config, event_bus))
        elif args.command == "stats":
            run_stats_cli(config, event_bus)
    except KeyboardInterrupt:
        subscriber.console.print("\n[yellow]Execution interrupted by user.[/yellow]")
        sys.exit(130)
    except Exception as e:
        subscriber.console.print(f"[bold red]Fatal Error:[/bold red] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
