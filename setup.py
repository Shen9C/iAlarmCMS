from setuptools import setup, find_packages
from setuptools.extension import Extension
from Cython.Build import cythonize
import os

# 获取所有需要编译的Python文件
def get_py_files():
    py_files = []
    exclude_files = ['run.py']  # 排除run.py
    
    for root, dirs, files in os.walk('.'):
        # 排除.git, __pycache__, venv等目录
        dirs[:] = [d for d in dirs if d not in ['.git', '__pycache__', 'venv', 'env', '.venv']]
        
        for file in files:
            if file.endswith('.py') and file not in exclude_files:
                path = os.path.join(root, file)
                # 转换路径格式以适应Extension
                module_path = path[2:-3].replace(os.path.sep, '.')
                py_files.append(Extension(module_path, [path]))
    
    return py_files

extensions = get_py_files()

setup(
    name='flask-alarm',
    version='1.0',
    packages=find_packages(),
    install_requires=[
        'Flask',
        'Flask-SQLAlchemy',
        'Flask-Login',
        'Cython',
    ],
    ext_modules=cythonize(
        extensions,
        compiler_directives={
            'language_level': 3,
            'always_allow_keywords': True,
        }
    ),
)