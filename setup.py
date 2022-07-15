"""Setup module for aioairq."""
from pathlib import Path

from setuptools import setup

PROJECT_DIR = Path(__file__).parent.resolve()
README_FILE = PROJECT_DIR / "README.md"
VERSION = "0.1.0"


setup(
    name="aioairq",
    version=VERSION,
    license="Apache License 2.0",
    url="https://github.com/CorantGmbH/aioairq",
    author="Daniel Lehmann",
    author_email="daniel.lehmann@air-q.com",
    description="Asynchronous library to retrieve data from air-Q devices.",
    long_description=README_FILE.read_text(encoding="utf-8"),
    long_description_content_type="text/markdown",
    packages=["aioairq"],
    python_requires=">=3.9",
    package_data={"aioairq": ["py.typed"]},
    zip_safe=True,
    platforms="any",
    install_requires=list(
        val.strip() for val in open("requirements.txt", encoding="utf-8")
    ),
    classifiers=[
        "Intended Audience :: Developers",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
)
