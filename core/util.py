from __future__ import annotations

import io
import json
import os
import platform
import re
import shutil
import subprocess
import time
from functools import wraps
from pathlib import Path

from PIL import Image, ExifTags
from PIL.TiffImagePlugin import IFDRational
from jinja2 import Template

from core.configs import templates_dir
from core.jinja2renders import vh, vw, auto_logo
from core.logger import logger


# EXIF 标签映射表
EXIF_TAG_MAP = {
    # 相机信息
    'Make': 'Make',
    'Model': 'Model',
    'LensModel': 'LensModel',
    'LensMake': 'LensMake',
    # 拍摄参数
    'FNumber': 'FNumber',
    'ExposureTime': 'ExposureTime',
    'ISOSpeedRatings': 'ISO',
    'FocalLength': 'FocalLength',
    'FocalLengthIn35mmFilm': 'FocalLengthIn35mmFormat',
    # 日期
    'DateTimeOriginal': 'DateTimeOriginal',
    'DateTime': 'DateTime',
    'DateTimeDigitized': 'DateTimeDigitized',
    # 其他
    'ExposureBiasValue': 'ExposureCompensation',
    'MeteringMode': 'MeteringMode',
    'Flash': 'Flash',
    'WhiteBalance': 'WhiteBalance',
}


def _convert_exif_value(value):
    """转换 EXIF 值为可序列化的格式"""
    if isinstance(value, bytes):
        try:
            return value.decode('utf-8', errors='ignore').strip('\x00')
        except:
            return str(value)
    elif isinstance(value, IFDRational):
        return float(value)
    elif isinstance(value, tuple):
        return tuple(_convert_exif_value(v) for v in value)
    return value


def _format_exposure_time(value):
    """格式化曝光时间为分数形式，如 1/125"""
    if isinstance(value, (int, float)):
        if value < 1:
            denominator = round(1 / value)
            return f"1/{denominator}"
        else:
            return str(int(value))
    return str(value)


def _format_f_number(value):
    """格式化光圈值，如 F2.8"""
    if isinstance(value, (int, float)):
        return f"F{value:.1f}".replace('.0', '')
    return str(value)


def _format_focal_length(value):
    """格式化焦距，如 50mm"""
    if isinstance(value, (int, float)):
        return f"{int(value)}mm"
    return str(value)


