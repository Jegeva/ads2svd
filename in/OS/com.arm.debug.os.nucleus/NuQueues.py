################################################################################
#
# Copyright (C) 2014,2017 Arm Limited (or its affiliates). All rights reserved.
#
#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

from osapi import *
from utils import *

class NuQueues( Table ):

    def __init__( self ):

        cid = "qu"

        fields = [ createPrimaryField( cid, "cb", ADDRESS ) ]

        fields.append( createField( cid, "name", TEXT ) )
        fields.append( createField( cid, "fixed", TEXT ) )
        fields.append( createField( cid, "fifo", TEXT ) )
        fields.append( createField( cid, "qsize", DECIMAL ) )
        fields.append( createField( cid, "messages", DECIMAL ) )
        fields.append( createField( cid, "msize", DECIMAL ) )
        fields.append( createField( cid, "words", DECIMAL ) )
        fields.append( createField( cid, "start", TEXT ) )
        fields.append( createField( cid, "end", TEXT ) )
        fields.append( createField( cid, "rdptr", TEXT ) )
        fields.append( createField( cid, "wrptr", TEXT ) )
        fields.append( createField( cid, "tasks", DECIMAL ) )

        Table.__init__( self, cid, fields )

    def readRecord( self, cbPtr, debugSession ):

        cbMembers = cbPtr.dereferencePointer( ).getStructureMembers( )

        cells = [ createAddressCell( cbPtr.readAsAddress( ) ) ]
        cells.append( createTextCell( cbMembers[ "qu_name" ].readAsNullTerminatedString( ) ) )
        cells.append( createTextCell( getNoYesText( cbMembers[ "qu_fixed_size" ].readAsNumber( ) ) ) )
        cells.append( createTextCell( getNoYesText( cbMembers[ "qu_fifo_suspend" ].readAsNumber( ) ) ) )
        cells.append( createNumberCell( cbMembers[ "qu_queue_size" ].readAsNumber( ) ) )
        cells.append( createNumberCell( cbMembers[ "qu_messages" ].readAsNumber( ) ) )
        cells.append( createNumberCell( cbMembers[ "qu_message_size" ].readAsNumber( ) ) )
        cells.append( createNumberCell( cbMembers[ "qu_available" ].readAsNumber( ) ) )
        cells.append( createTextCell( longToHex( cbMembers[ "qu_start" ].readAsNumber( ) ) ) )
        cells.append( createTextCell( longToHex( cbMembers[ "qu_end" ].readAsNumber( ) ) ) )
        cells.append( createTextCell( longToHex( cbMembers[ "qu_read" ].readAsNumber( ) ) ) )
        cells.append( createTextCell( longToHex( cbMembers[ "qu_write" ].readAsNumber( ) ) ) )
        cells.append( createNumberCell( cbMembers[ "qu_tasks_waiting" ].readAsNumber( ) ) )

        return self.createRecord( cells )

    def getRecords( self, debugSession ):
        cbIter = listIter(debugSession, getFirstQueue, getNextQueue)
        return [self.readRecord(cbPtr, debugSession) for cbPtr in cbIter]
