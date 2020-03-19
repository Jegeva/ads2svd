################################################################################
#
# Copyright (C) 2014,2017 Arm Limited (or its affiliates). All rights reserved.
#
#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

from osapi import *
from utils import *

class NuPipes( Table ):

    def __init__( self ):

        cid = "pi"

        fields = [ createPrimaryField( cid, "cb", ADDRESS ) ]

        fields.append( createField( cid, "name", TEXT ) )
        fields.append( createField( cid, "fixed", TEXT ) )
        fields.append( createField( cid, "fifo", TEXT ) )
        fields.append( createField( cid, "psize", DECIMAL ) )
        fields.append( createField( cid, "messages", DECIMAL ) )
        fields.append( createField( cid, "msize", DECIMAL ) )
        fields.append( createField( cid, "bytes", DECIMAL ) )
        fields.append( createField( cid, "start", TEXT ) )
        fields.append( createField( cid, "end", TEXT ) )
        fields.append( createField( cid, "rdptr", TEXT ) )
        fields.append( createField( cid, "wrptr", TEXT ) )
        fields.append( createField( cid, "tasks", DECIMAL ) )

        Table.__init__( self, cid, fields )

    def readRecord( self, cbPtr, debugSession ):

        cbMembers = cbPtr.dereferencePointer( ).getStructureMembers( )

        cells = [ createAddressCell( cbPtr.readAsAddress( ) ) ]
        cells.append( createTextCell( cbMembers[ "pi_name" ].readAsNullTerminatedString( ) ) )
        cells.append( createTextCell( getNoYesText( cbMembers[ "pi_fixed_size" ].readAsNumber( ) ) ) )
        cells.append( createTextCell( getNoYesText( cbMembers[ "pi_fifo_suspend" ].readAsNumber( ) ) ) )
        cells.append( createNumberCell( cbMembers[ "pi_pipe_size" ].readAsNumber( ) ) )
        cells.append( createNumberCell( cbMembers[ "pi_messages" ].readAsNumber( ) ) )
        cells.append( createNumberCell( cbMembers[ "pi_message_size" ].readAsNumber( ) ) )
        cells.append( createNumberCell( cbMembers[ "pi_available" ].readAsNumber( ) ) )
        cells.append( createTextCell( longToHex( cbMembers[ "pi_start" ].readAsNumber( ) ) ) )
        cells.append( createTextCell( longToHex( cbMembers[ "pi_end" ].readAsNumber( ) ) ) )
        cells.append( createTextCell( longToHex( cbMembers[ "pi_read" ].readAsNumber( ) ) ) )
        cells.append( createTextCell( longToHex( cbMembers[ "pi_write" ].readAsNumber( ) ) ) )
        cells.append( createNumberCell( cbMembers[ "pi_tasks_waiting" ].readAsNumber( ) ) )

        return self.createRecord( cells )

    def getRecords( self, debugSession ):
        cbIter = listIter(debugSession, getFirstPipe, getNextPipe)
        return [self.readRecord(cbPtr, debugSession) for cbPtr in cbIter]
