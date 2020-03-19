################################################################################
#
# Copyright (C) 2014,2017 Arm Limited (or its affiliates). All rights reserved.
#
#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

from osapi import *
from utils import *

class NuMailboxSuspend( Table ):

    def __init__( self ):

        cid = "mbs"

        fields = [ createPrimaryField( cid, "cb", ADDRESS ) ]

        fields.append( createField( cid, "name", TEXT ) )
        fields.append( createField( cid, "area", TEXT ) )
        fields.append( createField( cid, "task", TEXT ) )

        Table.__init__( self, cid, fields )

    def readRecord( self, cbPtr, records, debugSession ):

        cbMembers = cbPtr.dereferencePointer( ).getStructureMembers( )

        sbAddr = cbMembers[ "mb_suspension_list" ].readAsNumber( )
        firstPtr = nextPtr = debugSession.evaluateExpression( "(" + "MB_SUSPEND" + "*)(" + hex( sbAddr ) + ")" )

        while nextPtr.readAsNumber( ):

            sbMembers = nextPtr.dereferencePointer( ).getStructureMembers( )

            tcbPtr = sbMembers[ "mb_suspended_task" ]
            if tcbPtr.readAsNumber( ):
                tcbMembers = tcbPtr.dereferencePointer( ).getStructureMembers( )
                taskName = tcbMembers[ "tc_name" ].readAsNullTerminatedString( )
            else:
                taskName = "N/A"

            cells = [ createAddressCell( nextPtr.readAsAddress( ) ) ]
            cells.append( createTextCell( cbMembers[ "mb_name" ].readAsNullTerminatedString( ) ) )
            cells.append( createTextCell( longToHex( sbMembers[ "mb_message_area" ].readAsNumber( ) ) ) )
            cells.append( createTextCell( taskName ) )

            records.append( self.createRecord( cells ) )

            nextPtr = getNextMailboxsus( nextPtr, debugSession )

            if( nextPtr.readAsNumber( ) == firstPtr.readAsNumber( ) ):
                break

    def getRecords( self, debugSession ):
        result = []
        cbIter = listIter(debugSession, getFirstMailbox, getNextMailbox)
        for cbPtr in cbIter:
            self.readRecord(cbPtr, result, debugSession)
        return result


