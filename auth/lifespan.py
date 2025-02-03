import contextlib
from collections.abc import AsyncGenerator
from typing import Any, TypedDict

from fastapi import FastAPI

from auth import __version__, tasks
from auth.db.main import create_main_async_session_maker, create_main_engine
from auth.logger import init_logger, logger
from auth.services.posthog import get_server_id
from auth.settings import settings


class LifespanState(TypedDict):
    main_async_session_maker: Any
    server_id: str


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[LifespanState, None]:
    init_logger()

    main_engine = create_main_engine()

    logger.info("Auth Server started", version=__version__)

    if settings.telemetry_enabled:
        logger.warning(
            "Telemetry is enabled.\n"
            "We will collect data to better understand how Auth is used and improve the project.\n"
            "You can opt-out by setting the environment variable `TELEMETRY_ENABLED=false`.\n"
            "Read more about Auth's telemetry here: https://docs.auth.dev/telemetry"
        )
        tasks.send_task(tasks.heartbeat)

    yield {
        "main_async_session_maker": create_main_async_session_maker(main_engine),
        "server_id": get_server_id(),
    }

    await main_engine.dispose()

    logger.info("Auth Server stopped")
