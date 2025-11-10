import json
import logging
import sys
from enum import StrEnum
from pathlib import Path
from typing import Any, ClassVar

from loguru import logger
from pydantic_settings import BaseSettings, SettingsConfigDict


class LogLevel(StrEnum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LoggerSettings(BaseSettings):
    """Logger settings for the application."""

    LEVEL: LogLevel = LogLevel.INFO
    LEVEL_CONSOLE: LogLevel = LogLevel.DEBUG
    LEVEL_FILE: LogLevel = LogLevel.INFO

    LOG_FILE_PATH: Path = Path("logs/app.log")
    LOG_FILE_MAX_SIZE: str = "10 MB"
    LOG_FILE_RETENTION: str = "30 days"
    LOG_FILE_ENCODING: str = "utf-8"

    JSON_LOGS: bool = False
    INCLUDE_EXTRA: bool = True
    MULTILINE_EXTRA: bool = True

    LOG_REQUESTS: bool = True
    LOG_REQUEST_BODY: bool = False
    LOG_RESPONSE_BODY: bool = False
    REQUEST_ID_HEADER: str = "X-Request-ID"

    LOG_SLOW_REQUESTS: bool = True
    SLOW_REQUEST_THRESHOLD: float = 1.0

    model_config = SettingsConfigDict(
        env_file=Path(__file__).parents[3] / ".env",
        extra="ignore",
        env_prefix="LOGGER_",
    )


def _format_dict(value: dict, indent: int, prefix: str) -> str:
    if not value:
        return "<dim>{}</dim>"

    lines = []
    items = list(value.items())
    for i, (k, v) in enumerate(items):
        is_last_item = i == len(items) - 1
        branch = "└── " if is_last_item else "├── "
        extension = "    " if is_last_item else "│   "

        if isinstance(v, (dict, list)) and v:
            lines.append(f"{prefix}<dim>{branch}</dim><cyan>{k}</cyan><dim>:</dim>")
            lines.append(
                format_value(
                    v,
                    indent=indent + 1,
                    prefix=prefix + extension,
                ),
            )
        else:
            formatted_v = format_value(v, indent=0, prefix="")
            lines.append(f"{prefix}<dim>{branch}</dim><cyan>{k}</cyan><dim>:</dim> {formatted_v}")

    return "\n".join(lines)


def _format_list(value: list, indent: int, prefix: str) -> str:
    if not value:
        return "<dim>[]</dim>"

    lines = []
    for i, item in enumerate(value):
        is_last_item = i == len(value) - 1
        branch = "└── " if is_last_item else "├── "
        extension = "⠀⠀" if is_last_item else "│⠀⠀"

        if isinstance(item, (dict, list)) and item:
            lines.append(f"{prefix}<dim>{branch}[{i}]:</dim>")
            lines.append(
                format_value(
                    item,
                    indent=indent + 1,
                    prefix=prefix + extension,
                ),
            )
        else:
            formatted_item = format_value(item, indent=0, prefix="")
            lines.append(f"{prefix}<dim>{branch}</dim>{formatted_item}")

    return "\n".join(lines)


def format_value(value: Any, indent: int = 0, prefix: str = "") -> str:
    """Formats value with tree-like structure."""

    if isinstance(value, dict):
        return _format_dict(value, indent, prefix)
    if isinstance(value, list):
        return _format_list(value, indent, prefix)

    type_formatters = {
        str: lambda v: f'<white>"{v}"</white>' if " " in v or not v else f"<white>{v}</white>",
        bool: lambda v: f"<yellow>{str(v).lower()}</yellow>",
        type(None): lambda _: "<dim>null</dim>",
        int: lambda v: f"<magenta>{v}</magenta>",
        float: lambda v: f"<magenta>{v}</magenta>",
    }

    for type_cls, formatter in type_formatters.items():
        if isinstance(value, type_cls):
            return formatter(value)

    return f"<white>{value!s}</white>"


def multiline_formatter(record: Any) -> str:
    time_str = record["time"].strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    level = record["level"].name
    location = f"{record['name']}:{record['function']}:{record['line']}"

    level_colors = {
        "DEBUG": "cyan",
        "INFO": "green",
        "WARNING": "yellow",
        "ERROR": "red",
        "CRITICAL": "bold red",
    }
    level_color = level_colors.get(level, "white")

    main_line = (
        f"<dim>{time_str}</dim> | "
        f"<{level_color}>{level: <8}</{level_color}> | "
        f"<blue>{location}</blue> | "
        f"<level>{record['message']}</level>"
    )

    if record.get("extra"):
        extra_data = {k: v for k, v in record["extra"].items() if not k.startswith("_")}

        if extra_data:
            main_line += "\n<dim>└── extra:</dim>"
            formatted_extra = format_value(extra_data, indent=0, prefix="")
            formatted_extra = "\u200b\u200b\u200b" + formatted_extra.replace(
                "\n",
                "\n\u200b\u200b\u200b",
            )
            main_line += "\n" + formatted_extra

    if record.get("exception"):
        main_line += "\n<red>{exception}</red>"

    return main_line + "\n\n"


def json_formatter(record: Any) -> str:
    log_record = {
        "timestamp": record["time"].isoformat(),
        "elapsed": record["elapsed"].total_seconds(),
        "level": record["level"].name,
        "message": record["message"],
        "module": record["name"],
        "function": record["function"],
        "line": record["line"],
    }

    if record.get("extra"):
        extra_data = {k: v for k, v in record["extra"].items() if not k.startswith("_")}
        log_record.update(extra_data)

    if record.get("exception"):
        log_record["exception"] = str(record["exception"])

    return json.dumps(log_record, ensure_ascii=False)


class InterceptHandler(logging.Handler):
    _technical_fields: ClassVar[set[str]] = {
        "logger_name",
        "module",
        "function",
        "thread",
        "process",
    }

    def emit(self, record: logging.LogRecord) -> None:  # noqa: PLR6301
        if record.name.startswith("loguru"):
            return

        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = str(record.levelno)

        frame = logging.currentframe()
        depth = 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        tech_extra = {
            "logger_name": record.name,
            "module": record.module,
            "function": record.funcName,
            "thread": record.thread,
            "process": record.process,
        }

        record_extra = getattr(record, "__dict__", {}).get("extra", {}) or {}

        logger.opt(depth=depth, exception=record.exc_info).log(
            level,
            record.getMessage(),
            extra={"_technical_extra": tech_extra, **record_extra},
        )


app_logger = logger

_logging_configured = [False]
_setup_logging_call_count = [0]


def setup_logging(settings: LoggerSettings) -> None:
    """Setup structured logging with loguru."""

    _setup_logging_call_count[0] += 1
    caller_info = f" (call #{_setup_logging_call_count[0]})"

    if _logging_configured[0]:
        logger.debug(f"Logging already configured, skipping setup{caller_info}")
        return

    logger.remove()

    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    root_logger.handlers.clear()

    settings.LOG_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)

    if settings.MULTILINE_EXTRA:
        console_format = multiline_formatter
    else:
        console_format = (
            "<dim>{time:YYYY-MM-DD HH:mm:ss.SSS}</dim> | "
            "<level>{level: <8}</level> | "
            "<blue>{name}:{function}:{line}</blue> | "
            "<level>{message}</level>"
        )

    file_format = "" if settings.JSON_LOGS else console_format
    serialize_file = settings.JSON_LOGS

    logger.add(
        sys.stdout,
        level=settings.LEVEL_CONSOLE.value,
        format=console_format,
        serialize=False,
        colorize=True,
        enqueue=True,
        backtrace=True,
        diagnose=True,
    )

    logger.add(
        settings.LOG_FILE_PATH,
        level=settings.LEVEL_FILE.value,
        format=file_format,
        serialize=serialize_file,
        rotation=settings.LOG_FILE_MAX_SIZE,
        retention=settings.LOG_FILE_RETENTION,
        encoding=settings.LOG_FILE_ENCODING,
        enqueue=True,
        backtrace=True,
        diagnose=False,
    )

    logging.root.handlers = [InterceptHandler()]
    logging.root.setLevel(settings.LEVEL.value)

    for name in logging.root.manager.loggerDict:
        ext_logger = logging.getLogger(name)
        ext_logger.propagate = False
        ext_logger.handlers = [InterceptHandler()]
        ext_logger.setLevel(settings.LEVEL_FILE.value)

    noisy_libs = ["uvicorn", "uvicorn.access", "uvicorn.error", "fastapi", "asyncio"]
    for lib_name in noisy_libs:
        lib_logger = logging.getLogger(lib_name)
        lib_logger.handlers = [InterceptHandler()]
        lib_logger.propagate = False
        lib_logger.setLevel(logging.WARNING)

    _logging_configured[0] = True

    logger.opt(colors=True).info(f"<green>Logging initialized successfully</green>{caller_info}")
