from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="futures-backtesting",
    version="0.1.0",
    author="Tarric Sookdeo",
    description="Futures backtesting framework for prop firm trading strategies",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/tarricsookdeo/futures-backtesting",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Financial and Insurance Industry",
        "Topic :: Office/Business :: Financial :: Investment",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.13",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.13",
    install_requires=requirements,
    keywords="backtesting, trading, futures, prop firm, algorithmic trading",
)
