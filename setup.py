from setuptools import setup, find_packages

setup(
    name='flask-alarm',
    version='1.0',
    packages=find_packages(),
    install_requires=[
        'Flask',
        'Flask-SQLAlchemy',
        'Flask-Login',
    ]
)