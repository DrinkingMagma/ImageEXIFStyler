from __future__ import annotations

import traceback
from typing import Optional

from core.logger import logger
from UI.editor.constants import PREVIEW_MAX_DIMENSION
from UI.shared.logging_utils import format_log_message
from UI.shared.qt import QObject, Signal
from UI.shared.render_service import TemplateRenderService
from UI.shared.utils import pil_to_qimage


class PreviewWorker(QObject):
    finished = Signal(int, object, object)
    failed = Signal(int, str)

    def __init__(self, token: int, input_path: str, template_name: str):
        super().__init__()
        self.token = token
        self.input_path = input_path
        self.template_name = template_name

    def run(self):
        try:
            service = TemplateRenderService()
            exif_data = service.get_exif_data(self.input_path)
            image = service.render_preview(
                self.input_path,
                self.template_name,
                exif_data=exif_data,
                max_dimension=PREVIEW_MAX_DIMENSION,
            )
            meta = {
                "template": self.template_name,
                "resolution": f"{image.width}x{image.height}",
            }
            self.finished.emit(self.token, pil_to_qimage(image), meta)
        except Exception as exc:
            logger.error(
                format_log_message(
                    "Preview failed",
                    {
                        "source": self.input_path,
                        "template": self.template_name,
                        "error": exc,
                    },
                    {"traceback": traceback.format_exc()},
                )
            )
            self.failed.emit(self.token, str(exc))


class ExportWorker(QObject):
    finished = Signal(str)
    failed = Signal(str)

    def __init__(
        self,
        input_path: str,
        template_name: str,
        output_path: str,
        quality: Optional[int] = None,
        subsampling: Optional[int] = None,
    ):
        super().__init__()
        self.input_path = input_path
        self.template_name = template_name
        self.output_path = output_path
        self.quality = quality
        self.subsampling = subsampling

    def run(self):
        try:
            service = TemplateRenderService()
            output_path = service.export_image(
                self.input_path,
                self.template_name,
                self.output_path,
                quality=self.quality,
                subsampling=self.subsampling,
            )
            self.finished.emit(output_path)
        except Exception as exc:
            logger.error(
                format_log_message(
                    "Export worker failed",
                    {
                        "source": self.input_path,
                        "output": self.output_path,
                        "template": self.template_name,
                        "quality": self.quality if self.quality is not None else "default",
                        "error": exc,
                    },
                    {"traceback": traceback.format_exc()},
                )
            )
            self.failed.emit(str(exc))
