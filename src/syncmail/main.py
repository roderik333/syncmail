#! /usr/bin/env python3

"""Async mail fetcher.. which is cool."""

import asyncio
import logging
import os
import re
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path

import click
from dotenv import load_dotenv

load_dotenv()

LOG_FILE = os.getenv("LOG_FILE", "")
ACCOUNTS_PATH = Path(os.getenv("ACCOUNTS_PATH", ""))
INTERVAL = int(os.getenv("INTERVAL", "0"))

if not INTERVAL or not LOG_FILE or not ACCOUNTS_PATH:
    raise ValueError("Missing environment variables LOG_FILE, ACCOUNTS_PATH, or INTERVAL")

background_tasks: set[asyncio.Task[None]] = set()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        RotatingFileHandler(
            LOG_FILE,
            maxBytes=1024 * 1024,  # 1 MB
            backupCount=5,
        ),
    ],
)
logger = logging.getLogger(__name__)


async def run_mbsync(channel: str):
    logger.info(f"Running mbsync for {channel}")
    mb = await asyncio.create_subprocess_exec(
        "mbsync",
        channel,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await mb.communicate()
    if stdout:
        res = re.search(r"pulled (\d) new message\(s\)", stdout.decode())
        if res and res.group(1).isdigit() and int(res.group(1)) > 0:
            _ = await asyncio.create_subprocess_exec(
                "notify-send",
                "-t",
                "5000",
                "-i",
                "/home/roderik/Pictures/neomutt.png",
                f"{res.group(1)} new mail in {channel}",
            )
        logger.info(f"{channel} reports: {stdout.decode()}")
    if stderr:
        logger.error(f"{channel} reports error: {stderr.decode()}")
    logger.info(f"Done running {channel}")


async def execute():
    tasks: list[asyncio.Task[None]]
    tasks = [asyncio.create_task(run_mbsync(account_name.stem)) for account_name in ACCOUNTS_PATH.glob("*.muttrc")]
    background_tasks.update(tasks)
    [task.add_done_callback(background_tasks.discard) for task in tasks]


async def oneshot(verbose: bool = False):
    if verbose:
        click.secho("Running syncmail", fg="blue", nl=False)
    _ = await execute()
    if verbose:
        click.echo("\r", nl=False)
        click.secho("Running syncmail completed", fg="green")


async def main():
    click.secho(
        f"Starting mail fetcher at {datetime.now().strftime('%d.%m.%y %H:%M:%S')}",
        fg="green",
        nl=False,
    )
    try:
        await execute()
        while True:
            await asyncio.sleep(150)
            # not too sure about this. It might not be neccessary.
            _ = await asyncio.create_subprocess_exec("notmuch", "new", "--quiet")
            await asyncio.sleep(150)
            await execute()
            click.secho("\r", nl=False)
            click.secho(
                f"In mail fetcher loop. Last check at {datetime.now().strftime('%d.%m.%y %H:%M:%S')}",
                fg="blue",
                nl=False,
            )
    except (KeyboardInterrupt, asyncio.exceptions.CancelledError):
        pass
    finally:
        logger.info("Shutting down...")
        for task in background_tasks:
            _ = task.cancel()
        _ = await asyncio.gather(*background_tasks, return_exceptions=True)
        logger.info("Shutdown completed.")


@click.command(help="Run the mail fetcher indefinitely.")
def infinite_loop():
    asyncio.run(main())


@click.command(help="one shot execution of sync mail. Use --verbose to get output to terminal.")
@click.option("--verbose", is_flag=True, help="Enable verbose output")
def one_shot(verbose: bool):
    asyncio.run(oneshot(verbose))


@click.group(help="General commands")
def cli() -> None:
    pass


cli.add_command(one_shot)
cli.add_command(infinite_loop)
