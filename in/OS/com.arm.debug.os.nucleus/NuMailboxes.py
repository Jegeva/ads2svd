################################################################################
#
# Copyright (C) 2014,2017 Arm Limited (or its affiliates). All rights reserved.
#
#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

from osapi import *
from utils import *

class NuMailboxes( Table ):

    def __init__( self ):

        cid = "mb"

        fields = [ createPrimaryField( cid, "cb", ADDRESS ) ]

        fields.append( createField( cid, "name", TEXT ) )
        fields.append( createField( cid, "message", TEXT ) )
        fields.append( createField( cid, "fifo", TEXT ) )
        fields.append( createField( cid, "tasks", DECIMAL ) )
        fields.append( createField( cid, "area", TEXT ) )

        Table.__init__( self, cid, fields )

    def readRecord( self, cbPtr, debugSession ):

        cbMembers = cbPtr.dereferencePointer( ).getStructureMembers( )

        name = cbMembers[ "mb_name" ].readAsNullTerminatedString( )

        cells = [ createAddressCell( cbPtr.readAsAddress( ) ) ]
        cells.append( createTextCell( name ) )
        cells.append( createTextCell( getNoYesText( cbMembers[ "mb_message_present" ].readAsNumber( ) ) ) )
        cells.append( createTextCell( getNoYesText( cbMembers[ "mb_fifo_suspend" ].readAsNumber( ) ) ) )
        cells.append( createNumberCell( cbMembers[ "mb_tasks_waiting" ].readAsNumber( ) ) )
        cells.append( createTextCell( longToHex( addressExprsToLong( cbMembers[ "mb_message_area" ] ) ) ) )


        return self.createRecord( cells )

    def getRecords( self, debugSession ):
        if checkMailbox( debugSession ):
            cbIter = listIter(debugSession, getFirstMailbox, getNextMailbox)
            return [self.readRecord(cbPtr, debugSession) for cbPtr in cbIter]
        else:
            return []

