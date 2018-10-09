from edask.process.test import TestManager
from edask.workflow.data import EDASDataset
import numpy.ma as ma
import xarray as xa
import logging

class CollectionsTESTS:

    def __init__(self):
        self.logger =  logging.getLogger()
        self.mgr = TestManager("PlotTESTS","demo")

    def print(self, results: EDASDataset):
      for variable in results.inputs:
        result = variable.xr.load()
        self.logger.info("\n\n ***** Result {}, shape = {}".format(result.name, str(result.shape)))
        self.logger.info(result)

    def compute_eofs_TN(self):
        domains = [{"name": "d0", "lat": {"start": -80, "end": 80, "system": "values"},  "time": {"start": '1880-01-01T00', "end": '2012-01-01T00', "system": "values"} }]
        variables = [{"uri": "collection:cip_20crv2c_mth", "name": "ts:v0", "domain": "d0"}]
        operations = [  {"name": "xarray.decycle", "axis":"t", "input": "v0", "norm":"true", "result":"dc"},
                        {"name": "xarray.detrend", "axis": "t", "input": "dc", "wsize": 50, "result": "dt"},
                        {"name": "xarray.eof", "modes": 4, "input": "dt", "archive":"eofs-20crv-ts-TN"  } ]
        results = self.mgr.testExec(domains, variables, operations)
        self.print( results )

if __name__ == '__main__':
    tester = CollectionsTESTS()
    result = tester.compute_eofs_TN()