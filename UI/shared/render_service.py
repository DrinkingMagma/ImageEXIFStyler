from __future__ import annotations

import json
import os
import tempfile
from copy import deepcopy
from pathlib import Path
from typing import Optional

from PIL import Image, ImageOps

from UI.shared.paths import configure_project_root

configure_project_root()

from core.configs import load_config
from core.logger import init_from_config
from core.util import get_template_path
from processor import ensure_processors_registered
from processor.core import start_process
from UI.shared.utils import get_cached_exif, get_cached_template, get_file_signature


class TemplateRenderService:
    _logging_ready = False
    _PREVIEW_PIXEL_KEYS = {
        "border_radius",
        "bottom_margin",
        "blur_radius",
        "center_logo_height",
        "delimiter_width",
        "height",
        "left_margin",
        "middle_spacing",
        "padding",
        "right_margin",
        "shadow_radius",
        "spacing",
        "text_spacing",
        "top_margin",
        "width",
    }
    _PREVIEW_JSON_PIXEL_KEYS = {"offset", "offsets"}

    def __init__(self):
        self.config = load_config()
        ensure_processors_registered()
        if not TemplateRenderService._logging_ready:
            init_from_config(self.config)
            TemplateRenderService._logging_ready = True

    def get_exif_data(self, input_path: str | Path) -> dict:
        resolved_path, modified_ns, file_size = get_file_signature(input_path)
        return deepcopy(get_cached_exif(resolved_path, modified_ns, file_size))

    def get_template(self, template_name: str):
        template_path = get_template_path(template_name)
        return get_cached_template(template_name, template_path.stat().st_mtime_ns)

    def build_context(
        self,
        input_path: str,
        exif_data: Optional[dict] = None,
        render_input_path: Optional[str | Path] = None,
    ) -> dict:
        path = Path(input_path).resolve()
        processing_path = Path(render_input_path).resolve() if render_input_path else path
        return {
            "exif": exif_data if exif_data is not None else self.get_exif_data(path),
            "filename": path.stem,
            "file_dir": str(path.parent).replace("\\", "/"),
            "file_path": str(processing_path).replace("\\", "/"),
            "files": [str(processing_path).replace("\\", "/")],
        }

    def render_pipeline(
        self,
        input_path: str,
        template_name: str,
        exif_data: Optional[dict] = None,
        render_input_path: Optional[str | Path] = None,
    ) -> list[dict]:
        ensure_processors_registered()
        template = self.get_template(template_name)
        rendered = template.render(
            self.build_context(input_path, exif_data=exif_data, render_input_path=render_input_path)
        )
        return json.loads(rendered)

    def _prepare_preview_image(
        self,
        input_path: str,
        exif_data: dict,
        max_dimension: Optional[int],
    ) -> tuple[Optional[Image.Image], dict, float]:
        if not max_dimension or max_dimension <= 0:
            return None, exif_data, 1.0

        with Image.open(input_path) as source:
            image = ImageOps.exif_transpose(source)
            if max(image.width, image.height) <= max_dimension:
                return None, exif_data, 1.0

            scale = max_dimension / max(image.width, image.height)
            target_size = (
                max(1, int(round(image.width * scale))),
                max(1, int(round(image.height * scale))),
            )
            preview = image.resize(target_size, Image.Resampling.LANCZOS)
            if preview.mode not in {"RGB", "RGBA"}:
                preview = preview.convert("RGBA" if "A" in preview.getbands() else "RGB")

        return preview, exif_data, scale

    def _write_preview_image(self, preview: Image.Image) -> str:
        fd, temp_path = tempfile.mkstemp(prefix="image_exif_styler_preview_", suffix=".png")
        os.close(fd)
        preview.save(temp_path)
        return temp_path

    def _pipeline_references_path(self, value, input_path: str) -> bool:
        source_path = str(Path(input_path).resolve()).replace("\\", "/")
        if isinstance(value, str):
            return source_path in value.replace("\\", "/")
        if isinstance(value, list):
            return any(self._pipeline_references_path(item, input_path) for item in value)
        if isinstance(value, dict):
            return any(self._pipeline_references_path(item, input_path) for item in value.values())
        return False

    @staticmethod
    def _scaled_number(value, scale: float):
        if isinstance(value, bool):
            return value
        if isinstance(value, int):
            scaled = int(round(value * scale))
            if value and scaled == 0:
                scaled = 1 if value > 0 else -1
            return scaled
        return value * scale

    @classmethod
    def _scale_preview_value(cls, value, scale: float):
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return cls._scaled_number(value, scale)
        if isinstance(value, str):
            stripped = value.strip()
            try:
                number = float(stripped) if any(char in stripped for char in ".eE") else int(stripped)
            except ValueError:
                return value
            scaled = cls._scaled_number(number, scale)
            return str(scaled)
        if isinstance(value, list):
            return [cls._scale_preview_value(item, scale) for item in value]
        return value

    @classmethod
    def _scale_json_preview_value(cls, value, scale: float):
        if not isinstance(value, str):
            return cls._scale_preview_value(value, scale)
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return value
        scaled = cls._scale_preview_value(parsed, scale)
        return json.dumps(scaled, ensure_ascii=False)

    @classmethod
    def _scale_preview_pipeline(cls, value, scale: float):
        if scale == 1.0:
            return value
        if isinstance(value, list):
            return [cls._scale_preview_pipeline(item, scale) for item in value]
        if not isinstance(value, dict):
            return value

        scaled = {}
        for key, item in value.items():
            if key in cls._PREVIEW_PIXEL_KEYS:
                scaled[key] = cls._scale_preview_value(item, scale)
            elif key in cls._PREVIEW_JSON_PIXEL_KEYS:
                scaled[key] = cls._scale_json_preview_value(item, scale)
            else:
                scaled[key] = cls._scale_preview_pipeline(item, scale)
        return scaled

    def render_preview(
        self,
        input_path: str,
        template_name: str,
        exif_data: Optional[dict] = None,
        max_dimension: Optional[int] = None,
    ) -> Image.Image:
        exif = exif_data if exif_data is not None else self.get_exif_data(input_path)
        preview_image, preview_exif, preview_scale = self._prepare_preview_image(
            input_path,
            exif,
            max_dimension,
        )
        render_input_path = input_path
        cleanup_path = None
        try:
            pipeline = self.render_pipeline(
                input_path,
                template_name,
                exif_data=preview_exif,
                render_input_path=render_input_path,
            )
            if preview_image is not None and self._pipeline_references_path(pipeline, input_path):
                cleanup_path = self._write_preview_image(preview_image)
                render_input_path = cleanup_path
                pipeline = self.render_pipeline(
                    input_path,
                    template_name,
                    exif_data=preview_exif,
                    render_input_path=render_input_path,
                )

            if preview_image is not None:
                pipeline = self._scale_preview_pipeline(pipeline, preview_scale)

            initial_buffer = [preview_image] if preview_image is not None else None
            image = start_process(
                pipeline,
                input_path=render_input_path,
                exif_data=preview_exif,
                initial_buffer=initial_buffer,
            )
            return image.copy()
        finally:
            if cleanup_path is not None:
                try:
                    Path(cleanup_path).unlink(missing_ok=True)
                except OSError:
                    pass

    def export_image(
        self,
        input_path: str,
        template_name: str,
        output_path: str,
        quality: Optional[int] = None,
        subsampling: Optional[int] = None,
    ) -> str:
        exif = self.get_exif_data(input_path)
        pipeline = self.render_pipeline(input_path, template_name, exif_data=exif)
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        save_options = {}
        if quality is not None:
            save_options["quality"] = quality
        if subsampling is not None:
            save_options["subsampling"] = subsampling
        start_process(
            pipeline,
            input_path=input_path,
            output_path=str(output),
            exif_data=exif,
            save_options=save_options or None,
        )
        return str(output)
