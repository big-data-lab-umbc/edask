from typing import Dict, Any, Union, List, Callable, Optional
import zmq, traceback, time, logging, xml, socket, abc, dask, threading
from edas.workflow.module import edasOpManager
from edas.process.task import Job
from edas.workflow.data import EDASDataset
from dask.distributed import Client, Future, LocalCluster
from edas.util.logging import EDASLogger
from edas.portal.cluster import EDASCluster
from stratus.handlers.endpoint.base import Task, Status
from edas.config import EdaskEnv
import random, string, os, queue, datetime, atexit, multiprocessing, errno, uuid
from threading import Thread
import xarray as xa

class ExecHandlerBase(Task):
    __metaclass__ = abc.ABCMeta

    def __init__(self, clientId: str, jobId: str, **kwargs ):
        super(ExecHandlerBase, self).__init__(**kwargs)
        self.logger = EDASLogger.getLogger()
        self.clientId = clientId
        self.jobId = jobId
        self.cacheDir = kwargs.get( "cache", "/tmp")
        self.workers = kwargs.get( "workers", 1 )
        self.start_time = time.time()
        self.filePath = self.cacheDir + "/" + Job.randomStr(6) + ".nc"

    def updateStartTime( self):
        self.start_time = time.time()

    def getExpDir(self, proj: str, exp: str ) -> str:
        expDir =  self.cacheDir + "/experiments/" + proj + "/" + exp
        return self.mkDir( expDir )

    def getExpFile(self, proj: str, exp: str, name: str, type: str = "nc" ) -> str:
        expDir =  self.getExpDir( proj, exp )
        return expDir + "/" + name + "-" + Job.randomStr(6) + "." + type

    @abc.abstractmethod
    def processFailure(self, ex: Exception): pass

    @abc.abstractmethod
    def processResult(self, result: EDASDataset  ): pass

    def mkDir(self, dir: str ) -> str:
        try:
            os.makedirs(dir)
        except OSError as e:
            if e.errno != errno.EEXIST: raise
        return dir

class SubmissionThread(Thread):

    def __init__(self, job: Job, processResult, processFailure ):
        Thread.__init__(self)
        self.job = job
        self.processResult = processResult
        self.processFailure = processFailure
        self.logger =  EDASLogger.getLogger()

    def run(self):
        start_time = time.time()
        try:
            self.logger.info( "Running workflow for requestId " + self.job.requestId)
            result = edasOpManager.buildTask( self.job )
            self.logger.info( "Completed workflow in time " + str(time.time()-start_time) )
            self.processResult( result )
        except Exception as err:
            self.logger.error( "Execution error: " + str(err))
            self.logger.error( traceback.format_exc() )
            self.processFailure(err)

