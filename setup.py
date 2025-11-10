from setuptools import setup, find_packages

setup(
    name="buddharauer",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "fast-agent-mcp>=0.3.17",
        "fastapi>=0.104.1",
        "uvicorn>=0.24.0",
        "gradio>=4.1.1",
        "chromadb>=0.4.18",
        "pymupdf>=1.23.7",
        "pillow>=10.1.0",
        "python-dotenv>=1.0.0",
        "pyyaml>=6.0.1",
    ],
    extras_require={
        "test": [
            "pytest>=7.4.3",
            "pytest-asyncio>=0.21.1",
            "pytest-cov>=4.1.0",
            "httpx>=0.25.1",
        ]
    },
)