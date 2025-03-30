from setuptools import setup

with open('requirements.txt') as f:
    required = f.read().splitlines()

# read the contents of your README file
from pathlib import Path
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

setup(
    name='biot_python_sdk',
    version='1.0.20',
    description='A python SDK that wraps Bio-T Open API',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='Stanislav Steinberg',
    author_email='sstbrg@gmail.com',
    url='https://github.com/sstbrg/biot_python_sdk',
    packages=['biot_python_sdk'],
    install_requires=required,
)
