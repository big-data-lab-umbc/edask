import numpy as np
import pandas as pd
import xarray as xr
import time
from dask.distributed import Client
from edask.dataCollection import Collection

print "STARTUP"
start = time.time()
collection = "cip_merra2_mth"
varName = 'KE'

try:
    client = Client('cldradn101:8786')

    print "READ " + collection

    collection = Collection.get( collection )
    ds_m = xr.open_mfdataset( collection.pathList(varName), autoclose=True, data_vars=['KE'], parallel=True)

    print "COMPUTE MEAN, Result:"

    #    print ds_m.KE.mean(dim='time').mean(dim='lon').mean(dim='lat').values
    print ds_m.KE.mean().values

    print " Completed computation in " + str(time.time() - start) + " seconds"

finally:
    print "SHUTDOWN"
    client.close()
