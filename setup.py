import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

VERSION = "0.0.10"


setuptools.setup(
    name="tonga-py",
    version=VERSION,
    author="Optibus",
    author_email="eitan@optibus.com",
    description="A python client for the Tonga flag management framework",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Optibus/tonga-py",
    packages=setuptools.find_packages(),
    install_requires=[
        "six>=1.15.0",
        'requests==2.24; python_version < "3.0"',
        'requests>=2.24; python_version > "3.0"',
    ],
    extras_require={
        "dev": [
            "mock==2.0.0",
            "requests-mock==1.9.3",
            "pytest==4.6.9",
            'pylint==2.6.0; python_version > "3.0"',
            'pylint-junit==0.3.2; python_version > "3.0"',
            'flake8==3.8.4; python_version > "3.0"',
            'flake8-formatter-junit-xml==0.0.6; python_version > "3.0"',
        ]
    },
    classifiers=[
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=2.7",
)
