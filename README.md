# PyPI package `aioairq`

Python library to retrieve data asynchronous from air-Q.

This is primarily thought for the implementation of the air-Q plugin for [home-assistant](https://github.com/CorantGmbH/home-assistant-core), but may also be helpfull in general.

This will be published on PyPI when finished.

* For creation followed the guidlines [here](https://betterscientificsoftware.github.io/python-for-hpc/tutorials/python-pypi-packaging/)

## Retrieve data from air-Q

```python
import asyncio

from aioairq import AirQ

address = "123ab_air-q.local"
password = "airqsetup"
airq = AirQ(address, password)

loop = asyncio.get_event_loop()

data = loop.run_until_complete(airq.data)
average = loop.run_until_complete(airq.average)
config = loop.run_until_complete(airq.config)
```
