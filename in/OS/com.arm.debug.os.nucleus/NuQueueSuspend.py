################################################################################
#
# Copyright (C) 2014,2017 Arm Limited (or its affiliates). All rights reserved.
#
#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

from osapi import *
from utils import *

class NuQueueSuspend( Table ):

    def __init__( self ):

        cid = "qus"

        fields = [ createPrimaryField( cid, "cb", ADDRESS ) ]

        fields.append( createField( cid, "name", TEXT ) )
        fields.append( createField( cid, "urgent", TEXT ) )
        fields.append( createField( cid, "task", TEXT ) )

        Table.__init__( self, cid, fields )

    def addItem( self, list, cbPtr, urgent, records, debugSession ):

        cbMembers = cbPtr.dereferencePointer( ).getStructureMembers( )
        cbName = cbMembers[ "qu_name" ].readAsNullTerminatedString( )

        sbAddr = cbMembers[ list ].readAsNumber( )
        if sbAddr == 0:
            return

        try:
            firstPtr = nextPtr = debugSession.evaluateExpression( "(" + "QU_SUSPEND" + "*)(" + hex( sbAddr ) + ")" )
            susTaskMemberName = "qu_suspended_task"
            susLinkStructName = "QU_SUSPEND"
            susLinkmemberName = "qu_suspend_link"
        except DebugSessionException:
            firstPtr = nextPtr = debugSession.evaluateExpression( "(" + "MS_SUSPEND" + "*)(" + hex( sbAddr ) + ")" )
            susTaskMemberName = "ms_suspended_task"
            susLinkStructName = "MS_SUSPEND"
            susLinkmemberName = "ms_suspend_link"

        while nextPtr.readAsNumber( ):

            sbMembers = nextPtr.dereferencePointer( ).getStructureMembers( )

            tcbPtr = sbMembers[ susTaskMemberName ]
            if tcbPtr.readAsNumber( ):
                tcbMembers = tcbPtr.dereferencePointer( ).getStructureMembers( )
                taskName = tcbMembers[ "tc_name" ].readAsNullTerminatedString( )
            else:
                taskName = "N/A"

            cells = [ createAddressCell( nextPtr.readAsAddress( ) ) ]
            cells.append( createTextCell( cbName ) )
            cells.append( createTextCell( urgent ) )
            cells.append( createTextCell( taskName ) )

            records.append( self.createRecord( cells ) )

            nextPtr = getNextQuesus( nextPtr, susLinkStructName, susLinkmemberName, debugSession )

            if( nextPtr.readAsNumber( ) == firstPtr.readAsNumber( ) ):
                break

    def readRecord( self, cbPtr, records, debugSession ):
        self.addItem( "qu_urgent_list", cbPtr, "YES", records, debugSession )
        self.addItem( "qu_suspension_list", cbPtr, "NO", records, debugSession )

    def getRecords( self, debugSession ):
        result = []
        cbIter = listIter(debugSession, getFirstQueue, getNextQueue)
        for cbPtr in cbIter:
            self.readRecord(cbPtr, result, debugSession)
        return result


