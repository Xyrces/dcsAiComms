"""Setup configuration for DCS Natural Language ATC"""

from setuptools import setup, find_packages
from pathlib import Path

# Read the contents of README file
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding='utf-8')

setup(
    name="dcs-nl-atc",
    version="0.1.0",
    author="DCS-NL-ATC Project",
    description="Natural Language ATC system for DCS World with Ollama integration",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Xyrces/dcsAiComms",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Games/Entertainment :: Simulation",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.11",
    install_requires=[
        "ollama>=0.1.0",
        "numpy>=1.24.0",
        "sounddevice>=0.4.6",
        "pydub>=0.25.1",
        "pyaudio>=0.2.13",
        "scipy>=1.10.0",
        "faster-whisper>=0.10.0",
        "spacy>=3.7.0",
        "requests>=2.31.0",
        "websockets>=12.0",
        "pyyaml>=6.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
            "pytest-asyncio>=0.21.0",
            "pytest-mock>=3.11.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.5.0",
            "pre-commit>=3.5.0",
            "build>=1.0.0",
            "wheel>=0.42.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "dcs-nl-atc=atc_main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.yaml", "*.yml", "*.lua"],
    },
)
