"""
统一日志模块。

优先使用 loguru；未安装时退回标准 logging，保证项目仍可运行。
"""
import logging
import sys
from pathlib import Path
from types import SimpleNamespace

try:
    from loguru import logger as _loguru_logger
except ModuleNotFoundError:
    _loguru_logger = None

DEFAULT_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
    "<level>{message}</level>"
)
FILE_FORMAT = "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}"
STD_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s"


if _loguru_logger is not None:
    logger = _loguru_logger
    logger.remove()

    class InterceptHandler(logging.Handler):
        """
        拦截标准 logging 的输出，重定向到 loguru。
        """

        def emit(self, record):
            try:
                level = logger.level(record.levelname).name
            except ValueError:
                level = record.levelno

            frame, depth = logging.currentframe(), 2
            while frame and frame.f_code.co_filename == logging.__file__:
                frame = frame.f_back
                depth += 1

            logger.opt(depth=depth, exception=record.exc_info).log(
                level, record.getMessage()
            )


    def setup_logging(
        log_level: str = "INFO",
        log_dir: str = "logs",
        rotation: str = "00:00",
        retention: str = "10 days",
        compression: str = "zip",
        enable_console: bool = True,
        enable_file: bool = True,
    ):
        log_path = Path(log_dir)
        log_path.mkdir(exist_ok=True)

        logger.remove()

        if enable_console:
            logger.add(
                sys.stderr,
                level=log_level,
                format=DEFAULT_FORMAT,
                colorize=True,
                backtrace=True,
                diagnose=True,
            )

        if enable_file:
            logger.add(
                log_path / "app_{time:YYYY-MM-DD}.log",
                level=log_level,
                format=FILE_FORMAT,
                rotation=rotation,
                retention=retention,
                compression=compression,
                encoding="utf-8",
                enqueue=True,
                backtrace=True,
                diagnose=True,
            )
            logger.add(
                log_path / "error_{time:YYYY-MM-DD}.log",
                level="ERROR",
                format=FILE_FORMAT,
                rotation=rotation,
                retention=retention,
                compression=compression,
                encoding="utf-8",
                enqueue=True,
            )

        logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
        logging.getLogger("urllib3").setLevel(logging.WARNING)
        return logger


else:
    class _FallbackLogger:
        def __init__(self):
            self._logger = logging.getLogger("ImageEXIFStyler")

        def debug(self, message, *args, **kwargs):
            self._logger.debug(message, *args, **kwargs)

        def info(self, message, *args, **kwargs):
            self._logger.info(message, *args, **kwargs)

        def warning(self, message, *args, **kwargs):
            self._logger.warning(message, *args, **kwargs)

        def error(self, message, *args, **kwargs):
            self._logger.error(message, *args, **kwargs)

        def success(self, message, *args, **kwargs):
            self._logger.info(message, *args, **kwargs)

        def log(self, level, message, *args, **kwargs):
            self._logger.log(getattr(logging, str(level).upper(), logging.INFO), message, *args, **kwargs)

        def level(self, name):
            return SimpleNamespace(name=name)

        def opt(self, **kwargs):
            return self

        def remove(self, *args, **kwargs):
            return None

        def add(self, *args, **kwargs):
            return None


    logger = _FallbackLogger()

    def setup_logging(
        log_level: str = "INFO",
        log_dir: str = "logs",
        rotation: str = "00:00",
        retention: str = "10 days",
        compression: str = "zip",
        enable_console: bool = True,
        enable_file: bool = True,
    ):
        del rotation, retention, compression

        log_path = Path(log_dir)
        log_path.mkdir(exist_ok=True)

        root_logger = logging.getLogger()
        root_logger.handlers.clear()
        root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

        formatter = logging.Formatter(STD_FORMAT)

        if enable_console:
            console_handler = logging.StreamHandler(sys.stderr)
            console_handler.setFormatter(formatter)
            root_logger.addHandler(console_handler)

        if enable_file:
            app_handler = logging.FileHandler(log_path / "app.log", encoding="utf-8")
            app_handler.setFormatter(formatter)
            root_logger.addHandler(app_handler)

            error_handler = logging.FileHandler(log_path / "error.log", encoding="utf-8")
            error_handler.setLevel(logging.ERROR)
            error_handler.setFormatter(formatter)
            root_logger.addHandler(error_handler)

        logging.getLogger("urllib3").setLevel(logging.WARNING)
        return logger


def init_from_config(config):
    """
    从配置对象初始化日志系统。
    """
    debug_mode = config.getboolean("DEFAULT", "debug", fallback=False)
    log_level = "DEBUG" if debug_mode else "INFO"
    return setup_logging(log_level=log_level)


__all__ = ["logger", "setup_logging", "init_from_config"]
