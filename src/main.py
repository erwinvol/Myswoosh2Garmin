"""CLI and daemon entrypoint for Myswoosh2Garmin service."""

import argparse
import locale
import logging
import signal
import sys
import time
from datetime import datetime

from src.config import Config
from src.garmin_client import format_local_datetime
from src.sync_engine import SyncEngine

try:
    locale.setlocale(locale.LC_TIME, "")
except Exception:
    pass


def setup_logging(log_level: str = "INFO") -> None:
    """Configure console logging format."""
    level = getattr(logging, log_level.upper(), logging.INFO)
    log_format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    logging.basicConfig(level=level, format=log_format, stream=sys.stdout)


def parse_args() -> argparse.ArgumentParser:
    """Configure command line arguments."""
    parser = argparse.ArgumentParser(
        prog="Myswoosh2Garmin",
        description="Sync MyWhoosh activities to Garmin Connect with FIT device enhancement.",
    )
    parser.add_argument(
        "--daemon",
        action="store_true",
        help="Run continuously in background daemon mode polling periodically.",
    )
    parser.add_argument(
        "--interval",
        type=int,
        metavar="MINUTES",
        help="Interval between sync cycles in minutes (default from config or 15m).",
    )
    parser.add_argument(
        "--sync-latest",
        action="store_true",
        help="Synchronize only the single latest activity.",
    )
    parser.add_argument(
        "--batch",
        type=int,
        metavar="COUNT",
        help="Number of recent activities to inspect (overrides SYNC_BATCH_SIZE).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate execution without modifying Garmin Connect or persisting state.",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Display recent sync history and statistics from the database.",
    )
    return parser


def main() -> int:
    """Main execution entry point."""
    args = parse_args().parse_args()

    # Graceful shutdown handler for Docker SIGTERM
    stop_requested = False

    def handle_signal(sig, frame):
        nonlocal stop_requested
        logging.info("Received termination signal (%s). Shutting down cleanly...", sig)
        stop_requested = True

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    try:
        config = Config.from_env()
    except Exception as exc:
        print(f"Configuration Error: {exc}", file=sys.stderr)
        return 1

    setup_logging(config.log_level)
    logger = logging.getLogger("Myswoosh2Garmin")
    logger.info("Initializing Myswoosh2Garmin service...")

    engine = SyncEngine(config=config)

    # Status mode
    if args.status:
        recent = engine.store.get_recent_synced(limit=15)
        total = engine.store.count()
        print(f"\nTotal activities tracked: {total}")
        print("Recent sync history:")
        print(f"{'MyWhoosh ID':<16} {'Date':<24} {'Status':<18} {'Name'}")
        print("-" * 80)
        for row in recent:
            date_str = format_local_datetime(row.get("activity_date"))
            print(
                f"{str(row['mywhoosh_id']):<16} "
                f"{date_str:<24} "
                f"{str(row['garmin_status']):<18} "
                f"{str(row.get('name') or '')}"
            )
        return 0

    batch_size = 1 if args.sync_latest else (args.batch or config.sync_batch_size)

    # Daemon mode
    if args.daemon:
        interval_minutes = args.interval or config.sync_interval_minutes
        interval_seconds = max(60, interval_minutes * 60)
        logger.info(
            "Entering daemon mode. Polling interval: %d minutes (%d seconds).",
            interval_minutes,
            interval_seconds,
        )

        while not stop_requested:
            try:
                engine.run_sync(limit=batch_size, dry_run=args.dry_run)
            except Exception as exc:
                logger.exception("Unexpected error during sync cycle: %s", exc)

            logger.info("Sleeping for %d minutes until next sync cycle...", interval_minutes)

            # Sleep in 1-second chunks to respond quickly to SIGTERM
            for _ in range(interval_seconds):
                if stop_requested:
                    break
                time.sleep(1)

        logger.info("Daemon stopped gracefully.")
        return 0

    # One-off run
    stats = engine.run_sync(limit=batch_size, dry_run=args.dry_run)
    return 1 if stats["failed"] > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
