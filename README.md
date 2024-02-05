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

# You can now create a script (see example above) and run it
vim hello-air-q.py
python hello-air-q.py

# Optional: Testing

# Install optional dependencies for testing
pip install -e ".[tests]"

# If you get an error message about incompatible version,
# try to install the packages separately:
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

# end Optional: Testing

# Optional: Linting
pip install pylint
pylint aioairq/*.py

# Leave the virtual environment when you are done
deactivate
```
