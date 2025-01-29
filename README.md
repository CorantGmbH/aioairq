[![PyPI pyversions](https://img.shields.io/pypi/pyversions/aioairq.svg)](https://pypi.org/project/aioairq/0.3.0/)
[![PyPI downloads](https://pepy.tech/badge/aioairq)](https://pypi.org/project/aioairq/0.3.0/)
# PyPI package `aioairq`

Python library for asynchronous data access to local air-Q devices.

## Retrieve data from air-Q

At its present state, `AirQ` requires an `aiohttp` session to be provided by the user:

```python
import asyncio
import aiohttp
from aioairq import AirQ

ADDRESS = "123ab_air-q.local"
PASSWORD = "airqsetup"

async def main():
    async with aiohttp.ClientSession() as session:
        airq = AirQ(ADDRESS, PASSWORD, session)

        config = await airq.config
        print(f"Available sensors: {config['sensors']}")

        data = await airq.data
        print(f"Momentary data: {data}")

asyncio.run(main())
```

## Logging
Since version 0.4.4, `aioairq` supports a very verbose logging at the `DEBUG` level, especially in `AirQ.get_latest_data` method, which can cache the previous data and log the difference between the latest and the previous sensor readings. Note that this caching and difference calculation does not happen when the logging is set up to a higher level than `DEBUG`, incurring no additional overhead when not requested.

## Development

Example script for Linux how to run everything.

```sh
# Checkout the repository
git clone https://github.com/CorantGmbH/aioairq
cd aioairq

# Create a virtual environment
#
# We assume that your system has Python in version 3.9 or higher installed
# and accessible via `python3`. 
# - If this command is not found or references an older version, consult your distribution.
# - Depending on the distribution, you may need to install an additional package, e.g. `python3-venv`.
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e .
# Optionally, you may install developmental dependencies
# which include testing, linting/formatting, and pre-commit
pip install -e ".[dev]" # if errors, see below

# You can now create a script (see example above) and run it
vim hello-air-q.py
python hello-air-q.py
```

### Testing

```sh
# If you get an error message about incompatible version, when attempting
# pip install -e ".[dev]", you may try to install the packages separately:
#
# pip install pytest
# pip install pytest-asyncio

# Prepare an environment file
# (You don't want to type your passwords into the shell)
cat <<EOF >.env
export AIRQ_IP=192.168.168.42
export AIRQ_PASS=12345678
export AIRQ_MDNS=abcde_air-q.local
export AIRQ_HOSTNAME=air-q-livingroom
EOF

# Run the tests
source .env
pytest
```

### Contributing

This repository uses [pre-commit](https://pre-commit.com/) primarily to ensure linting and formatting using [Ruff](https://github.com/astral-sh/ruff) (besides codespell and yamlling). If you want to commit changes to this repository, make sure you have `pre-commit` installed (included among the `dev` extras). Then initialise the git hooks by running

```sh
pre-commit install
```

Once successfully installed, `ruff` git hook will be triggered upon `git commit` and it will lint and try to fix the code you are about to commit. Should any changes be made, the commit will be aborted and you will need to address the lints and stage the modified files to your commit before trying again.


### Linting

Ruff's rule list is far less exhaustive than that of `pylint`, so if you want, you can gain additional insight by running `pylint` (not installed as a part of the `dev` extras).

```sh
pip install pylint
pylint aioairq/*.py
```

Once done, you may leave the virtual environment

```sh
deactivate
```
