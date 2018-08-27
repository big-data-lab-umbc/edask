from typing import Dict, Any, Union, List
import zmq, traceback, time, logging, xml, cdms2, socket, defusedxml, abc
from xml.etree.ElementTree import Element, ElementTree
from threading import Thread
from edask.workflow.module import edasOpManager
from edask.process.task import Job
from dask.distributed import Client, Future
import random, string, os, queue, datetime, atexit
from enum import Enum
import xarray as xa

class GenericProcessManager:
  __metaclass__ = abc.ABCMeta

  @abc.abstractmethod
  def executeProcess( self,  service: str, job: Job )-> str: pass

  @abc.abstractmethod
  def getResult( self, service: str, resultId: str )-> Element: pass

  @abc.abstractmethod
  def getResultStatus( self, service: str, resultId: str )-> Element: pass

  @abc.abstractmethod
  def hasResult( self, service: str, resultId: str )-> bool: pass

  @abc.abstractmethod
  def serverIsDown( self )-> bool: pass

  @abc.abstractmethod
  def term(self): pass

  def waitUntilJobCompletes( self, service: str, resultId: str  ):
    while( not self.hasResult(service,resultId) ): time.sleep(0.5)


class ProcessManager(GenericProcessManager):

  def __init__( self, serverConfiguration: Dict[str,str] ):
      self.config = serverConfiguration
      self.logger =  logging.getLogger()

  def term(self): pass

  def executeProcess( self, service: str, job: Job ) -> str:

      try:
            client = Client()
            self.logger.info("Defining workflow")
            result_future = client.submit( lambda x: edasOpManager.buildTask( x ), job )
            self.logger.info("Submitted computation")
            result_future.add_done_callback( self.processResult )

      except Exception:
            traceback.print_exc()

      finally:
            self.logger.info( "SHUTDOWN" )

      return ""

  def processResult(self , resultFuture: Future ):
      status = resultFuture.status
      if status == "finished":
          result = resultFuture.result()
          print( result )
      pass

      # request: TaskRequest = TaskRequest( job.requestId, job.identifier, dataInputsObj )
      #
      # serviceProvider = apiManager.getServiceProvider("edas")
      # ( job.requestId, serviceProvider.executeProcess( request, job.datainputs, job.runargs, executionCallback ) )


#
#
#   def alloc = if( _apiManagerOpt.isEmpty ) { _apiManagerOpt = Some( new APIManager( serverConfiguration ) ) }
#   def apiManager: APIManager = { alloc; _apiManagerOpt.get }
#   def serverIsDown: bool = { false; }
#
#   def unacceptable(msg: str): Unit = {
#     logger.error(msg)
#     throw new NotAcceptableException(msg)
#   }
#
#   def term = _apiManagerOpt.foreach( _.shutdown )
#
#   def describeProcess(service: str, name: str, runArgs: Dict[str,str]): xml.Elem = {
#     val serviceProvider = apiManager.getServiceProvider(service)
#     //        logger.info("Executing Service {}, Service provider = {} ".format( service, serviceProvider.getClass.getName ))
#     serviceProvider.describeWPSProcess( name, runArgs )
#   }
#
#   def getCapabilities(service: str, identifier: str, runArgs: Dict[str,str]): xml.Elem = {
#     edasOpManager
#   }
#
#
# //  def getResultFilePath( service: str, resultId: str, executor: WorkflowExecutor ): Option[str] = {
# //    val serviceProvider = apiManager.getServiceProvider(service)
# //    val path = serviceProvider.getResultFilePath( resultId, executor )
# //    logger.info( "EDAS ProcessManager-> getResultFile: " + resultId + ", path = " + path.getOrElse("NULL") )
# //    path
# //  }
#
#   def hasResult( service: str, resultId: str ): bool = { false }
#
#   def getResult( service: str, resultId: str, response_syntax: wps.ResponseSyntax.Value ): Element = {
#     logger.info( "EDAS ProcessManager-> getResult: " + resultId)
#     val serviceProvider = apiManager.getServiceProvider(service)
#     serviceProvider.getResult( resultId, response_syntax )
#   }
#
#   def getResultVariable( service: str, resultId: str ): Option[RDDTransientVariable] = {
#     logger.info( "EDAS ProcessManager-> getResult: " + resultId)
#     val serviceProvider = apiManager.getServiceProvider(service)
#     serviceProvider.getResultVariable(resultId)
#   }
#
#   def getResultVariables( service: str ): Iterable[str] = {
#     val serviceProvider = apiManager.getServiceProvider(service)
#     serviceProvider.getResultVariables
#   }
#
#   def getResultStatus( service: str, resultId: str, response_syntax: wps.ResponseSyntax.Value ): Element = {
#     logger.info( "EDAS ProcessManager-> getResult: " + resultId)
#     val serviceProvider = apiManager.getServiceProvider(service)
#     serviceProvider.getResultStatus(resultId,response_syntax)
#   }
# }

