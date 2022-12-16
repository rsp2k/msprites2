import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="msprites2",
    version="0.9",
    author="Ryan Malloy",
    author_email="ryan@supported.systems",
    description="Create thumbnail spritesheet and webvtt from video files",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/rsp2k/msprites2",
    project_urls = {
        "Bug Tracker": "https://github.com/rsp2k/msprites2/issues",
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    packages=setuptools.find_packages(),
    python_requires=">=3.6",
)