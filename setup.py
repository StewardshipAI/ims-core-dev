"""
IMS Core - Intelligent Model Switching
Enterprise AI orchestration platform
"""

from setuptools import setup, find_packages
import os

# Read long description from README
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

# Read requirements
with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="ims-core",
    version="0.1.0",
    author="Stewardship Solutions",
    author_email="contact@stewardshipsolutions.com",
    description="Enterprise AI orchestration platform for intelligent model switching",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/StewardshipSolutions/ims-core",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.11",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.4.3",
            "pytest-cov>=4.1.0",
            "black>=23.12.1",
            "flake8>=7.0.0",
            "mypy>=1.8.0",
        ],
        "docs": [
            "mkdocs>=1.5.3",
            "mkdocs-material>=9.5.3",
        ],
    },
    entry_points={
        "console_scripts": [
            "ims=src.cli:main",  # Future CLI tool
        ],
    },
)
