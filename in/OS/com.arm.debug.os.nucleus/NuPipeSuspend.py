################################################################################
#
# Copyright (C) 2014,2017 Arm Limited (or its affiliates). All rights reserved.
#
#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

from osapi import *
from utils import *

class NuPipeSuspend( Table ):

    def __init__( self ):

        cid = "pis"

        fields = [ createPrimaryField( cid, "cb", ADDRESS ) ]

        fields.append( createField( cid, "name", TEXT ) )
        fields.append( createField( cid, "urgent", TEXT ) )
        fields.append( createField( cid, "task", TEXT ) )

        Table.__init__( self, cid, fields )

    def addItem( self, list, cbPtr, urgent, records, debugSession ):

        cbMembers = cbPtr.dereferencePointer( ).getStructureMembers( )
        cbName = cbMembers[ "pi_name" ].readAsNullTerminatedString( )

        sbAddr = cbMembers[ list ].readAsNumber( )
        if sbAddr == 0:
            return

        try:
            firstPtr = nextPtr = debugSession.evaluateExpression( "(" + "PI_SUSPEND" + "*)(" + hex( sbAddr ) + ")" )
        except DebugSessionException:
            return

        while nextPtr.readAsNumber( ):

            sbMembers = nextPtr.dereferencePointer( ).getStructureMembers( )

            tcbPtr = sbMembers[ "pi_suspended_task" ]
            tcbMembers = tcbPtr.dereferencePointer( ).getStructureMembers( )
            taskName = tcbMembers[ "tc_name" ].readAsNullTerminatedString( )

            cells = [ createAddressCell( nextPtr.readAsAddress( ) ) ]
            cells.append( createTextCell( cbName ) )
            cells.append( createTextCell( urgent ) )
            cells.append( createTextCell( taskName ) )

            records.append( self.createRecord( cells ) )

            nextPtr = getNextPipesus( nextPtr, debugSession )

            if( nextPtr.readAsNumber( ) == firstPtr.readAsNumber( ) ):
                break

    def readRecord( self, cbPtr, records, debugSession ):

        self.addItem( "pi_urgent_list", cbPtr, "YES", records, debugSession )
        self.addItem( "pi_suspension_list", cbPtr, "NO", records, debugSession )

    def getRecords( self, debugSession ):
        result = []
        cbIter = listIter(debugSession, getFirstPipe, getNextPipe)
        for cbPtr in cbIter:
            self.readRecord(cbPtr, result, debugSession)
        return result




