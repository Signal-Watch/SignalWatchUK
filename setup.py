#!/usr/bin/env python
"""
Setup script for installing SignalWatch
"""
from setuptools import setup, find_packages
from pathlib import Path

# Read README
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

setup(
    name="signalwatch",
    version="1.0.0",
    description="Companies House data analysis tool for detecting mismatches and mapping director networks",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Your Name",
    author_email="your.email@example.com",
    url="https://github.com/yourusername/signalwatch",
    license="MIT",
    packages=find_packages(exclude=["tests", "tests.*"]),
    include_package_data=True,
    python_requires=">=3.9",
    install_requires=[
        "flask>=3.0.0",
        "requests>=2.31.0",
        "python-dotenv>=1.0.0",
        "PyPDF2>=3.0.1",
        "pdf2image>=1.17.0",
        "pytesseract>=0.3.10",
        "Pillow>=11.0.0",
        "pandas>=2.1.4",
        "numpy>=1.26.2",
        "dateparser>=1.2.0",
        "ratelimit>=2.2.1",
        "cachetools>=5.3.2",
        "openpyxl>=3.1.2",
        "jinja2>=3.1.3",
    ],
    extras_require={
        "ai": ["openai>=1.6.1"],
        "dev": [
            "pytest>=7.4.3",
            "pytest-cov>=4.1.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "signalwatch=cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Financial and Insurance Industry",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Office/Business :: Financial",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    keywords="companies-house, corporate-data, due-diligence, network-analysis, compliance",
)
