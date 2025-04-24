#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import subprocess
import shutil

def main():
    """
    编译项目中除run.py外的所有Python文件为.so文件
    """
    print("开始编译Python文件为.so文件...")
    
    # 确保安装了Cython
    try:
        import Cython
        print(f"检测到Cython版本: {Cython.__version__}")
    except ImportError:
        print("正在安装Cython...")
        subprocess.call(["pip", "install", "Cython"])
    
    # 清理之前的编译文件
    build_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "build")
    if os.path.exists(build_dir):
        print("清理旧的build目录...")
        shutil.rmtree(build_dir)
    
    # 执行编译
    print("开始编译过程...")
    subprocess.call(["python", "setup.py", "build_ext", "--inplace"])
    
    # 清理过程中生成的.c文件
    print("清理生成的.c文件...")
    for root, dirs, files in os.walk('.'):
        # 排除一些目录
        dirs[:] = [d for d in dirs if d not in ['.git', '__pycache__', 'venv', 'env', '.venv', 'build']]
        for file in files:
            if file.endswith('.c') and file != 'run.py.c':  # 确保不会意外生成run.py.c
                os.remove(os.path.join(root, file))
    
    print("编译完成！项目中除run.py外的所有Python文件已被编译为.so文件")

if __name__ == "__main__":
    main() 