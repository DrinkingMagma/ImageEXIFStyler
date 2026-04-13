"""
统一日志模块。

优先使用 loguru；未安装时退回标准 logging，保证项目仍可运行。
"""
import logging
import sys
from datetime import datetime
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
        compression=None,
        enable_console: bool = False,
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

        logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
        logging.getLogger("urllib3").setLevel(logging.WARNING)
        return logger


else:
    class _DailyFileHandler(logging.Handler):
        """
        标准 logging 的按天文件处理器。

        loguru 可直接用文件名中的时间占位和 rotation；fallback 下手动按日期切换，
        保持当前日志文件名为 app_YYYY-MM-DD.log。
        """

        def __init__(self, log_dir: Path, encoding: str = "utf-8"):
            super().__init__()
            self.log_dir = log_dir
            self.encoding = encoding
            self.current_date = None
            self._handler = None

        def _ensure_handler(self):
            today = datetime.now().strftime("%Y-%m-%d")
            if self._handler is not None and self.current_date == today:
                return

            if self._handler is not None:
                self._handler.close()

            self.current_date = today
            self._handler = logging.FileHandler(
                self.log_dir / f"app_{today}.log",
                encoding=self.encoding,
            )
            self._handler.setLevel(self.level)
            if self.formatter is not None:
                self._handler.setFormatter(self.formatter)

        def setLevel(self, level):
            super().setLevel(level)
            if self._handler is not None:
                self._handler.setLevel(level)

        def setFormatter(self, fmt):
            super().setFormatter(fmt)
            if self._handler is not None:
                self._handler.setFormatter(fmt)

        def emit(self, record):
            self._ensure_handler()
            self._handler.emit(record)

        def close(self):
            if self._handler is not None:
                self._handler.close()
                self._handler = None
            super().close()


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
        compression=None,
        enable_console: bool = False,
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
            app_handler = _DailyFileHandler(log_path, encoding="utf-8")
            app_handler.setFormatter(formatter)
            root_logger.addHandler(app_handler)

        logging.getLogger("urllib3").setLevel(logging.WARNING)
        return logger


def init_from_config(config):
    """
    从配置对象初始化日志系统。
    """
    debug_mode = config.getboolean("DEFAULT", "debug", fallback=False)
    log_level = "DEBUG" if debug_mode else "INFO"
    return setup_logging(log_level=log_level, enable_console=False)


__all__ = ["logger", "setup_logging", "init_from_config"]