class ExecHandler(ExecHandlerBase):

    def __init__( self, clientId: str, _job: Job, portal = None, **kwargs ):
        from edas.portal.base import EDASPortal
        super(ExecHandler, self).__init__(clientId, _job.requestId, **kwargs)
        self.portal: EDASPortal = portal
        self.sthread = None
        self._processResults = True
        self.results: List[EDASDataset] = []
        self.job = _job
        self._status = Status.IDLE

    def execJob(self, job: Job ) -> SubmissionThread:
        self.sthread = SubmissionThread( job, self.processResult, self.processFailure )
        self.sthread.start()
        self.logger.info( " ----------------->>> Submitted request for job " + job.requestId )
        return self.sthread

    @property
    def status(self):
        return self._status

    def getEDASResult(self, timeout=None, block=False) -> Optional[EDASDataset]:
        self._processResults = False
        if block:
            self.sthread.join(timeout)
            return self.mergeResults()
        else:
            if self._status == Status.COMPLETED:
                return self.mergeResults()
            else: return None

    def getResult(self, timeout=None, block=False) ->  Optional[xa.Dataset]:
        edasResult = self.getEDASResult(timeout,block)
        return edasResult.xr if edasResult is not None else None

    def processResult( self, result: EDASDataset ):
        self.results.append( result )
        self._processFinalResult( )
        if self.portal: self.portal.removeHandler( self.clientId, self.jobId )
        self._status = Status.COMPLETED
        self.logger.info(" ----------------->>> REQUEST COMPLETED "  )

    def _processFinalResult( self ):
        assert len(self.results), "No results generated by request"
        if self._processResults:
            self.logger.info(" ----------------->>> Process Final Result " )
            result = self.mergeResults()
            try:
                savePath = result.save()
                if self.portal:
                    sendData = self.job.runargs.get( "sendData", "true" ).lower().startswith("t")
                    self.portal.sendFile( self.clientId, self.jobId, result.id, savePath, sendData )
                else:
                    self.printResult(savePath)
            except Exception as err:
                self.logger.error( "Error processing final result: " + str(err) )
                self.logger.info(traceback.format_exc())
                if self.portal:
                    self.portal.sendFile(self.clientId, self.jobId, result.id, "", False )

    def printResult( self, filePath: str ):
        dset = xa.open_dataset(filePath)
        print( str(dset) )

    def mergeResults(self) -> EDASDataset:
        mergeMethod: str = self.results[0]["merge"]
        if mergeMethod is None: return EDASDataset.merge( self.results )
        mergeToks = mergeMethod.split(":")
        return self.getBestResult( mergeToks[0].strip().lower(), mergeToks[1].strip().lower() )

    def getBestResult(self, method: str, parm: str )-> EDASDataset:
        bestResult = None
        bestValue = None
        values = []
        for result in self.results:
            pval = result[parm]
            assert pval, "Error, parameter '{}' not defined in dataset".format( parm )
            values.append(float(pval))
            if bestResult is None or self.compare( method, float(pval), bestValue ):
                bestResult = result
                bestValue = float(pval)
        return bestResult

    def compare(self, method: str, current: float, threshold: float ):
        if method == "min": return current < threshold
        if method == "max": return current > threshold
        raise Exception( "Unknown comparison method: " + method )

    @classmethod
    def getTbStr( cls, ex ) -> str:
        if ex.__traceback__  is None: return ""
        tb = traceback.extract_tb( ex.__traceback__ )
        return " ".join( traceback.format_list( tb ) )

    @classmethod
    def getErrorReport( cls, ex ):
        try:
            errMsg = getattr( ex, 'message', repr(ex) )
            return errMsg + ">~>" +  str( cls.getTbStr(ex) )
        except:
            return repr(ex)

    def processFailure(self, ex: Exception):
        error_message = self.getErrorReport( ex )
        if self.portal:
            self.portal.sendErrorReport( self.clientId, self.jobId, error_message )
            self.portal.removeHandler( self.clientId, self.jobId )
        else:
            self.logger.error( error_message )
        self._status = Status.ERROR
        self._parms["error"] = error_message

    # def iterationCallback( self, resultFuture: Future ):
    #   status = resultFuture.status
    #   if status == "finished":
    #       self.completed = self.completed + 1
    #       result: EDASDataset = resultFuture.result()
    #       self.results.append(result)
    #   else:
    #       try:                      self.processFailure(Exception("status = " + status + "\n>~>" + str(traceback.format_tb(resultFuture.traceback(60)))))
    #       except TimeoutError:
    #           try:                  self.processFailure(Exception("status = " + status + ", Exception = " + str(resultFuture.exception(60))))
    #           except TimeoutError:
    #                                 self.processFailure(Exception("status = " + status))
    #   if self.completed == self.workers:
    #     self._processFinalResult()
    #     if self.portal:
    #         self.portal.removeHandler( self.clientId, self.jobId )

class GenericProcessManager:
  __metaclass__ = abc.ABCMeta

  @abc.abstractmethod
  def submitProcess(self, service: str, job: Job, resultHandler: ExecHandler)-> str: pass

  @abc.abstractmethod
  def getResult( self, service: str, resultId: str ): pass

  @abc.abstractmethod
  def getResultStatus( self, service: str, resultId: str ): pass

  @abc.abstractmethod
  def hasResult( self, service: str, resultId: str )-> bool: pass

  @abc.abstractmethod
  def serverIsDown( self )-> bool: pass

  @abc.abstractmethod
  def term(self): pass

  def waitUntilJobCompletes( self, service: str, resultId: str  ):
    while( not self.hasResult(service,resultId) ): time.sleep(0.5)

class ProcessManager(GenericProcessManager):

  def __init__( self, serverConfiguration: Dict[str,str], cluster: EDASCluster = None ):
      self.config = serverConfiguration
      self.logger =  EDASLogger.getLogger()
      self.cluster = cluster
      self.submitters = []
      if self.cluster is not None:
          self.logger.info( "Initializing Dask-distributed cluster with scheduler address: " + self.cluster.scheduler_address )
          self.client = Client( self.cluster.scheduler_address )
      else:
          nWorkers = int( self.config.get("dask.nworkers",multiprocessing.cpu_count()) )
          self.logger.info( "Initializing Local Dask cluster with {} workers".format(nWorkers) )
          self.client = Client( LocalCluster( n_workers=nWorkers ) )
          self.client.submit( lambda x: edasOpManager.buildIndices( x ), nWorkers )

  def term(self):
      self.client.close()

  def runProcess( self, job: Job ) -> EDASDataset:
    start_time = time.time()
    try:
        self.logger.info( "Running workflow for requestId " + job.requestId)
        result = edasOpManager.buildTask( job )
        self.cluster.logMetrics()
        self.logger.info( "Completed workflow in time " + str(time.time()-start_time) )
        return result
    except Exception as err:
        self.logger.error( "Execution error: " + str(err))
        traceback.print_exc()


  def submitProcess(self, service: str, job: Job, resultHandler: ExecHandler):
      submitter: SubmissionThread = SubmissionThread( job, resultHandler )
      self.submitters.append( submitter )
      submitter.start()


