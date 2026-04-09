#!/usr/bin/env python
"""
测试模板样式
输入: ./input 文件夹
输出: ./output_test/样式名/ 子文件夹
质量: 100
覆盖: 启用

用法:
  python test_all_templates.py              # 运行所有模板
  python test_all_templates.py 标准水印      # 运行指定模板
  python test_all_templates.py 标准水印 背景模糊  # 运行多个指定模板
"""
import os
import sys
import argparse
from pathlib import Path

from core.configs import load_config, templates_dir
from core.logger import logger, init_from_config
from cli import process_single_file, get_all_image_files
from core.util import get_template


def test_templates(specific_templates=None):
    """测试模板
    
    Args:
        specific_templates: 指定要测试的模板列表，None表示测试所有模板
    """
    # 加载配置
    config = load_config()
    init_from_config(config)
    
    # 设置参数
    input_folder = './input'
    output_base = './output_test'
    quality = 100
    override = True
    
    # 获取所有可用模板
    available_templates = []
    for template_file in sorted(templates_dir.glob('*.json')):
        available_templates.append(template_file.stem)
    
    # 确定要测试的模板
    if specific_templates:
        # 过滤只保留存在的模板
        templates_to_test = []
        for t in specific_templates:
            if t in available_templates:
                templates_to_test.append(t)
            else:
                print(f"警告: 模板 '{t}' 不存在，已跳过")
        
        if not templates_to_test:
            print(f"错误: 没有有效的模板可测试")
            print(f"可用模板: {', '.join(available_templates)}")
            sys.exit(1)
        
        print(f"指定测试 {len(templates_to_test)} 个模板:")
        for t in templates_to_test:
            print(f"  - {t}")
    else:
        templates_to_test = available_templates
        print(f"找到 {len(templates_to_test)} 个模板:")
        for t in templates_to_test:
            print(f"  - {t}")
    print()
    
    # 检查输入文件夹
    if not os.path.exists(input_folder):
        logger.error(f"输入文件夹不存在: {input_folder}")
        sys.exit(1)
    
    # 获取所有图片文件
    suffixes = set(['.jpeg', '.jpg', '.png', '.heic'])
    input_files = get_all_image_files(input_folder, suffixes)
    total_files = len(input_files)
    
    if total_files == 0:
        logger.warning(f"输入文件夹中没有找到支持的图片文件: {input_folder}")
        sys.exit(0)
    
    print(f"找到 {total_files} 个待处理文件\n")
    
    # 更新配置
    config.set('DEFAULT', 'quality', str(quality))
    config.set('DEFAULT', 'subsampling', '2')
    
    # 遍历模板
    for template_name in templates_to_test:
        print(f"\n{'='*60}")
        print(f"测试模板: {template_name}")
        print('='*60)
        
        # 设置输出文件夹
        output_folder = os.path.join(output_base, template_name)
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)
            print(f"创建输出文件夹: {output_folder}")
        
        # 获取模板
        try:
            template = get_template(template_name)
        except Exception as e:
            logger.error(f"加载模板失败 {template_name}: {e}")
            continue
        
        # 处理文件
        success_count = 0
        failure_count = 0
        
        for i, input_path in enumerate(input_files, 1):
            file_name = os.path.basename(input_path)
            print(f"\n[{i}/{total_files}] 处理: {file_name}")
            
            success, skipped, error = process_single_file(
                input_path, input_folder, output_folder, template_name, template, config, override
            )
            
            if success:
                print(f"  ✓ 完成")
                success_count += 1
            elif skipped:
                print(f"  → 跳过")
            else:
                print(f"  ✗ 失败: {error}")
                failure_count += 1
        
        print(f"\n模板 '{template_name}' 处理完成: 成功 {success_count}, 失败 {failure_count}")
    
    print(f"\n{'='*60}")
    print("测试完成!")
    print(f"输出位置: {os.path.abspath(output_base)}")
    print('='*60)


if __name__ == '__main__':
    # 解析命令行参数
    parser = argparse.ArgumentParser(
        description='测试水印模板',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  python test_all_templates.py              # 运行所有模板
  python test_all_templates.py 标准水印      # 运行指定模板
  python test_all_templates.py 标准水印 背景模糊  # 运行多个模板
        '''
    )
    parser.add_argument(
        'templates',
        nargs='*',
        help='要测试的模板名称（可选，不指定则测试所有模板）'
    )
    
    args = parser.parse_args()
    
    # 运行测试
    test_templates(args.templates if args.templates else None)
