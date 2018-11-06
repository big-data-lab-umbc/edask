from edask.process.manager import ProcessManager, ExecResultHandler
from edask.portal.base import Message, Response
from dask.distributed import Future
from typing import Sequence, List, Dict, Mapping, Optional, Any
import matplotlib.pyplot as plt
from edask.util.logging import EDASLogger
from edask.portal.plotters import plotter
from edask.process.task import Job
from edask.process.test import TestDataManager
import xarray as xa
import logging, traceback, time, os

# class AppTestsResultHandler(ResultHandler):
#
#     def __init__(self, clientId: str, jobId: str, **kwargs ):
#         super(AppTestsResultHandler,self).__init__(clientId,jobId,**kwargs)
#         self.results: List[EDASDataset] = []
#         self.logger =  EDASLogger.getLogger()
#
#     def successCallback(self, resultFuture: Future):
#         status = resultFuture.status
#         print("SUCCESS")
#         if status == "finished":
#             self.results.append(resultFuture.result())
#             self.processFinalResult()
#         else:
#             self.failureCallback( Exception("status = " + status) )
#
#     def getMergedResult(self)-> EDASDataset:
#         assert len(self.results), "No results generated by request"
#         mergeMethod: str = self.results[0]["merge"]
#         if mergeMethod is None: return EDASDataset.merge( self.results )
#         mergeToks = mergeMethod.split(":")
#         return self.getBestResult(  mergeToks[0].strip().lower(), mergeToks[1].strip().lower() )
#
#     def getBestResult(self, method: str, parm: str )-> EDASDataset:
#         bestResult = None
#         bestValue = None
#         values = []
#         for result in self.results:
#             pval = result[parm]
#             assert pval, "Error, parameter '{}' not defined in dataset".format( parm )
#             values.append(float(pval))
#             if bestResult is None or self.compare( method, float(pval), bestValue ):
#                 bestResult = result
#                 bestValue = float(pval)
#         self.logger.info( "Find {} of {} values: {}, result = {}".format( method, parm, str(values), bestValue ) )
#         return bestResult
#
#     def compare(self, method: str, current: float, threshold: float ):
#         if method == "min": return current < threshold
#         if method == "max": return current > threshold
#         raise Exception( "Unknown comparison method: " + method )
#
#     def processFinalResult(self):
#         result: EDASDataset = self.getMergedResult()
#         savePath = result.save( self.archivePath( result["archive"] ) )
#         self.printResult(savePath)
#
#     def failureCallback(self, ex: Exception ):
#         print( "ERROR: "+ str(ex) )
#         print( traceback.format_exc() )
#
#     def archivePath(self, archivePath: str  ) -> str:
#         if not archivePath: return self.filePath
#         toks = archivePath.split(":")
#         proj =  toks[0]
#         exp = toks[1] if len(toks) > 1 else Job.randomStr(6)
#         return Archive.getExperimentPath( proj, exp )
#
#     def printResult( self, filePath: str ):
#         dset = xa.open_dataset(filePath)
#         print( str(dset) )
#
#     def iterationCallback( self, resultFuture: Future ):
#       status = resultFuture.status
#       print( "ITERATE: status = {}, iteration = {}".format( resultFuture.status, self.completed ) )
#       if status == "finished":
#           self.completed = self.completed + 1
#           result: EDASDataset = resultFuture.result()
#           self.results.append(result)
#       else:
#           self.failureCallback( Exception("status = " + status) )
#
#       if self.completed == self.workers:
#           self.processFinalResult()

