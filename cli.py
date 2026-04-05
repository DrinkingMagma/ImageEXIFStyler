import argparse
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from core.configs import load_config, templates_dir, CONFIG_PATH
from core.logger import logger, init_from_config
from core.util import list_files, get_exif, get_template
from processor.core import start_process


def process_single_file(input_path, input_folder, output_folder, template, config, override_existed=False):
    """处理单个文件，返回 (success, skipped, error_message)"""
    if not os.path.exists(input_path):
        return False, False, f"文件不存在: {input_path}"

    try:
        # 获取 input_path 相对 input_folder 的位置
        relative_path = os.path.relpath(input_path, input_folder)
        # 基于 output_folder 组装出输出路径 output_path
        output_path = os.path.join(output_folder, relative_path)

        # 如果路径不存在, 那么递归创建文件夹
        output_dir = os.path.dirname(output_path)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # 如果 output_path 对应的文件存在, 直接跳过
        if os.path.exists(output_path) and not override_existed:
            return False, True, None

        _input_path = Path(input_path)
        # 开始处理
        context = {
            'exif': get_exif(input_path),
            'filename': _input_path.stem,
            'file_dir': str(_input_path.parent.absolute()).replace('\\', '/'),
            'file_path': str(_input_path).replace('\\', '/'),
            'files': [input_path]
        }
        final_template = template.render(context)
        start_process(json.loads(final_template), input_path, output_path=output_path)
        return True, False, None

    except Exception as e:
        logger.error(f"处理文件失败 {input_path}: {e}")
        return False, False, str(e)


def get_all_image_files(input_folder, suffixes):
    """获取输入文件夹中所有支持的图片文件"""
    all_files = []
    root = Path(input_folder).resolve()

    if not root.exists():
        return all_files

    for item in root.rglob('*'):
        if item.is_file() and item.suffix.lower() in suffixes:
            all_files.append(str(item))

    return all_files


def main():
    parser = argparse.ArgumentParser(
        description='Semi-Utils 命令行工具 - 图片水印处理',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  python cli.py -i ./input -o ./output
  python cli.py -i ./input -o ./output -t 标准水印 -q 80
  python cli.py -i ./input -o ./output --override
        '''
    )

    parser.add_argument('-i', '--input', type=str, default=None,
                        help='输入文件夹路径 (默认: 使用 config.ini 中的 input_folder)')
    parser.add_argument('-o', '--output', type=str, default=None,
                        help='输出文件夹路径 (默认: 使用 config.ini 中的 output_folder)')
    parser.add_argument('-t', '--template', type=str, default=None,
                        help='模板名称 (默认: 使用 config.ini 中的 template_name)')
    parser.add_argument('-q', '--quality', type=int, default=None,
                        help='输出图片质量 1-100 (默认: 使用 config.ini 中的 quality)')
    parser.add_argument('--subsampling', type=int, default=None,
                        help='JPEG 子采样 0-2 (默认: 使用 config.ini 中的 subsampling)')
    parser.add_argument('--override', action='store_true',
                        help='覆盖已存在的输出文件')
    parser.add_argument('--workers', type=int, default=4,
                        help='并发处理线程数 (默认: 4)')
    parser.add_argument('--list-templates', action='store_true',
                        help='列出所有可用模板')

    args = parser.parse_args()

    # 加载配置
    config = load_config()
    init_from_config(config)

    # 列出模板
    if args.list_templates:
        print("可用模板:")
        for template_file in sorted(templates_dir.glob('*.json')):
            template_name = template_file.stem
            print(f"  - {template_name}")
        return

    # 获取参数（命令行优先，其次配置文件）
    input_folder = args.input or config.get('DEFAULT', 'input_folder')
    output_folder = args.output or config.get('DEFAULT', 'output_folder')
    template_name = args.template or config.get('render', 'template_name')
    quality = args.quality if args.quality is not None else config.getint('DEFAULT', 'quality')
    subsampling = args.subsampling if args.subsampling is not None else config.getint('DEFAULT', 'subsampling')
    override_existed = args.override or config.getboolean('DEFAULT', 'override_existed')

    # 验证输入文件夹
    if not os.path.exists(input_folder):
        logger.error(f"输入文件夹不存在: {input_folder}")
        sys.exit(1)

    # 获取模板
    try:
        template = get_template(template_name)
    except FileNotFoundError:
        logger.error(f"模板不存在: {template_name}")
        logger.info("使用 --list-templates 查看所有可用模板")
        sys.exit(1)

    # 确保输出文件夹存在
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
        logger.info(f"创建输出文件夹: {output_folder}")

    # 获取支持的文件后缀
    suffixes = set([ft for ft in config.get('DEFAULT', 'supported_file_suffixes').split(',')])

    # 获取所有待处理文件
    input_files = get_all_image_files(input_folder, suffixes)
    total_count = len(input_files)

    if total_count == 0:
        logger.warning(f"输入文件夹中没有找到支持的图片文件: {input_folder}")
        sys.exit(0)

    logger.info(f"找到 {total_count} 个待处理文件")
    logger.info(f"输入文件夹: {input_folder}")
    logger.info(f"输出文件夹: {output_folder}")
    logger.info(f"使用模板: {template_name}")
    logger.info(f"图片质量: {quality}")
    logger.info(f"并发线程: {args.workers}")

    # 更新配置（用于 start_process 中的质量设置）
    config.set('DEFAULT', 'quality', str(quality))
    config.set('DEFAULT', 'subsampling', str(subsampling))

    # 处理文件
    processed = 0
    success_count = 0
    failure_count = 0
    skipped_count = 0

    def worker(file_path):
        """工作线程函数"""
        file_name = os.path.basename(file_path)
        logger.info(f"正在处理: {file_name}")

        success, skipped, error = process_single_file(
            file_path, input_folder, output_folder, template, config, override_existed
        )

        if skipped:
            logger.info(f"跳过: {file_name}")
            return 'skipped', error
        elif success:
            logger.success(f"完成: {file_name}")
            return 'success', error
        else:
            logger.error(f"失败: {file_name} - {error}")
            return 'failure', error

    # 使用线程池并发处理
    max_workers = min(args.workers, total_count)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(worker, f): f for f in input_files}

        for future in as_completed(futures):
            status, error = future.result()
            processed += 1

            if status == 'success':
                success_count += 1
            elif status == 'skipped':
                skipped_count += 1
            else:
                failure_count += 1

            # 显示进度
            percent = round((processed / total_count) * 100) if total_count > 0 else 0
            print(f"\r进度: {processed}/{total_count} ({percent}%) | 成功: {success_count} | 跳过: {skipped_count} | 失败: {failure_count}", end='', flush=True)

    print()  # 换行
    logger.info(f"处理完成! 成功: {success_count}, 跳过: {skipped_count}, 失败: {failure_count}")


if __name__ == '__main__':
    main()
