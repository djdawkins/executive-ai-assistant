# filepath: c:\Users\ddawk\OneDrive\Desktop\codeCamp\executive-ai-assistant\setup.py
from setuptools import setup, find_packages

setup(
    name="executive-ai-assistant",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        # Add your dependencies here, e.g., "requests>=2.25.1"
    ],
    include_package_data=True,
)