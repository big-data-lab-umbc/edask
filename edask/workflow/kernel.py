from abc import ABCMeta, abstractmethod
import logging, cdms2, time, os, itertools, random, string
from edask.messageParser import mParse
from edask.process.task import TaskRequest
from typing import List, Dict, Sequence, BinaryIO, TextIO, ValuesView, Tuple, Set, Any
from edask.process.operation import WorkflowNode, SourceNode, OpNode
import xarray as xr
from .results import KernelSpec, EDASDataset, EDASArray
from edask.process.source import SourceType
from edask.process.source import VariableSource, DataSource
from edask.process.domain import Axis
from edask.agg import Collection

class Kernel:

    __metaclass__ = ABCMeta

    def __init__( self, spec: KernelSpec ):
        self.logger = logging.getLogger()
        self._spec: KernelSpec = spec
        self._id: str  = self._spec.name + "-" + ''.join([ random.choice( string.ascii_letters + string.digits ) for n in range(5) ] )

    def name(self): return self._spec.name

    def getSpec(self) -> KernelSpec: return self._spec
    def getCapabilities(self) -> str: return self._spec.summary
    def describeProcess( self ) -> str: return str(self._spec)

    def getResultDataset(self, request: TaskRequest, node: WorkflowNode, inputs: List[EDASDataset]) -> EDASDataset:
        result = request.getCachedResult( self._id )
        if result is None:
           result = self.buildWorkflow( request, node, inputs )
           request.cacheResult( self._id, result )
        return result

    @abstractmethod
    def buildWorkflow(self, request: TaskRequest, node: WorkflowNode, inputs: List[EDASDataset]) -> EDASDataset: pass

class OpKernel(Kernel):

    def buildWorkflow(self, request: TaskRequest, wnode: WorkflowNode, inputs: List[EDASDataset]) -> EDASDataset:
        op: OpNode = wnode
        self.logger.info("  ~~~~~~~~~~~~~~~~~~~~~~~~~~ Build Workflow, inputs: " + str( [ str(w) for w in op.inputs ] ) + ", op metadata = " + str(op.metadata) + ", axes = " + str(op.axes) )
        result: EDASDataset = EDASDataset.empty()
        inputDataset = self.preprocessInputs( request, op, inputs )
        for variable in inputDataset.getVariables():
            inputArray: EDASArray = self.processVariable( request, op, variable )
            inputArray.name = op.getResultId(variable.name)
            self.logger.info( " Process Input {} -> {}".format( variable.name, inputArray.name ) )
            result.addArray( inputArray, inputDataset.dataset.attrs )
        return result

    @abstractmethod
    def processVariable( self, request: TaskRequest, node: OpNode, inputs: EDASArray ) -> EDASArray: pass

    def preprocessInputs(self, request: TaskRequest, op: OpNode, inputs: List[EDASDataset]) -> EDASDataset:
        alignmentStrategy = op.getParm("align")
        if op.domain is None and alignmentStrategy is None:
            return EDASDataset.merge( inputs )
        else:
            domains: Set[str] = EDASDataset.domains( inputs, op.domset )
            merged_domain: str  = request.intersectDomains( domains )
            result: EDASDataset = EDASDataset.empty()
            kernelInputs = [request.subsetDataset(merged_domain, input) for input in inputs]
            for kernelInput in kernelInputs:
                for variable in kernelInput.getVariables():
                    result.addArray( variable, kernelInput.dataset.attrs )
            return result.align( alignmentStrategy )

class TupOpKernel(Kernel):

    def buildWorkflow(self, request: TaskRequest, wnode: WorkflowNode, inputs: List[EDASDataset]) -> EDASDataset:
        op: OpNode = wnode
        self.logger.info("  ~~~~~~~~~~~~~~~~~~~~~~~~~~ Build Workflow, inputs: " + str( [ str(w) for w in op.inputs ] ) + ", op metadata = " + str(op.metadata) + ", axes = " + str(op.axes) )
        result: EDASDataset = EDASDataset.empty()
        input_vars: List[List[EDASArray]] = [ dset.getVariables() for dset in inputs ]
        matched_inputs: List[EDASArray] = None
        for matched_inputs in zip( *input_vars ):
            inputVars: EDASDataset = self.preprocessInputs(request, op, matched_inputs, inputs[0].dataset.attrs )
            product: EDASDataset = self.processVariables( request, op, inputVars )
            product.name = op.getResultId( inputVars.id )
            result.addResult( product.dataset, { array.name:array.domId for array in matched_inputs } )
        return result

    @abstractmethod
    def processVariables( self, request: TaskRequest, node: OpNode, inputVars: EDASDataset ) -> EDASDataset: pass

    def preprocessInputs(self, request: TaskRequest, op: OpNode, inputs: List[EDASArray], atts: Dict[str,Any] ) -> EDASDataset:
        domains: Set[str] = { op.domain } | EDASArray.domains( inputs )
        merged_domain: str  = request.intersectDomains(  domains.discard( None )  )
        result: EDASDataset = EDASDataset.empty()
        for input in inputs: result.addArray( request.subsetArray( merged_domain, input ), atts  )
        return result.align( op.getParm("align","lowest") )

class InputKernel(Kernel):
    def __init__( self ):
        Kernel.__init__( self, KernelSpec("input", "Data Input","Data input and workflow source node" ) )

    def buildWorkflow(self, request: TaskRequest, node: WorkflowNode, inputs: List[EDASDataset]) -> EDASDataset:
        snode: SourceNode = node
        dataSource: DataSource = snode.varSource.dataSource
        result: EDASDataset = EDASDataset.empty()
        if dataSource.type == SourceType.collection:
            collection = Collection.new( dataSource.address )
            aggs = collection.sortVarsByAgg( snode.varSource.vids )
            for ( aggId, vars ) in aggs.items():
                dset = xr.open_mfdataset( collection.pathList(aggId), autoclose=True, data_vars=vars, parallel=True)
                result.addResult( *self.processDataset( request, dset, snode )  )
        elif dataSource.type == SourceType.file:
            self.logger.info( "Reading data from address: " + dataSource.address )
            dset = xr.open_mfdataset(dataSource.address, autoclose=True, data_vars=snode.varSource.ids(), parallel=True)
            result.addResult( *self.processDataset( request, dset, snode ) )
        elif dataSource.type == SourceType.dap:
            dset = xr.open_dataset( dataSource.address, autoclose=True  )
            result.addResult( *self.processDataset( request, dset, snode ) )
        return result

    def processDataset(self, request: TaskRequest, dset: xr.Dataset, snode: SourceNode ) -> ( xr.Dataset, Dict[str,str] ):
        coordMap = Axis.getDatasetCoordMap( dset )
        idMap: Dict[str,str] = snode.varSource.name2id(coordMap)
        dset.rename( idMap, True )
        roi = snode.domain  #  .rename( idMap )
        return ( request.subset( roi, dset ), { id:snode.domain for id in snode.varSource.ids() } )