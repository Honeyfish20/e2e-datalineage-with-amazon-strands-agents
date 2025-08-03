"""
Enhanced Lineage Agent Setup
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="enhanced-lineage-agent",
    version="0.1.0",
    author="Enhanced Lineage Team",
    author_email="team@example.com",
    description="基于Amazon Strands Agents的智能血缘提取系统",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/example/enhanced-lineage-agent",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.9",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "pytest-mock>=3.10.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
        ],
        "jupyter": [
            "jupyter>=1.0.0",
            "ipython>=8.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "enhanced-lineage-agent=enhanced_lineage_agent.cli:main",
        ],
    },
)