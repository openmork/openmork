"""CLI entry point for the openmork ACP adapter.

Loads environment variables from ``~/.openmork/.env``, configures logging
to write to stderr (so stdout is reserved for ACP JSON-RPC transport),
and starts the ACP agent server.

Usage::

    python -m acp_adapter.entry
    # or
    openmork acp
    # or
    openmork-acp
"""

import asyncio
import logging
import os
import sys
from pathlib import Path


def _setup_logging() -> None:
    """Route all logging to stderr so stdout stays clean for ACP stdio."""
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.INFO)

    # Quiet down noisy libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)


def _load_env() -> None:
    """Load .env from OPENMORK_HOME (default ``~/.openmork``)."""
    from openmork_cli.env_loader import load_openmork_dotenv

    openmork_home = Path(os.getenv("OPENMORK_HOME", Path.home() / ".openmork"))
    loaded = load_openmork_dotenv(openmork_home=openmork_home)
    if loaded:
        for env_file in loaded:
            logging.getLogger(__name__).info("Loaded env from %s", env_file)
    else:
        logging.getLogger(__name__).info(
            "No .env found at %s, using system env", openmork_home / ".env"
        )


def main() -> None:
    """Entry point: load env, configure logging, run the ACP agent."""
    _setup_logging()
    _load_env()

    logger = logging.getLogger(__name__)
    logger.info("Starting openmork ACP adapter")

    # Ensure the project root is on sys.path so ``from run_agent import AIAgent`` works
    project_root = str(Path(__file__).resolve().parent.parent)
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    import acp
    from .server import OPENMORKACPAgent

    agent = OPENMORKACPAgent()
    try:
        asyncio.run(acp.run_agent(agent))
    except KeyboardInterrupt:
        logger.info("Shutting down (KeyboardInterrupt)")
    except Exception:
        logger.exception("ACP agent crashed")
        sys.exit(1)


if __name__ == "__main__":
    main()
