import logging, time
import xarray as xr
from dask.distributed import Client, Future, LocalCluster
from edas.config import EdaskEnv
from typing import List, Optional, Tuple, Dict, Any

variable = "tas"
appConf = { "sources.allowed": "collection,https", "log.metrics": "true"}
EdaskEnv.update(appConf)

client = Client( "127.0.0.1:8786", timeout=60 )

if variable == "tas":
    pathList=['/dass/dassnsd/data01/cldra/data/pubrepo/CREATE-IP/data/reanalysis/ECMWF/IFS-Cy31r2/mon/atmos/ta/ta_Amon_reanalysis_IFS-Cy31r2_198001-198012.nc', '/dass/dassnsd/data01/cldra/data/pubrepo/CREATE-IP/data/reanalysis/ECMWF/IFS-Cy31r2/mon/atmos/ta/ta_Amon_reanalysis_IFS-Cy31r2_198101-198112.nc', '/dass/dassnsd/data01/cldra/data/pubrepo/CREATE-IP/data/reanalysis/ECMWF/IFS-Cy31r2/mon/atmos/ta/ta_Amon_reanalysis_IFS-Cy31r2_198201-198212.nc', '/dass/dassnsd/data01/cldra/data/pubrepo/CREATE-IP/data/reanalysis/ECMWF/IFS-Cy31r2/mon/atmos/ta/ta_Amon_reanalysis_IFS-Cy31r2_198301-198312.nc', '/dass/dassnsd/data01/cldra/data/pubrepo/CREATE-IP/data/reanalysis/ECMWF/IFS-Cy31r2/mon/atmos/ta/ta_Amon_reanalysis_IFS-Cy31r2_198401-198412.nc', '/dass/dassnsd/data01/cldra/data/pubrepo/CREATE-IP/data/reanalysis/ECMWF/IFS-Cy31r2/mon/atmos/ta/ta_Amon_reanalysis_IFS-Cy31r2_198501-198512.nc', '/dass/dassnsd/data01/cldra/data/pubrepo/CREATE-IP/data/reanalysis/ECMWF/IFS-Cy31r2/mon/atmos/ta/ta_Amon_reanalysis_IFS-Cy31r2_198601-198612.nc', '/dass/dassnsd/data01/cldra/data/pubrepo/CREATE-IP/data/reanalysis/ECMWF/IFS-Cy31r2/mon/atmos/ta/ta_Amon_reanalysis_IFS-Cy31r2_198701-198712.nc', '/dass/dassnsd/data01/cldra/data/pubrepo/CREATE-IP/data/reanalysis/ECMWF/IFS-Cy31r2/mon/atmos/ta/ta_Amon_reanalysis_IFS-Cy31r2_198801-198812.nc', '/dass/dassnsd/data01/cldra/data/pubrepo/CREATE-IP/data/reanalysis/ECMWF/IFS-Cy31r2/mon/atmos/ta/ta_Amon_reanalysis_IFS-Cy31r2_198901-198912.nc', '/dass/dassnsd/data01/cldra/data/pubrepo/CREATE-IP/data/reanalysis/ECMWF/IFS-Cy31r2/mon/atmos/ta/ta_Amon_reanalysis_IFS-Cy31r2_199001-199012.nc', '/dass/dassnsd/data01/cldra/data/pubrepo/CREATE-IP/data/reanalysis/ECMWF/IFS-Cy31r2/mon/atmos/ta/ta_Amon_reanalysis_IFS-Cy31r2_199101-199112.nc', '/dass/dassnsd/data01/cldra/data/pubrepo/CREATE-IP/data/reanalysis/ECMWF/IFS-Cy31r2/mon/atmos/ta/ta_Amon_reanalysis_IFS-Cy31r2_199201-199212.nc', '/dass/dassnsd/data01/cldra/data/pubrepo/CREATE-IP/data/reanalysis/ECMWF/IFS-Cy31r2/mon/atmos/ta/ta_Amon_reanalysis_IFS-Cy31r2_199301-199312.nc', '/dass/dassnsd/data01/cldra/data/pubrepo/CREATE-IP/data/reanalysis/ECMWF/IFS-Cy31r2/mon/atmos/ta/ta_Amon_reanalysis_IFS-Cy31r2_199401-199412.nc', '/dass/dassnsd/data01/cldra/data/pubrepo/CREATE-IP/data/reanalysis/ECMWF/IFS-Cy31r2/mon/atmos/ta/ta_Amon_reanalysis_IFS-Cy31r2_199501-199512.nc', '/dass/dassnsd/data01/cldra/data/pubrepo/CREATE-IP/data/reanalysis/ECMWF/IFS-Cy31r2/mon/atmos/ta/ta_Amon_reanalysis_IFS-Cy31r2_199601-199612.nc', '/dass/dassnsd/data01/cldra/data/pubrepo/CREATE-IP/data/reanalysis/ECMWF/IFS-Cy31r2/mon/atmos/ta/ta_Amon_reanalysis_IFS-Cy31r2_199701-199712.nc', '/dass/dassnsd/data01/cldra/data/pubrepo/CREATE-IP/data/reanalysis/ECMWF/IFS-Cy31r2/mon/atmos/ta/ta_Amon_reanalysis_IFS-Cy31r2_199801-199812.nc', '/dass/dassnsd/data01/cldra/data/pubrepo/CREATE-IP/data/reanalysis/ECMWF/IFS-Cy31r2/mon/atmos/ta/ta_Amon_reanalysis_IFS-Cy31r2_199901-199912.nc', '/dass/dassnsd/data01/cldra/data/pubrepo/CREATE-IP/data/reanalysis/ECMWF/IFS-Cy31r2/mon/atmos/ta/ta_Amon_reanalysis_IFS-Cy31r2_200001-200012.nc', '/dass/dassnsd/data01/cldra/data/pubrepo/CREATE-IP/data/reanalysis/ECMWF/IFS-Cy31r2/mon/atmos/ta/ta_Amon_reanalysis_IFS-Cy31r2_200101-200112.nc', '/dass/dassnsd/data01/cldra/data/pubrepo/CREATE-IP/data/reanalysis/ECMWF/IFS-Cy31r2/mon/atmos/ta/ta_Amon_reanalysis_IFS-Cy31r2_200201-200212.nc', '/dass/dassnsd/data01/cldra/data/pubrepo/CREATE-IP/data/reanalysis/ECMWF/IFS-Cy31r2/mon/atmos/ta/ta_Amon_reanalysis_IFS-Cy31r2_200301-200312.nc', '/dass/dassnsd/data01/cldra/data/pubrepo/CREATE-IP/data/reanalysis/ECMWF/IFS-Cy31r2/mon/atmos/ta/ta_Amon_reanalysis_IFS-Cy31r2_200401-200412.nc', '/dass/dassnsd/data01/cldra/data/pubrepo/CREATE-IP/data/reanalysis/ECMWF/IFS-Cy31r2/mon/atmos/ta/ta_Amon_reanalysis_IFS-Cy31r2_200501-200512.nc', '/dass/dassnsd/data01/cldra/data/pubrepo/CREATE-IP/data/reanalysis/ECMWF/IFS-Cy31r2/mon/atmos/ta/ta_Amon_reanalysis_IFS-Cy31r2_200601-200612.nc', '/dass/dassnsd/data01/cldra/data/pubrepo/CREATE-IP/data/reanalysis/ECMWF/IFS-Cy31r2/mon/atmos/ta/ta_Amon_reanalysis_IFS-Cy31r2_200701-200712.nc', '/dass/dassnsd/data01/cldra/data/pubrepo/CREATE-IP/data/reanalysis/ECMWF/IFS-Cy31r2/mon/atmos/ta/ta_Amon_reanalysis_IFS-Cy31r2_200801-200812.nc', '/dass/dassnsd/data01/cldra/data/pubrepo/CREATE-IP/data/reanalysis/ECMWF/IFS-Cy31r2/mon/atmos/ta/ta_Amon_reanalysis_IFS-Cy31r2_200901-200912.nc', '/dass/dassnsd/data01/cldra/data/pubrepo/CREATE-IP/data/reanalysis/ECMWF/IFS-Cy31r2/mon/atmos/ta/ta_Amon_reanalysis_IFS-Cy31r2_201001-201012.nc', '/dass/dassnsd/data01/cldra/data/pubrepo/CREATE-IP/data/reanalysis/ECMWF/IFS-Cy31r2/mon/atmos/ta/ta_Amon_reanalysis_IFS-Cy31r2_201101-201112.nc']
elif variable == "ta":
    pathList=['/dass/dassnsd/data01/cldra/data/pubrepo/CREATE-IP/data/reanalysis/ECMWF/IFS-Cy31r2/mon/atmos/tas/tas_Amon_reanalysis_IFS-Cy31r2_197901-201712.nc']
else:
    raise Exception( f"Unknown variable: {variable}" )

start = time.time()
dset: xr.Dataset = xr.open_mfdataset( pathList, data_vars=[variable], parallel=True )
var: xr.Variable = dset.variables.get(variable)
print( f"Opened dataset, shape: {var.shape}, completed  in {str(time.time() - start)} seconds"  )
