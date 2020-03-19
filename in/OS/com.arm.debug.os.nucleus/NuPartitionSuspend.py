################################################################################
#
# Copyright (C) 2014,2017 Arm Limited (or its affiliates). All rights reserved.
#
#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

from osapi import *
from utils import *

class NuPartitionSuspend( Table ):

    def __init__( self ):

        cid = "pms"

        fields = [ createPrimaryField( cid, "cb", ADDRESS ) ]

        fields.append( createField( cid, "name", TEXT ) )
        fields.append( createField( cid, "task", TEXT ) )

        Table.__init__( self, cid, fields )

    def readRecord( self, cbPtr, records, debugSession ):

        cbMembers = cbPtr.dereferencePointer( ).getStructureMembers( )

        sbAddr = cbMembers[ "pm_suspension_list" ].readAsNumber( )
        firstPtr = nextPtr = debugSession.evaluateExpression( "(" + "PM_SUSPEND" + "*)(" + hex( sbAddr ) + ")" )

        while nextPtr.readAsNumber( ):

            sbMembers = nextPtr.dereferencePointer( ).getStructureMembers( )

            tcbPtr = sbMembers[ "pm_suspended_task" ]
            tcbMembers = tcbPtr.dereferencePointer( ).getStructureMembers( )
            taskName = tcbMembers[ "tc_name" ].readAsNullTerminatedString( )

            cells = [ createAddressCell( nextPtr.readAsAddress( ) ) ]
            cells.append( createTextCell( cbMembers[ "pm_name" ].readAsNullTerminatedString( ) ) )
            cells.append( createTextCell( taskName ) )

            records.append( self.createRecord( cells ) )

            nextPtr = getNextPartitionSus( nextPtr, debugSession )

            if( nextPtr.readAsNumber( ) == firstPtr.readAsNumber( ) ):
                break

    def getRecords( self, debugSession ):
        result = []
        cbIter = listIter(debugSession, getFirstPartition, getNextPartition)
        for cbPtr in cbIter:
            self.readRecord(cbPtr, result, debugSession)
        return result
