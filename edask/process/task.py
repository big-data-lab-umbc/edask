from typing import Dict, Any, Union, Sequence, List
import zmq, traceback, time, logging, xml, random, string, defusedxml, abc

class UID:
    ndigits = 6

    @staticmethod
    def randomId( length: int ) -> str:
        sample = string.ascii_lowercase+string.digits+string.ascii_uppercase
        return ''.join(random.choice(sample) for i in range(length))

    def __init__(self, uid = randomId(ndigits) ):
        self.uid = uid

    def __add__(self, other: str ):
        return other if other.endswith(self.uid) else other + "-" + self.uid

    def __str__(self): return self.uid

class TaskRequest:
    
  @classmethod
  def new( cls, rId: str, process_name: str, datainputs: Dict[str, Sequence[Dict[str, Any]]]):
    logger = logging.getLogger()
    logger.info( "TaskRequest--> process_name: %s, datainputs: %s".format(process_name, datainputs.toString))
    uid = UID(rId)
    op_spec_list: Sequence[Dict[str, Any]] = datainputs .get( "operation", [] )
    data_list: List[DataContainer] = datainputs.get("variable", []).flatMap(DataContainer.factory(uid, _, op_spec_list.isEmpty )).toList
    domain_list: List[DomainContainer] = datainputs.get("domain", []).map(DomainContainer(_)).toList
    opSpecs: Sequence[Dict[str, Any]] = if(op_spec_list.isEmpty) { getEmptyOpSpecs(data_list) } else { op_spec_list }
    operation_map: Dict[str,OperationContext] = Dict( opSpecs.map (  op => OperationContext( uid, process_name, data_list.map(_.uid), op) ) map ( opc => opc.identifier -> opc ) :_* )
    operation_list: Sequence[OperationContext] = operation_map.values.toSeq
    variableMap: Dict[str, DataContainer] = buildVarMap(data_list, operation_list)
    domainMap: Dict[str, DomainContainer] = buildDomainMap(domain_list)
    inferDomains(operation_list, variableMap )
    gridId = datainputs.get("grid", data_list.headOption.map(dc => dc.uid).get("#META")).toString
    gridSpec = Dict("id" -> gridId.toString)
    rv = TaskRequest( uid, process_name, variableMap, domainMap, operation_list, gridSpec )
    logger.info( " -> Generated TaskRequest, uid = " + uid.toString )
    return rv

  
  
  def __init__( self, id: UID, name: str, variableMap: Dict[str, DataContainer], domainMap: Dict[str, DomainContainer],
                   operations: Sequence[OperationContext] = [], metadata: Dict[str, str] = Dict("id" -> "#META"), user: User = User());
        