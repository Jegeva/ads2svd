################################################################################
#
# Copyright (C) 2014,2017 Arm Limited (or its affiliates). All rights reserved.
#
#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

from osapi import *
from utils import *

class NuEventGroups( Table ):

    def __init__( self ):

        cid = "eg"

        fields = [ createPrimaryField( cid, "cb", ADDRESS ) ]

        fields.append( createField( cid, "name", TEXT ) )
        fields.append( createField( cid, "flags", TEXT ) )
        fields.append( createField( cid, "tasks", DECIMAL ) )

        Table.__init__( self, cid, fields )

    def readRecord( self, cbPtr, debugSession ):

        cbMembers = cbPtr.dereferencePointer( ).getStructureMembers( )

        cells = [ createAddressCell( cbPtr.readAsAddress( ) ) ]
        cells.append( createTextCell( cbMembers[ "ev_name" ].readAsNullTerminatedString( ) ) )
        cells.append( createTextCell( longToHex( cbMembers[ "ev_current_events" ].readAsNumber( ) ) ) )
        cells.append( createNumberCell( cbMembers[ "ev_tasks_waiting" ].readAsNumber( ) ) )

        return self.createRecord( cells )


    def getRecords( self, debugSession ):
        cbIter = listIter(debugSession, getFirstEventGroup, getNextEventGroup)
        return [self.readRecord(cbPtr, debugSession) for cbPtr in cbIter]



