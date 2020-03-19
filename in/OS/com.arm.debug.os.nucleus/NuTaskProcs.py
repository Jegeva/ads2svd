################################################################################
#
# Copyright (C) 2014,2017 Arm Limited (or its affiliates). All rights reserved.
#
#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

from osapi import *
from utils import *

class NuTaskProcs( Table ):

    def __init__( self ):

        cid = "tsp"

        fields = [ createPrimaryField( cid, "cb", ADDRESS ) ]
        fields.append( createField( cid, "name", TEXT ) )
        fields.append( createField( cid, "process", TEXT ) )
        fields.append( createField( cid, "retaddr", TEXT ) )
        fields.append( createField( cid, "pretaddr", TEXT ) )
        fields.append( createField( cid, "savedsp", TEXT ) )

        Table.__init__( self, cid, fields )

    def readRecord( self, cbPtr, debugSession ):

        cbMembers = cbPtr.dereferencePointer( ).getStructureMembers( )

        cells = [ createAddressCell( cbPtr.readAsAddress( ) ) ]
        cells.append( createTextCell( cbMembers[ "tc_name" ].readAsNullTerminatedString( ) ) )
        cells.append( createTextCell( longToHex( cbMembers[ "tc_process" ].readAsNumber( ) ) ) )
        cells.append( createTextCell( longToHex( cbMembers[ "tc_return_addr" ].readAsNumber( ) ) ) )
        cells.append( createTextCell( longToHex( cbMembers[ "tc_saved_return_addr" ].readAsNumber( ) ) ) )
        cells.append( createTextCell( longToHex( cbMembers[ "tc_saved_stack_ptr" ].readAsNumber( ) ) ) )

        return self.createRecord( cells )

    def getRecords( self, debugSession ):
        semaIter = listIter(debugSession, getFirstTask, getNextTask)
        return [self.readRecord(semaPtr, debugSession) for semaPtr in semaIter]

