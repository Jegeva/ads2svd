################################################################################
#
# Copyright (C) 2014,2017 Arm Limited (or its affiliates). All rights reserved.
#
#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

from osapi import *
from utils import *

class NuDynamicMemorySuspend( Table ):

    def __init__( self ):

        cid = "dms"

        fields = [ createPrimaryField( cid, "cb", ADDRESS ) ]

        fields.append( createField( cid, "name", TEXT ) )
        fields.append( createField( cid, "task", TEXT ) )
        fields.append( createField( cid, "size", DECIMAL ) )
        fields.append( createField( cid, "align", DECIMAL ) )

        Table.__init__( self, cid, fields )

    def readRecord( self, cbPtr, records, debugSession ):

        cbMembers = cbPtr.dereferencePointer( ).getStructureMembers( )

        cbName = cbMembers[ "dm_name" ].readAsNullTerminatedString( )

        sbAddr = cbMembers[ "dm_suspension_list" ].readAsNumber( )
        firstPtr = nextPtr = debugSession.evaluateExpression( "(" + "DM_SUSPEND" + "*)(" + hex( sbAddr ) + ")" )

        while nextPtr.readAsNumber( ):

            sbMembers = nextPtr.dereferencePointer( ).getStructureMembers( )

            tcbPtr = sbMembers[ "dm_suspended_task" ]
            tcbMembers = tcbPtr.dereferencePointer( ).getStructureMembers( )
            taskName = tcbMembers[ "tc_name" ].readAsNullTerminatedString( )

            cells = [ createAddressCell( nextPtr.readAsAddress( ) ) ]
            cells.append( createTextCell( cbName ) )
            cells.append( createTextCell( taskName ) )
            cells.append( createNumberCell( sbMembers[ "dm_request_size" ].readAsNumber( ) ) )
            cells.append( createNumberCell( sbMembers[ "dm_alignment" ].readAsNumber( ) ) )

            records.append( self.createRecord( cells ) )

            nextPtr = getNextDynsus( nextPtr, debugSession )

            if( nextPtr.readAsNumber( ) == firstPtr.readAsNumber( ) ):
                break

    def getRecords( self, debugSession ):
        result = []
        cbIter = listIter(debugSession, getFirstDynamic, getNextDynamic)
        for cbPtr in cbIter:
            self.readRecord(cbPtr, result, debugSession)
        return result
