import os, datetime
from collections import OrderedDict
import numpy as np
import edask
from netCDF4 import MFDataset, Variable
from typing import List, Dict, Sequence, BinaryIO, TextIO, ValuesView
from edask.process.operation import SourceConnector
from edask.process.source import VID


def parse_dict( dict_spec ):
    result = {}
    for elem in dict_spec.split(","):
        elem_toks = elem.split(":")
        result[ elem_toks[0].strip() ] = elem_toks[1].strip()

class Archive:

    cacheDir = os.environ['EDAS_CACHE_DIR']
    baseDir = os.path.join( cacheDir, "results" )

    @classmethod
    def getProjectPath( cls, project: str ):
        path = os.path.join( Archive.baseDir, project )
        os.makedirs( path, mode=0o777, exist_ok=True )
        return path

    @classmethod
    def getExperimentPath( cls, project: str, experiment: str ):
        projPath = cls.getProjectPath( project )
        return os.path.join( projPath, experiment + ".nc")

    @classmethod
    def getLogDir( cls ):
        path = os.path.join( Archive.baseDir, "logs" )
        os.makedirs( path, mode=0o777, exist_ok=True )
        return path

class Collection:

    cacheDir = os.environ['EDAS_CACHE_DIR']
    baseDir = os.path.join( cacheDir, "collections", "agg" )

    @classmethod
    def new(cls, name: str ):
        spec_file = os.path.join( cls.baseDir, name + ".csv" )
        return Collection(name, spec_file)

    def __init__(self, _name, _spec_file ):
        self.name = _name
        self.spec = _spec_file
        self.aggs = {}
        self.parms = {}
        self._parseSpecFile()

    def _parseSpecFile(self):
        with open( self.spec, "r" ) as file:
            for line in file.readlines():
                if not line: break
                if( line[0] == '#' ):
                    toks = line[1:].split(",")
                    self.parms[toks[0].strip()] = ",".join(toks[1:]).strip()
                else:
                    toks = line.split(",")
                    self.aggs[toks[0].strip()] = ",".join(toks[1:]).strip()

    def getAggId( self, varName: str ) -> str:
        return self.aggs.get( varName )

    def getAggregation( self, aggId: str ):
        agg_file = os.path.join( Collection.baseDir, aggId + ".ag1")
        return Aggregation( self.name, agg_file )

    def getVariable( self, varName ) -> Variable:
        agg =  self.getAggregation( varName )
        return agg.getVariable(varName)

    def fileList(self, aggId: str ) -> List[BinaryIO]:
        agg = self.getAggregation( aggId )
        return agg.fileList()

    def sortVarsByAgg(self, vids: List[VID] ) -> Dict[str,List[str]]:
        bins = {}
        for vid in vids:
            agg_id = self.aggs.get(vid.name)
            bin = bins.setdefault( agg_id, [] )
            bin.append( vid.name )
        return bins

    def pathList(self, aggId: str ) -> List[str]:
        agg = self.getAggregation( aggId )
        return agg.pathList()

# class EVariable:
#
#    def __init__(self, *args ):
#        self.name = args[0].strip()
#        self.long_name = args[1].strip()
#        self.dods_name = args[2].strip()
#        self.description = args[3].strip()
#        self.shape = [ int(sval.strip()) for sval in args[4].split(",") ]
#        self.resolution = parse_dict( args[5] )
#        self.dims = args[6].strip().split(' ')
#        self.units = args[7].strip()

class Axis:

   def __init__(self, *args ):
       self.name = args[0].strip()
       self.long_name = args[1].strip()
       self.type = args[2].strip()
       self.length = int(args[3].strip())
       self.units = args[4].strip()
       self.bounds = [ float(args[5].strip()), float(args[6].strip()) ]

   def getIndexList( self, dset, min_value, max_value ):
        values = dset.variables[self.name][:]
        return np.where((values > min_value) & (values < max_value))

class File:

    def __init__(self, _collection, *args ):
       self.collection = _collection
       self.start_time = float(args[0].strip())
       self.size = int(args[1].strip())
       self.relpath = args[2].strip()
       self.date = datetime.datetime.utcfromtimestamp(self.start_time*60)

    def getPath(self):
        return os.path.join( self.parm("base.path"), self.relpath )

    def parm(self, key ):
        return self.collection.parm( key )

class VarRec:

    @staticmethod
    def new( parms: List[str]):
        metadata = {}
        metadata["shortName"] = parms[0].strip()
        metadata["longName"] = parms[1].strip()
        metadata["dodsName"] = parms[2].strip()
        metadata["description"] = parms[3].strip()
        shape = list( map( lambda x: int(x), parms[4].strip().split(",") ) )
        resolution = { key: float(value) for (key,value) in map( lambda x: x.split(":"), parms[5].strip().split(",") ) }
        dims = parms[6].strip().split(" ")
        units = parms[7].strip()
        return VarRec( parms[0], shape, resolution, dims, units, metadata )

    def __init__(self, name, shape, resolution, dims, units, metadata ):
        self.name = name
        self.shape = shape
        self.resolution = resolution
        self.dims = dims
        self.units = units
        self.metadata = metadata

    def parm(self, key ):
        return self.metadata.get( key )


class Aggregation:

    def __init__(self, _name, _agg_file ):
        self.name = _name
        self.spec = _agg_file
        self.parms = {}
        self.files: Dict[str,BinaryIO] = OrderedDict()
        self.axes = {}
        self.dims = {}
        self.vars = {}
        self._parseAggFile()

    def _parseAggFile(self):
        with open(self.spec, "r") as file:
            for line in file.readlines():
                if not line: break
                if line[1] == ";":
                    type = line[0]
                    value = line[2:].split(";")
                    if type == 'P': self.parms[ value[0].strip() ] = ";".join( value[1:] ).strip()
                    elif type == 'A': self.axes[ value[2].strip() ] = Axis( *value )
                    elif type == 'C': self.dims[ value[0].strip() ] = int( value[1].strip() )
                    elif type == 'V': self.vars[ value[0].strip() ] = VarRec.new( value )
                    elif type == 'F': self.files[ value[0].strip() ] = File( self, *value )

    def parm(self, key ):
        return self.parms.get( key, "" )

    def getAxis( self, atype ):
        return next((x for x in self.axes.values() if x.type == atype), None)

    def fileList(self) -> ValuesView[BinaryIO]:
        return self.files.values()

    def pathList(self)-> List[str]:
        return [ file.getPath() for file in self.files.values() ]

    def getVariable( self, varName: str ) -> Variable:
        ds = self.getDataset()
        return ds.variables[varName]

    def getDataset( self ) -> MFDataset:
        return MFDataset( self.pathList() )