#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
图片存储路径测试脚本
用于检查告警图片目录是否存在，并创建测试图片
"""

import os
import sys
import shutil
from datetime import datetime
from pathlib import Path

def create_test_image(path, filename="test_image_001.jpg"):
    """创建一个简单的测试图片
    
    如果没有现成的图片，生成一个空文件
    """
    image_path = os.path.join(path, filename)
    
    # 写入一个简单的文本内容作为测试
    with open(image_path, 'w') as f:
        f.write(f"This is a test image file created at {datetime.now()}")
    
    print(f"创建测试图片: {image_path}")
    return image_path

def check_directory(path):
    """检查目录是否存在，如果不存在则创建"""
    if os.path.exists(path):
        print(f"目录已存在: {path}")
        # 列出目录内容
        files = os.listdir(path)
        print(f"目录中的文件: {files}")
        return True
    else:
        print(f"目录不存在: {path}，尝试创建...")
        try:
            os.makedirs(path, exist_ok=True)
            print(f"成功创建目录: {path}")
            return True
        except Exception as e:
            print(f"创建目录失败: {e}")
            return False

def main():
    """主函数"""
    # 当前工作目录
    cwd = os.getcwd()
    print(f"当前工作目录: {cwd}")
    
    # 尝试多个可能的路径
    possible_paths = [
        os.path.join(cwd, 'static', 'alarm_images'),
        # os.path.join(cwd, 'app', 'static', 'alarm_images'),
        # os.path.join(cwd, '..', 'static', 'alarm_images'),
        # os.path.join(cwd, '..', '..', 'static', 'alarm_images')
    ]
    
    # 检查每个路径
    for i, path in enumerate(possible_paths):
        print(f"\n检查路径 {i+1}: {path}")
        if check_directory(path):
            # 创建测试图片
            for j in range(1, 4):  # 创建3个测试图片
                file_name = f"test_image_{j:03d}.jpg"
                create_test_image(path, file_name)
            print(f"已在 {path} 创建测试图片")
    
    # 检查相对路径的静态目录
    for rel_path in ['static/alarm_images', 'app/static/alarm_images']:
        path = os.path.normpath(os.path.join(cwd, rel_path))
        print(f"\n检查相对路径: {rel_path} -> {path}")
        if os.path.exists(path):
            print(f"相对路径存在: {rel_path}")
            files = os.listdir(path)
            print(f"目录中的文件: {files}")
        else:
            print(f"相对路径不存在: {rel_path}")
    
    print("\n图片目录检查完成。")
    
if __name__ == "__main__":
    main() 