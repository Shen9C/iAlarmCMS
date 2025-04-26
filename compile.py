#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import subprocess
import shutil

CYTHON_MODULE_DIRS = ['app', 'scripts', 'config']
EXCLUDE_DIRS = ['.git', '__pycache__', 'venv', 'env', '.venv', 'build', 'migrations', 'tests', 'docs', 'logs', 'backups', 'alarm_images', 'flask_alarm.egg-info']
EXCLUDE_FILES = ['run.py', 'setup.py', 'compile.py', 'wsgi.py']

def main():
    """
    编译项目中业务目录下的Python文件为.so文件，并清理源码
    """
    print("开始编译Python文件为.so文件...")
    
    # 确保安装了Cython
    try:
        import Cython
        print(f"检测到Cython版本: {Cython.__version__}")
    except ImportError:
        print("正在安装Cython...")
        subprocess.call(["pip", "install", "Cython"])
    
    # 清理旧的build目录
    build_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "build")
    if os.path.exists(build_dir):
        print("清理旧的build目录...")
        shutil.rmtree(build_dir)
    
    # 执行编译
    print("开始编译过程...")
    subprocess.call(["python", "setup.py", "build_ext", "--inplace"])
    
    # 清理过程中生成的.c文件
    print("清理生成的.c文件...")
    for base_dir in CYTHON_MODULE_DIRS:
        for root, dirs, files in os.walk(base_dir):
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
            for file in files:
                if file.endswith('.c'):
                    os.remove(os.path.join(root, file))
    
    # 删除源码，仅保留so文件和__init__.py、入口文件
    print("删除源码，仅保留so文件和__init__.py、入口文件...")
    for base_dir in CYTHON_MODULE_DIRS:
        for root, dirs, files in os.walk(base_dir):
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
            for file in files:
                if file.endswith('.py') and file not in EXCLUDE_FILES and file != '__init__.py':
                    os.remove(os.path.join(root, file))
    
    print("编译完成！项目中业务目录下的Python文件已被编译为.so文件，并清理源码。")

if __name__ == "__main__":
    main() 