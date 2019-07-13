from typing import Dict, Any, Union, List, Callable, Optional, Iterable
import zmq, traceback, time, itertools, queue
from edas.process.task import Job
from edas.process.manager import SubmissionThread
from edas.workflow.data import EDASDataset
from stratus_endpoint.handler.base import Status, TaskHandle, TaskResult
from edas.util.logging import EDASLogger
import xarray as xa

class TaskExecHandler(TaskHandle):

    def __init__( self, cid: str, _job: Job, **kwargs ):
        super(TaskExecHandler, self).__init__(**{"rid": _job.requestId, "cid": cid, **kwargs})
        self.logger = EDASLogger.getLogger()
        self.sthread = None
        self._processResults = True
        self.results = queue.Queue()
        self.job = _job
        self._status = Status.IDLE
        self._exception = None
        self.start_time = time.time()

    def execJob(self, job: Job ) -> SubmissionThread:
        self._status = Status.EXECUTING
        self.sthread = SubmissionThread( job, self.processResult, self.processFailure )
        self.sthread.start()
        self.logger.info( " ----------------->>> Submitted request for job " + job.requestId )
        return self.sthread

    def status(self):
        return self._status

    def exception(self) -> Exception:
        return self._exception

    def getResult(self, timeout=None, block=False) ->  Optional[TaskResult]:
        edasResults: List[EDASDataset] = self.results.get( block, timeout )
        for edasResult in edasResults:
            if edasResult.getResultClass() ==   "METADATA":
                return TaskResult( edasResult.attrs, [] )
        xaResults: Iterable[xa.Dataset] = itertools.chain.from_iterable( [ edasResult.xr for edasResult in edasResults ] )
        return TaskResult( self._parms, list(xaResults) )

    def processResult( self, result: EDASDataset ):
        self.results.put( result )
        self._status = Status.COMPLETED
        self.logger.info(" ----------------->>> STRATUS REQUEST COMPLETED "  )

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
        self.logger.error( error_message )
        self._status = Status.ERROR
        self._exception = Exception( error_message )
        self._parms["type"] = "error"
        self._parms["mesage"] = error_message
