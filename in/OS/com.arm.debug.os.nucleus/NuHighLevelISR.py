################################################################################
#
# Copyright (C) 2014,2017 Arm Limited (or its affiliates). All rights reserved.
#
#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

from osapi import *
from utils import *

class NuHighLevelISR( Table ):

    def __init__( self ):

        cid = "hli"

        fields = [ createPrimaryField( cid, "cb", ADDRESS ) ]

        fields.append( createField( cid, "name", TEXT ) )
        fields.append( createField( cid, "priority", DECIMAL ) )
        fields.append( createField( cid, "runcount", DECIMAL ) )
        fields.append( createField( cid, "timeslice", DECIMAL ) )
        fields.append( createField( cid, "process", TEXT ) )
        fields.append( createField( cid, "activations", DECIMAL ) )
        fields.append( createField( cid, "entry", TEXT ) )
        fields.append( createField( cid, "nhcb", TEXT ) )

        Table.__init__( self, cid, fields )

    def readRecord( self, cbPtr, debugSession ):

        cbMembers = cbPtr.dereferencePointer( ).getStructureMembers( )

        cells = [ createAddressCell( cbPtr.readAsAddress( ) ) ]
        cells.append( createTextCell( cbMembers[ "tc_name" ].readAsNullTerminatedString( ) ) )
        cells.append( createNumberCell( cbMembers[ "tc_priority" ].readAsNumber( ) ) )
        cells.append( createNumberCell( cbMembers[ "tc_scheduled" ].readAsNumber( ) ) )
        cells.append( createNumberCell( cbMembers[ "tc_cur_time_slice" ].readAsNumber( ) ) )
        cells.append( createTextCell( longToHex( cbMembers[ "tc_process" ].readAsNumber( ) ) ) )
        cells.append( createNumberCell( cbMembers[ "tc_activation_count" ].readAsNumber( ) ) )
        cells.append( createTextCell( longToHex( cbMembers[ "tc_entry" ].readAsNumber( ) ) ) )
        cells.append( createTextCell( longToHex( cbMembers[ "tc_active_next" ].readAsNumber( ) ) ) )

        return self.createRecord( cells )

    def getRecords( self, debugSession ):
        cbIter = listIter(debugSession, getFirstHisr, getNextHisr)
        return [self.readRecord(cbPtr, debugSession) for cbPtr in cbIter]