class AppTests:

    def __init__( self, _project: str, _experiment: str, appConfiguration: Dict[str,str] ):
        self.logger =  EDASLogger.getLogger()
        self.project = _project
        self.experiment = _experiment
        self.processManager = ProcessManager(appConfiguration)

    def exec( self, name, domains: List[Dict[str, Any]], variables: List[Dict[str, Any]], operations: List[Dict[str, Any]] )-> Response:
        job1 = Job.init( self.project, self.experiment, name, domains, variables, operations )
        return self.runJob( job1 )

    def runJob( self, job: Job, clientId: str = "local" )-> Response:
        try:
          resultHandler = ExecResultHandler( "local", job.process, workers=job.workers)
          self.processManager.submitProcess(job.process, job, resultHandler)
          return Message(clientId, job.process, resultHandler.filePath)
        except Exception as err:
            self.logger.error( "Caught execution error: " + str(err) )
            traceback.print_exc()
            return Message(clientId, job.process, str(err))

    def plot( self, filePath: str ):
        try:
            dset = xa.open_dataset(filePath)
            vars = list( dset.data_vars.values() )
            nplots = len( vars )
            fig, axes = plt.subplots(ncols=nplots)
            self.logger.info( "Plotting {} plots ".format(nplots) )
            if nplots == 1:
                vars[0].plot(ax=axes)
            else:
                for iaxis, result in enumerate( vars ):
                    result.plot(ax=axes[iaxis])
            plt.show()
        except Exception as err:
            self.logger.error( "Error Plotting: {} ".format(str(err)) )

    def test_detrend(self):
        domains = [ {"name": "d0", "lat": {"start": 0, "end": 50, "system": "values"}, "lon": {"start": 0, "end": 50, "system": "values"}, "time": { "start": '1990-01-01', "end": '2000-01-01', "system":"values" }  },
                    {"name": "d1", "lat": {"start": 20, "end": 20, "system": "values"}, "lon": {"start": 20, "end": 20, "system": "values"}}]
        variables = [{"uri":  TestDataManager.getAddress("merra2", "tas"), "name": "tas:v0", "domain":"d0"}]
        operations = [  {"name": "xarray.decycle", "input": "v0", "result":"dc"},
                        {"name": "xarray.norm", "axis":"xy", "input": "dc", "result":"dt" },
                        {"name": "xarray.subset", "input": "dt", "domain":"d1"} ]
        return self.exec( "test_detrend", domains, variables, operations )

    def test_norm(self):
        domains = [{"name": "d0", "lat": {"start": 20, "end": 40, "system": "values"}, "lon": {"start": 60, "end": 100, "system": "values"}}]
        variables = [{"uri": TestDataManager.getAddress("merra2", "tas"), "name": "tas:v0", "domain": "d0"}]
        operations = [ { "name": "xarray.norm", "axis": "xy", "input": "v0" } ]
        return self.exec( "test_detrend", domains, variables, operations )

    def plotPerformanceXa(self, filePath: str):
        while True:
            if os.path.isfile(filePath):
                dset = xa.open_dataset( filePath, autoclose=True )
                plotter.plotPerformanceXa(dset, "20crv-ts")
                print("EXITING PLOT LOOP")
                return
            else:
                time.sleep(0.5)
                print( "." , end='' )

    def test_monsoon_learning(self):
        domains = [{"name": "d0",  "time": {"start": '1880-01-01T00', "end": '2005-01-01T00', "system": "values"} } ]
        variables = [{"uri": "archive:pcs-20crv-ts-TN", "name": "pcs:v0", "domain":"d0"}, {"uri": "archive:IITM/monsoon/timeseries","name":"AI:v1","domain":"d0", "offset":"1y"} ]
        operations = [  {"name": "xarray.filter", "input": "v0", "result": "v0f", "axis":"t", "sel": "aug"},
                        {"name": "keras.layer", "input": "v0f", "result":"L0", "axis":"m", "units":64, "activation":"relu"},
                        {"name": "keras.layer", "input": "L0", "result":"L1", "units":1, "activation":"linear" },
                        {"name": "xarray.norm", "input": "v1", "axis":"t", "result": "dc"},
                        {"name": "xarray.detrend", "input": "dc", "axis":"t", "wsize": 50, "result": "t1"},
                        {"name": "keras.train",  "axis":"t", "input": "L1,t1", "lr":0.002, "vf":0.2, "decay":0.002, "momentum":0.9, "epochs":1000, "batch":200, "iterations":50, "target":"t1", "archive":"model-20crv-ts" } ]
        return self.exec( "test_monsoon_learning", domains, variables, operations )

if __name__ == '__main__':
    tester = AppTests( "PlotTESTS", "demo", { "nWorkers":"4" } )
    result: Response = tester.test_monsoon_learning()
    tester.plotPerformanceXa( result.message() )




