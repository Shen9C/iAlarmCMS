import os
from setuptools import setup, find_packages
from setuptools.extension import Extension
from Cython.Build import cythonize

# 需要递归编译的业务目录
CYTHON_MODULE_DIRS = [
    # 'app', 'scripts', 'config'
    'app', 'config' #暂时不编译scripts下的文件
]

# 需要排除的目录和文件
EXCLUDE_DIRS = [
    '.git', '__pycache__', 'venv', 'env', '.venv', 'build', 'scripts'
    'migrations', 'tests', 'docs', 'logs', 'backups', 'v0.9.0',
    'alarm_images', 'flask_alarm.egg-info'
]

EXCLUDE_FILES = [
    'run.py', 'setup.py', 'wsgi.py'
]

def get_py_files():
    """获取需要编译的Python文件列表"""
    py_files = []
    for base_dir in CYTHON_MODULE_DIRS:
        for root, dirs, files in os.walk(base_dir):
            # 排除不需要编译的目录
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
            for file in files:
                if file.endswith('.py') and file not in EXCLUDE_FILES:
                    path = os.path.join(root, file)
                    # 生成模块名（如 app.module.submodule）
                    module_path = path[:-3].replace(os.path.sep, '.')
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