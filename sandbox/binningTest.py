from edas.process.test import LocalTestManager
import xarray as xr
from xarray.core.resample import DatasetResample

testMgr = LocalTestManager("TESTS","binning")

domains = [{"name": "d0", "lat": {"start": 0, "end": 10, "system": "values"},
            "lon": {"start": 0, "end": 10, "system": "values"},
            "time": {"start": '1980-01-01T00', "end": '1989-01-01T00', "system": "values"}}]
variables = [{"uri": testMgr.getAddress("merra2", "tas"), "name": "tas:v0", "domain": "d0"}]
operations = [{"name": "edas.subset", "input": "v0"}]
results = testMgr.testExec(domains, variables, operations)
ds = results[0].xr
# taxis = results[0].inputs[0].data.coords.get("t")
# print( results[0].inputs[0].data.coords.get("t").dt )
rs: DatasetResample = ds.resample(t='Q-FEB')
print( rs.groups )
