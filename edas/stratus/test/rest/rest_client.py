from stratus_endpoint.handler.base import TaskHandle, TaskResult
from typing import Sequence, List, Dict, Mapping, Optional, Any
from edas.process.test import TestDataManager as mgr
import xarray as xa
from stratus.app.core import StratusCore

if __name__ == "__main__":

    settings = dict( stratus=dict(type="rest", host="127.0.0.1", port="5000" ) )
    stratus = StratusCore(settings)
    client = stratus.getClient()
    time_range = {"start": "1980-01-01", "end": "1982-12-31", "crs": "timestamps"}
    uri = mgr.getAddress("merra2", "tas")

    requestSpec = dict(
        domain=[dict(name="d0", lat=dict(start=0, end=15, system="values"), lon=dict(start=20, end=30, system="values"), time=time_range) ],
        input=[dict(uri=uri, name="tas:v0", domain="d0")],
        operation=[dict(name="edas:ave", axis="xy", input="v0")],
        rid = "r1",
        cid = "c1"
    )

    task: TaskHandle = client.request(requestSpec)
    result: Optional[TaskResult] = task.getResult(block=True)
    dsets: List[xa.Dataset] = result.data
    for index, dset in enumerate(dsets):
        fileName = f"/tmp/edas_endpoint_test_result-{index}.nc"
        print(f"Got result[{index}]: Saving to file {fileName} ")

