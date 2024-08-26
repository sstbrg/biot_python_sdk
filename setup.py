from setuptools import setup

with open('requirements.txt') as f:
    required = f.read().splitlines()

setup(
    name='biot_python_sdk',
    version='1.0.3',
    description='A python SDK that wraps Bio-T Open API',
    author='Stanislav Steinberg',
    author_email='sstbrg@gmail.com',
    url='https://github.com/sstbrg/biot_python_sdk',
    packages=['biot_python_sdk'],
    install_requires=required,
)