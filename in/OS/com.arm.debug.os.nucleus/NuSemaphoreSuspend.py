################################################################################
#
# Copyright (C) 2014,2017 Arm Limited (or its affiliates). All rights reserved.
#
#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

from osapi import *
from utils import *

class NuSemaphoreSuspend( Table ):

    def __init__( self ):

        cid = "sms"

        fields = [ createPrimaryField( cid, "cb", ADDRESS ) ]

        fields.append( createField( cid, "name", TEXT ) )
        fields.append( createField( cid, "task", TEXT ) )

        Table.__init__( self, cid, fields )

    def readRecord( self, cbPtr, records, debugSession ):

        cbMembers = cbPtr.dereferencePointer( ).getStructureMembers( )

        cbName = cbMembers[ "sm_name" ].readAsNullTerminatedString( )

        sbAddr = cbMembers[ "sm_suspension_list" ].readAsNumber( )
        firstPtr = nextPtr = debugSession.evaluateExpression( "(" + "SM_SUSPEND" + "*)(" + hex( sbAddr ) + ")" )

        while nextPtr.readAsNumber( ):

            sbMembers = nextPtr.dereferencePointer( ).getStructureMembers( )

            tcbPtr = sbMembers[ "sm_suspended_task" ]
            tcbMembers = tcbPtr.dereferencePointer( ).getStructureMembers( )
            taskName = tcbMembers[ "tc_name" ].readAsNullTerminatedString( )

            cells = [ createAddressCell( nextPtr.readAsAddress( ) ) ]
            cells.append( createTextCell( cbName ) )
            cells.append( createTextCell( taskName ) )

            records.append( self.createRecord( cells ) )

            nextPtr = getNextSemasus( nextPtr, debugSession )

            if( nextPtr.readAsNumber( ) == firstPtr.readAsNumber( ) ):
                break

    def getRecords( self, debugSession ):
        result = []
        cbIter = listIter(debugSession, getFirstSemaphore, getNextSemaphore)
        for cbPtr in cbIter:
            self.readRecord(cbPtr, result, debugSession)
        return result