def get_exif(path) -> dict:
    """
    使用 PIL 从图片中直接读取 EXIF 信息
    :param path: 照片路径
    :return: exif信息字典
    """
    exif_dict = {}
    try:
        with Image.open(path) as img:
            # 获取 EXIF 数据
            exif_data = img._getexif()
            
            if exif_data is not None:
                # 遍历所有 EXIF 标签
                for tag_id, value in exif_data.items():
                    tag_name = ExifTags.TAGS.get(tag_id, str(tag_id))
                    exif_dict[tag_name] = _convert_exif_value(value)
                
                # 获取 GPS 信息
                try:
                    gps_info = {}
                    for key in exif_data.keys():
                        if ExifTags.TAGS.get(key) == 'GPSInfo':
                            gps_data = exif_data[key]
                            for gps_key in gps_data.keys():
                                gps_tag = ExifTags.GPSTAGS.get(gps_key, str(gps_key))
                                gps_info[gps_tag] = _convert_exif_value(gps_data[gps_key])
                            break
                    if gps_info:
                        exif_dict['GPSInfo'] = gps_info
                except Exception:
                    pass
            
            # 添加图片基本信息
            exif_dict['ImageWidth'] = img.width
            exif_dict['ImageHeight'] = img.height
            exif_dict['ImageSize'] = f"{img.width} x {img.height}"
            
            # 格式化常用字段（与 exiftool 输出格式保持一致）
            if 'Make' in exif_dict:
                exif_dict['Make'] = exif_dict['Make'].strip()
            if 'Model' in exif_dict:
                exif_dict['Model'] = exif_dict['Model'].strip()
            if 'LensModel' in exif_dict:
                exif_dict['LensModel'] = exif_dict['LensModel'].strip()
            if 'FNumber' in exif_dict:
                exif_dict['FNumber'] = _format_f_number(exif_dict['FNumber'])
            if 'ExposureTime' in exif_dict:
                # 同时设置 ExposureTime 和 ShutterSpeed（模板兼容）
                formatted_time = _format_exposure_time(exif_dict['ExposureTime'])
                exif_dict['ExposureTime'] = formatted_time
                exif_dict['ShutterSpeed'] = formatted_time
                exif_dict['ShutterSpeedValue'] = formatted_time
            if 'FocalLength' in exif_dict:
                exif_dict['FocalLength'] = _format_focal_length(exif_dict['FocalLength'])
            if 'FocalLengthIn35mmFilm' in exif_dict:
                exif_dict['FocalLengthIn35mmFormat'] = _format_focal_length(exif_dict['FocalLengthIn35mmFilm'])
            if 'ISOSpeedRatings' in exif_dict:
                exif_dict['ISO'] = str(exif_dict['ISOSpeedRatings'])
                exif_dict['ISOSpeedRatings'] = str(exif_dict['ISOSpeedRatings'])
            
            # 品牌名映射表：将完整的厂商名称映射为简化版本
            BRAND_MAP = {
                'nikon corporation': 'NIKON',
                'canon': 'Canon',
                'canon inc.': 'Canon',
                'sony': 'SONY',
                'sony corporation': 'SONY',
                'fujifilm': 'FUJIFILM',
                'fuji photo film co., ltd.': 'FUJIFILM',
                'olympus': 'OLYMPUS',
                'olympus corporation': 'OLYMPUS',
                'panasonic': 'Panasonic',
                'panasonic corporation': 'Panasonic',
                'leica': 'Leica',
                'leica camera': 'Leica',
                'hasselblad': 'Hasselblad',
                'pentax': 'PENTAX',
                'ricoh': 'RICOH',
                'dji': 'DJI',
                'apple': 'Apple',
                'apple inc.': 'Apple',
            }
            
            # 简化品牌名
            if 'Make' in exif_dict:
                make_original = exif_dict['Make'].strip()
                make_lower = make_original.lower()
                # 查找映射表
                for key, value in BRAND_MAP.items():
                    if key in make_lower or make_lower.startswith(key):
                        exif_dict['Make'] = value
                        break
                else:
                    # 如果没有匹配，使用原始值（首字母大写）
                    exif_dict['Make'] = make_original
            
            # 处理相机型号：有些相机会在 Model 中包含品牌名，需要清理
            if 'Make' in exif_dict and 'Model' in exif_dict:
                make = exif_dict['Make'].lower()
                model = exif_dict['Model']
                # 如果 Model 以品牌名开头，移除它
                if model.lower().startswith(make):
                    model = model[len(make):].strip()
                # 清理常见的品牌前缀
                for prefix in ['canon', 'nikon', 'sony', 'fujifilm', 'olympus', 'panasonic', 'leica', 'hasselblad', 'pentax', 'ricoh', 'dji']:
                    if model.lower().startswith(prefix):
                        model = model[len(prefix):].strip()
                exif_dict['Model'] = model
            
            # 创建兼容 exiftool 格式的键名（移除空格和斜杠）
            formatted_dict = {}
            for key, value in exif_dict.items():
                # 过滤非 ASCII 字符
                if isinstance(value, str):
                    value = ''.join(c for c in value if ord(c) < 128)
                formatted_key = re.sub(r'\s+', '', key)
                formatted_key = re.sub(r'/', '', formatted_key)
                formatted_dict[formatted_key] = value
                # 同时保留原始键名
                formatted_dict[key] = value
            
            exif_dict.update(formatted_dict)
            
    except Exception as e:
        logger.error(f'get_exif error: {path} : {e}')
    
    return exif_dict


def list_files(path: str, suffixes: set[str], depth: int = 0, max_depth: int = 20):
    """
    使用 pathlib 实现的版本

    Args:
        path: 要扫描的路径
        suffixes: 支持的文件后缀
        depth: 当前递归深度（内部使用）
        max_depth: 最大递归深度，防止无限递归
    """
    result = []
    root = Path(path).resolve()

    if not root.exists():
        return result

    # 防止递归过深
    if depth > max_depth:
        logger.warning(f"list_files: 达到最大递归深度 {max_depth}，跳过 {path}")
        return result

    try:
        # 分离文件夹和文件，分别排序
        items = list(root.iterdir())
        dirs = sorted([i for i in items if i.is_dir()], key=lambda x: x.name.lower(), reverse=True)
        files = sorted([i for i in items if i.is_file()], key=lambda x: (x.stat().st_mtime, x.name.lower()),
                       reverse=True)

        # 先处理文件夹
        for item in dirs:
            if item.name.startswith('.'):
                continue
            # 跳过符号链接，避免无限递归
            if item.is_symlink():
                continue
            children = list_files(str(item), suffixes, depth + 1, max_depth)
            if children:
                result.append({
                    'label': item.name,
                    'value': str(item),
                    'children': children,
                })

        # 再处理文件
        for item in files:
            if item.name.startswith('.'):
                continue
            if item.suffix.lower() in suffixes:
                result.append({
                    'label': item.name,
                    'value': str(item),
                    'is_file': True
                })

    except PermissionError:
        logger.debug(f"list_files: 权限不足，跳过 {path}")
    except Exception as e:
        logger.error(f"list_files: 扫描失败 {path}: {e}")

    return result


