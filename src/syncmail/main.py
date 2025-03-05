#! /usr/bin/env python3

"""Async mail fetcher.. which is cool."""

import asyncio
import importlib.resources
import logging
import re
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import TypedDict

import click
from dotenv import dotenv_values


class Config(TypedDict):
    NEOMUTT_CHECK_INTERVAL: str
    NEOMUTT_LOG_FILE: str
    NEOMUTT_ACCOUNTS_PATH: str


try:
    if not Path(".syncmailenv").exists:
        raise FileNotFoundError("Could not find the `.syncmailenv` configuration file in the current directory.")
except FileNotFoundError as e:
    click.secho(str(e), fg="red")
    sys.exit(1)


config: Config = dotenv_values(".syncmailenv")  # type: ignore

try:
    if (
        not config.get("NEOMUTT_CHECK_INTERVAL")
        or not config.get("NEOMUTT_LOG_FILE")
        or not config.get("NEOMUTT_ACCOUNTS_PATH")
    ):
        raise ValueError(
            "Missing environment variables NEOMUTT_LOG_FILE, NEOMUTT_ACCOUNTS_PATH, or NEOMUTT_CHECK_INTERVAL. Are you executing the program from the directory that contains your configuration options file?"
        )
except ValueError as e:
    click.secho(str(e), fg="red")
    sys.exit(1)

background_tasks: set[asyncio.Task[None]] = set()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        RotatingFileHandler(
            config["NEOMUTT_LOG_FILE"],
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
        with importlib.resources.path("syncmail", "icon/neomutt.png") as filepath:
            res = re.search(r"pulled (\d) new message\(s\)", stdout.decode())
            if res and res.group(1).isdigit() and int(res.group(1)) > 0:
                _ = await asyncio.create_subprocess_exec(
                    "notify-send",
                    "-t",
                    "5000",
                    "-a",
                    f"New Mail in {channel}",
                    "-e",
                    "-i",
                    filepath,
                )
            logger.info(f"{channel} reports: {stdout.decode()}")
    if stderr:
        logger.error(f"{channel} reports error: {stderr.decode()}")
    logger.info(f"Done running {channel}")


async def execute():
    tasks: list[asyncio.Task[None]]
    tasks = [
        asyncio.create_task(run_mbsync(account_name.stem))
        for account_name in Path(config["NEOMUTT_ACCOUNTS_PATH"]).glob("*.muttrc")
    ]
    background_tasks.update(tasks)
    [task.add_done_callback(background_tasks.discard) for task in tasks]


async def oneshot(verbose: bool = False):
    if verbose:
        click.secho("Running syncmail", fg="blue", nl=False)

    await execute()

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
            await asyncio.sleep(int(config["NEOMUTT_CHECK_INTERVAL"]) / 2)
            # not too sure about this. It might not be neccessary.
            _ = await asyncio.create_subprocess_exec("notmuch", "new", "--quiet")
            await asyncio.sleep(int(config["NEOMUTT_CHECK_INTERVAL"]) / 2)
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
