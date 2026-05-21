from setuptools import setup, find_packages

setup(
    name="mediacrawler",
    version="0.1.0",
    description="Social media crawler for Xiaohongshu, Douyin, etc.",
    packages=find_packages(include=[
        "api", "api.*",
        "base", "base.*",
        "libs", "libs.*",
        "cache", "cache.*",
        "model", "model.*",
        "proxy", "proxy.*",
        "store", "store.*",
        "config", "config.*",
        "cmd_arg", "cmd_arg.*",
        "constant", "constant.*",
        "database", "database.*",
        "media_platform", "media_platform.*",
    ]),
    python_requires=">=3.11",
    install_requires=[
        "httpx>=0.27.0",
        "playwright>=1.45.0",
        "tenacity>=8.2.2",
        "pyhumps>=3.8.0",
        "websockets>=15.0.1",
    ],
)