def build_export_filename(
    source: str | Path,
    template_name: str,
    quality: int | None = None,
    extension: str | None = None,
) -> str:
    source_path = Path(source)
    resolved_extension = extension or source_path.suffix or ".jpg"
    if not resolved_extension.startswith("."):
        resolved_extension = f".{resolved_extension}"

    parts = [source_path.stem]
    if template_name:
        parts.append(template_name)
    if quality is not None:
        parts.append(f"Q{int(quality)}")
    return f"{'_'.join(parts)}{resolved_extension.lower()}"


def ensure_export_suffixes(path: str | Path, template_name: str, quality: int | None = None) -> Path:
    output_path = Path(path)
    extension = output_path.suffix or ".jpg"
    tokens = [token for token in output_path.stem.split("_") if token]

    if template_name and template_name not in tokens:
        tokens.append(template_name)

    quality_token = f"Q{int(quality)}" if quality is not None else None
    if quality_token and quality_token not in tokens:
        tokens.append(quality_token)

    return output_path.with_name(f"{'_'.join(tokens)}{extension.lower()}")


def log_rt(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()  # 记录开始时间
        result = func(*args, **kwargs)  # 调用被装饰的函数
        end_time = time.time()  # 记录结束时间
        elapsed_time = (end_time - start_time) * 1000  # 计算运行时间

        logger.debug(f"[monitor]api#{func.__name__} cost {elapsed_time:.2f}ms")
        return result

    return wrapper


def convert_heic_to_jpeg(path: str, quality: int = 90) -> io.BytesIO:
    """转换 HEIC 为 JPEG 字节流"""
    with Image.open(path) as img:
        if img.mode in ('RGBA', 'P', 'LA'):
            img = img.convert('RGB')

        buffer = io.BytesIO()
        img.save(buffer, format='JPEG', quality=quality)
        buffer.seek(0)
        return buffer


# ==================== 模板管理相关方法 ====================

def get_template_path(template_name: str) -> Path:
    """
    获取模板文件的完整路径

    Args:
        template_name: 模板名称（不含扩展名），如 "standard1"

    Returns:
        模板文件的完整 Path 对象
    """
    return templates_dir / f"{template_name}.json"


def get_template(template_name: str) -> Template:
    """
    读取并解析模板文件为 Jinja2 Template 对象

    Args:
        template_name: 模板名称（不含扩展名），如 "standard1"

    Returns:
        Jinja2 Template 对象，已注册 vh, vw, auto_logo 全局函数
    """
    template_path = get_template_path(template_name)
    with open(template_path, encoding='utf-8') as f:
        template_str = f.read()
    template = Template(template_str)
    template.globals['vh'] = vh
    template.globals['vw'] = vw
    template.globals['auto_logo'] = auto_logo
    return template


def get_template_content(template_name: str) -> str:
    """
    获取模板文件的内容（原始字符串）

    Args:
        template_name: 模板名称（不含扩展名），如 "standard1"

    Returns:
        模板文件的原始内容字符串
    """
    template_path = get_template_path(template_name)
    with open(template_path, encoding='utf-8') as f:
        return f.read()


def save_template(template_name: str, content: str) -> None:
    """
    保存模板文件

    Args:
        template_name: 模板名称（不含扩展名），如 "standard1"
        content: 模板内容（JSON 字符串）
    """
    template_path = get_template_path(template_name)
    # 确保目录存在
    template_path.parent.mkdir(parents=True, exist_ok=True)
    with open(template_path, 'w', encoding='utf-8') as f:
        f.write(content)


def create_template(template_name: str, content: str = '[]') -> None:
    """
    创建新的模板文件

    Args:
        template_name: 模板名称（不含扩展名），如 "my_template"
        content: 模板内容（JSON 字符串），默认为空数组 '[]'

    Raises:
        FileExistsError: 如果模板文件已存在
    """
    template_path = get_template_path(template_name)
    if template_path.exists():
        raise FileExistsError(f"模板 '{template_name}' 已存在")
    save_template(template_name, content)


def list_templates() -> list[str]:
    """
    列出所有可用的模板名称

    Returns:
        模板名称列表（不含扩展名）
    """
    if not templates_dir.exists():
        return []
    return [f.stem for f in templates_dir.glob('*.json')]
