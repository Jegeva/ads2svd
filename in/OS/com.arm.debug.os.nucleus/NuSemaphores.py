################################################################################
#
# Copyright (C) 2014,2017 Arm Limited (or its affiliates). All rights reserved.
#
#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

from osapi import *
from utils import *

class NuSemaphores( Table ):

    def __init__( self ):

        cid = "sm"

        fields = [ createPrimaryField( cid, "cb", ADDRESS ) ]

        fields.append( createField( cid, "name", TEXT ) )
        fields.append( createField( cid, "count", DECIMAL ) )
        fields.append( createField( cid, "type", TEXT ) )
        fields.append( createField( cid, "killed", TEXT ) )
        fields.append( createField( cid, "owner", TEXT ) )
        fields.append( createField( cid, "tasks", DECIMAL ) )

        Table.__init__( self, cid, fields )

    def readRecord( self, cbPtr, debugSession ):

        cbMembers = cbPtr.dereferencePointer( ).getStructureMembers( )

        cbName = cbMembers[ "sm_name" ].readAsNullTerminatedString( )

        cells = [ createAddressCell( cbPtr.readAsAddress( ) ) ]
        cells.append( createTextCell( cbName ) )
        cells.append( createNumberCell( cbMembers[ "sm_semaphore_count" ].readAsNumber( ) ) )
        cells.append( createTextCell( getServiceText( cbMembers[ "sm_suspend_type" ].readAsNumber( ) ) ) )
        cells.append( createTextCell( getNoYesText( cbMembers[ "sm_owner_killed" ].readAsNumber( ) ) ) )

        tcbPtr = cbMembers[ "sm_semaphore_owner" ]
        if tcbPtr.readAsNumber( ):
            tcbMembers = tcbPtr.dereferencePointer( ).getStructureMembers( )
            cells.append( createTextCell( tcbMembers[ "tc_name" ].readAsNullTerminatedString( ) ) )
        else:
            cells.append( createTextCell( "N/A" ) )

        cells.append( createNumberCell( cbMembers[ "sm_tasks_waiting" ].readAsNumber( ) ) )

        return self.createRecord( cells )

    def getRecords( self, debugSession ):
        semaIter = listIter(debugSession, getFirstSemaphore, getNextSemaphore)
        return [self.readRecord(semaPtr, debugSession) for semaPtr in semaIter]
