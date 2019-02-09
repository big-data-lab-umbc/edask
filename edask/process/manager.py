from typing import Dict, Any, Union, List, Callable, Optional
import zmq, traceback, time, logging, xml, socket, abc, dask, threading
from edask.workflow.module import edasOpManager
from edask.process.task import Job
from edask.workflow.data import EDASDataset
from dask.distributed import Client, Future, LocalCluster
from edask.util.logging import EDASLogger
from edask.portal.cluster import EDASCluster
from edask.config import EdaskEnv
import random, string, os, queue, datetime, atexit, multiprocessing, errno, uuid
from threading import Thread
import xarray as xa

class ExecHandlerBase:
    __metaclass__ = abc.ABCMeta

    def __init__(self, clientId: str, jobId: str, **kwargs ):
        self.logger = EDASLogger.getLogger()
        self.clientId = clientId
        self.jobId = jobId
        self.cacheDir = kwargs.get( "cache", "/tmp")
        self.workers = kwargs.get( "workers", 1 )
        self.completed = 0
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
    def successCallback(self, resultFuture: Future): pass

    @abc.abstractmethod
    def failureCallback(self, ex: Exception): pass

    @abc.abstractmethod
    def processResult(self, result: EDASDataset  ): pass

    @abc.abstractmethod
    def iterationCallback( self, resultFuture: Future ): pass

    def mkDir(self, dir: str ) -> str:
        try:
            os.makedirs(dir)
        except OSError as e:
            if e.errno != errno.EEXIST: raise
        return dir

class ExecHandler(ExecHandlerBase):

    def __init__( self, clientId: str, _job: Job, portal, **kwargs ):
        from edask.portal.base import EDASPortal
        super(ExecHandler, self).__init__(clientId, _job.requestId, **kwargs)
        self.portal: EDASPortal = portal
        self.client = portal.processManager.client
        self._processResults = True
        self.results: List[EDASDataset] = []
        self._completed = False
        self.job = _job
        self.startTime = time.time()

    def execJob( self ):
        resultFuture: Future = self.client.submit( edasOpManager.buildTask, self.job )
        resultFuture.add_done_callback( self.processResult )
        self.logger.info( " ----------------->>> Submitted request for job " + self.job.requestId )

    def getResult(self):
        self._processResults = False
        while self._completed == False:
            time.sleep(0.2)
        return self.mergeResults()

    def processResult( self, resultFuture: Future ):
        result: EDASDataset = resultFuture.result()
        self.results.append( result )
        self._processFinalResult( )
        if self.portal: self.portal.removeHandler( self.clientId, self.jobId )
        self.logger.info("-" * 50 )
        self.logger.info(" Completed job in " + str( time.time() - self.startTime ) + " seconds")
        self.logger.info("-" * 50)

    def successCallback(self, resultFuture: Future):
      status = resultFuture.status
      if status == "finished":
          self.results.append( resultFuture.result() )
          self.logger.info( " Completed computation " + self.jobId + " in " + str(time.time() - self.start_time) + " seconds" )
          self._processFinalResult( )
      else:
          self.failureCallback( resultFuture.result() )
      if self.portal: self.portal.removeHandler( self.clientId, self.jobId )

    def _processFinalResult( self ):
        assert len(self.results), "No results generated by request"
        if self._processResults:
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
                self.portal.sendFile(self.clientId, self.jobId, result.id, "", False )
        self._completed = True

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

    def getTbStr(self, ex ) -> str:
        if ex.__traceback__  is None: return ""
        tb = traceback.extract_tb( ex.__traceback__ )
        return " ".join( traceback.format_list( tb ) )

    def getErrorReport(self, ex ):
        errMsg = getattr( ex, 'message', repr(ex) )
        return errMsg + ">~>" +  str( self.getTbStr(ex) )

    def failureCallback(self, ex: Exception ):
        try: error_message = self.getErrorReport( ex )
        except: error_message = repr(ex)
        if self.portal:
            self.portal.sendErrorReport( self.clientId, self.jobId, error_message )
            self.portal.removeHandler( self.clientId, self.jobId )
        else:
            self.logger.error( error_message )

    def iterationCallback( self, resultFuture: Future ):
      status = resultFuture.status
      if status == "finished":
          self.completed = self.completed + 1
          result: EDASDataset = resultFuture.result()
          self.results.append(result)
      else:
          try:                      self.failureCallback( Exception("status = " + status + "\n>~>" + str( traceback.format_tb(resultFuture.traceback(60)) ) ) )
          except TimeoutError:
              try:                  self.failureCallback( Exception("status = " + status + ", Exception = " + str( resultFuture.exception(60) )  ) )
              except TimeoutError:
                                    self.failureCallback( Exception("status = " + status  ) )
      if self.completed == self.workers:
        self._processFinalResult()
        if self.portal:
            self.portal.removeHandler( self.clientId, self.jobId )

class GenericProcessManager:
  __metaclass__ = abc.ABCMeta

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
          self.logger.info( "Initializing Dask cluster with cluster" )
          self.client = Client( self.cluster.scheduler.address )
      else:
          nWorkers = int( self.config.get("dask.nworkers",multiprocessing.cpu_count()) )
          self.logger.info( "Initializing Local Dask cluster with {} workers".format(nWorkers) )
          self.client = Client( LocalCluster( n_workers=nWorkers ) )
          self.client.submit( lambda x: edasOpManager.buildIndices( x ), nWorkers )

  def term(self):
      self.client.close()

  # def runProcess( self, job: Job ) -> EDASDataset:
  #   start_time = time.time()
  #   try:
  #       self.logger.info( " @SW: Submitting workflow using client for requestId " + job.requestId)
  #       future_result = self.client.submit( edasOpManager.buildTask, job )
  #       self.cluster.logMetrics()
  #       result = future_result.result()
  #       self.logger.info( "Completed workflow in time " + str(time.time()-start_time) )
  #       return result
  #   except Exception as err:
  #       self.logger.error( "Execution error: " + str(err))
  #       traceback.print_exc()


  # def submitProcess(self, service: str, job: Job, resultHandler: ExecHandler):
  #     self.logger.info(" @SW: Submitting workflow using resultHandler for requestId " + job.requestId)
  #     submitter: SubmissionThread = SubmissionThread( job, resultHandler )
  #     self.submitters.append( submitter )
  #     submitter.start()


