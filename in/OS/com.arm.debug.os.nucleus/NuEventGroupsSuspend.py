################################################################################
#
# Copyright (C) 2014,2017 Arm Limited (or its affiliates). All rights reserved.
#
#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

from osapi import *
from utils import *

class NuEventGroupsSuspend( Table ):

    def __init__( self ):

        cid = "egs"

        fields = [ createPrimaryField( cid, "cb", ADDRESS ) ]

        fields.append( createField( cid, "name", TEXT ) )
        fields.append( createField( cid, "task", TEXT ) )
        fields.append( createField( cid, "events", TEXT ) )
        fields.append( createField( cid, "oper", TEXT ) )

        Table.__init__( self, cid, fields )

    def readRecord( self, cbPtr, records, debugSession ):

        cbMembers = cbPtr.dereferencePointer( ).getStructureMembers( )

        cbName = cbMembers[ "ev_name" ].readAsNullTerminatedString( )

        sbAddr = cbMembers[ "ev_suspension_list" ].readAsNumber( )
        firstPtr = nextPtr = debugSession.evaluateExpression( "(" + "EV_SUSPEND" + "*)(" + hex( sbAddr ) + ")" )

        while nextPtr.readAsNumber( ):

            sbMembers = nextPtr.dereferencePointer( ).getStructureMembers( )

            tcbPtr = sbMembers[ "ev_suspended_task" ]
            tcbMembers = tcbPtr.dereferencePointer( ).getStructureMembers( )
            taskName = tcbMembers[ "tc_name" ].readAsNullTerminatedString( )

            cells = [ createAddressCell( nextPtr.readAsAddress( ) ) ]
            cells.append( createTextCell( cbName ) )
            cells.append( createTextCell( taskName ) )
            cells.append( createTextCell( longToHex( sbMembers[ "ev_requested_events" ].readAsNumber( ) ) ) )
            cells.append( createTextCell( getEvOperText( sbMembers[ "ev_operation" ].readAsNumber( ) ) ) )

            records.append( self.createRecord( cells ) )

            nextPtr = getNextEvgrpsus( nextPtr, debugSession )

            if( nextPtr.readAsNumber( ) == firstPtr.readAsNumber( ) ):
                break

    def getRecords( self, debugSession ):
        result = []
        cbIter = listIter(debugSession, getFirstEventGroup, getNextEventGroup)
        for cbPtr in cbIter:
            self.readRecord(cbPtr, result, debugSession)
        return result

