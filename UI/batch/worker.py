from __future__ import annotations

import os
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Optional

from PIL import Image

from core.logger import logger
from UI.batch.models import build_batch_output_filename, build_batch_output_path
from UI.shared.logging_utils import format_log_message
from UI.shared.qt import QObject, Signal
from UI.shared.render_service import TemplateRenderService
from UI.shared.utils import format_duration


class BatchProcessWorker(QObject):
    item_progress = Signal(int, int, str)
    item_complete = Signal(int, str, str, int)
    item_skipped = Signal(int, str)
    item_failed = Signal(int, str)
    overall_progress = Signal(int, int, int, str)
    status_message = Signal(str)
    finished = Signal(dict)

    def __init__(
        self,
        input_paths: list[str],
        template_name: str,
        output_root: str,
        quality: int,
        subsampling: int,
        override_existing: bool,
        common_root: Optional[Path],
        max_workers: Optional[int] = None,
        extension: str = ".jpg",
    ):
        super().__init__()
        self.input_paths = input_paths
        self.template_name = template_name
        self.output_root = output_root
        self.quality = quality
        self.subsampling = subsampling
        self.override_existing = override_existing
        self.common_root = common_root
        self.max_workers = max_workers or self.recommended_worker_count(len(input_paths))
        self.extension = extension if extension.startswith(".") else f".{extension}"

    @staticmethod
    def recommended_worker_count(total: int) -> int:
        cpu_count = os.cpu_count() or 1
        if total <= 1 or cpu_count <= 2:
            return 1
        return min(total, max(1, cpu_count - 1), 4)

    def _eta_text(self, started_at: float, processed: int, total: int) -> str:
        if processed <= 0 or processed >= total:
            return "00:00"
        elapsed = time.perf_counter() - started_at
        average = elapsed / processed
        return format_duration(average * (total - processed))

    def _process_item(self, index: int, input_path: str) -> dict:
        output_path = build_batch_output_path(input_path, self.output_root, self.common_root)
        output_path = output_path.with_name(
            build_batch_output_filename(output_path, self.template_name, self.quality, self.extension)
        )
        self.item_progress.emit(index, 6, "准备处理")

        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            if output_path.exists() and not self.override_existing:
                logger.info(
                    format_log_message(
                        "Export skipped",
                        {
                            "source": Path(input_path).resolve(),
                            "output": output_path.resolve(),
                            "template": self.template_name,
                            "quality": self.quality,
                            "reason": "output_exists",
                        },
                    )
                )
                return {
                    "status": "skipped",
                    "output_path": str(output_path),
                }

            service = TemplateRenderService()
            exif_data = service.get_exif_data(input_path)
            self.item_progress.emit(index, 28, "读取 EXIF")
            self.item_progress.emit(index, 58, "渲染模板")
            rendered_path = service.export_image(
                input_path=input_path,
                template_name=self.template_name,
                output_path=str(output_path),
                exif_data=exif_data,
                quality=self.quality,
                subsampling=self.subsampling,
            )
            output_path = Path(rendered_path)
            self.item_progress.emit(index, 88, "写入文件")
            with Image.open(output_path) as rendered_image:
                resolution = f"{rendered_image.width}x{rendered_image.height}"
            return {
                "status": "success",
                "output_path": str(output_path),
                "resolution": resolution,
                "output_size": output_path.stat().st_size,
            }
        except Exception as exc:
            logger.error(
                format_log_message(
                    "Batch export failed",
                    {
                        "source": Path(input_path).resolve(),
                        "output": output_path.resolve(),
                        "template": self.template_name,
                        "quality": self.quality,
                        "error": exc,
                    },
                    {"traceback": traceback.format_exc()},
                )
            )
            return {
                "status": "failed",
                "error_message": str(exc),
            }

    def run(self):
        total = len(self.input_paths)
        success_count = 0
        skipped_count = 0
        failure_count = 0
        started_at = time.perf_counter()
        worker_count = self.max_workers

        self.status_message.emit(f"状态：批量处理中 | 模板：{self.template_name} | 并发：{worker_count} 线程")

        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            futures = {
                executor.submit(self._process_item, index, input_path): index
                for index, input_path in enumerate(self.input_paths)
            }
            for future in as_completed(futures):
                index = futures[future]
                try:
                    result = future.result()
                except Exception as exc:
                    input_path = self.input_paths[index] if index < len(self.input_paths) else "<unknown>"
                    logger.error(
                        format_log_message(
                            "Batch future failed",
                            {
                                "source": Path(input_path).resolve() if input_path != "<unknown>" else input_path,
                                "template": self.template_name,
                                "quality": self.quality,
                                "error": exc,
                            },
                            {"traceback": traceback.format_exc()},
                        )
                    )
                    result = {"status": "failed", "error_message": str(exc)}

                status = result["status"]
                if status == "success":
                    success_count += 1
                    self.item_complete.emit(
                        index,
                        result["output_path"],
                        result["resolution"],
                        result["output_size"],
                    )
                elif status == "skipped":
                    skipped_count += 1
                    self.item_skipped.emit(index, result["output_path"])
                else:
                    failure_count += 1
                    self.item_failed.emit(index, result.get("error_message", "Unknown error"))

                processed = success_count + skipped_count + failure_count
                next_index = min(processed + 1, total) if processed < total else total
                self.overall_progress.emit(
                    processed,
                    total,
                    next_index,
                    self._eta_text(started_at, processed, total),
                )

        self.finished.emit(
            {
                "total": total,
                "success": success_count,
                "skipped": skipped_count,
                "failed": failure_count,
                "elapsed": time.perf_counter() - started_at,
                "workers": worker_count,
            }
        )
