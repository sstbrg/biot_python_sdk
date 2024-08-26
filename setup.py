from setuptools import setup

setup(
    name='biot_python_sdk',
    version='1.0.2',
    description='A python SDK that wraps Bio-T Open API',
    author='Stanislav Steinberg',
    author_email='sstbrg@gmail.com',
    url='https://github.com/sstbrg/biot_python_sdk',
    py_modules=['biot_python_sdk'],
    install_requires=[
        'requests',
    ],
)