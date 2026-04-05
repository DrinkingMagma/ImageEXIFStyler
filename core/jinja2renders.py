from jinja2 import pass_context

from core.configs import logos_dir

# 品牌名到 logo 文件名的映射表
# 支持多个关键词映射到同一个 logo
BRAND_LOGO_MAP = {
    'canon': 'canon',
    'nikon': 'nikon',
    'nikon corporation': 'nikon',
    'sony': 'sony',
    'sony corporation': 'sony',
    'fujifilm': 'fujifilm',
    'fuji': 'fujifilm',
    'olympus': 'olympus',
    'olympus corporation': 'olympus',
    'panasonic': 'panasonic',
    'leica': 'leica',
    'leica camera': 'leica',
    'hasselblad': 'hasselblad',
    'pentax': 'pentax',
    'ricoh': 'ricoh',
    'dji': 'dji',
    'apple': 'apple',
    'xmage': 'xmage',
}


def _find_logo_for_brand(brand: str) -> str:
    """根据品牌名查找对应的 logo 文件名"""
    brand = brand.lower().strip()
    
    # 1. 直接匹配
    if brand in BRAND_LOGO_MAP:
        return BRAND_LOGO_MAP[brand]
    
    # 2. 遍历映射表，检查品牌名是否包含映射键
    for key, logo_name in BRAND_LOGO_MAP.items():
        if key in brand:
            return logo_name
    
    # 3. 遍历 logo 文件，检查文件名是否包含在品牌中
    for f in logos_dir.iterdir():
        if f.suffix.lower() in {'.png', '.jpg', '.jpeg'}:
            if f.stem.lower() in brand:
                return f.stem.lower()
    
    return 'default'


@pass_context
def vw(context, percent):
    exif = context.get('exif', {})
    return int(int(exif.get('ImageWidth', 0)) * percent / 100)


@pass_context
def vh(context, percent):
    exif = context.get('exif', {})
    return int(int(exif.get('ImageHeight', 0)) * percent / 100)


@pass_context
def auto_logo(context, brand: str = None):
    exif = context.get('exif', {})
    brand = (brand or exif.get('Make', 'default')).strip()

    # 查找对应的 logo 文件名
    logo_name = _find_logo_for_brand(brand)

    # 查找对应的 logo 文件
    for f in logos_dir.iterdir():
        if f.suffix.lower() in {'.png', '.jpg', '.jpeg'}:
            # 精确匹配 logo 文件名
            if f.stem.lower() == logo_name:
                return str(f.absolute()).replace('\\', '/')

    # 返回默认 logo
    default_logo = logos_dir / 'default.png'
    if default_logo.exists():
        return str(default_logo.absolute()).replace('\\', '/')
    return None
