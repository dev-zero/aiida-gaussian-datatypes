#!/usr/bin/env python

import json
from setuptools import setup, find_packages
from pathlib import Path

CURRENT_DIR = Path(__file__).parent


def get_long_description():
    readme_md = CURRENT_DIR / "README.md"
    with open(readme_md, encoding="utf8") as ld_file:
        return ld_file.read()


if __name__ == "__main__":
    # Provide static information in setup.json
    # such that it can be discovered automatically
    with open("setup.json", "r") as info:
        kwargs = json.load(info)
    setup(
        packages=find_packages(),
        long_description=get_long_description(),
        long_description_content_type="text/markdown",
        **kwargs,
    )
