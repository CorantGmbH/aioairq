[![PyPI pyversions](https://img.shields.io/pypi/pyversions/aioairq.svg)](https://pypi.org/project/aioairq/0.1.1/)
[![PyPI downloads](https://pepy.tech/badge/aioairq)](https://pypi.org/project/aioairq/0.1.1/)
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
