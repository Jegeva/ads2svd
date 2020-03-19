################################################################################
#
# Copyright (C) 2014,2017 Arm Limited (or its affiliates). All rights reserved.
#
#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

from osapi import *
from utils import *

class NuTaskCtrl( Table ):

    def __init__( self ):

        cid = "tsc"

        fields = [ createPrimaryField( cid, "cb", ADDRESS ) ]
        fields.append( createField( cid, "name", TEXT ) )
        fields.append( createField( cid, "entry", TEXT ) )
        fields.append( createField( cid, "argc", DECIMAL ) )
        fields.append( createField( cid, "argv", TEXT ) )
        fields.append( createField( cid, "ptcb", TEXT ) )
        fields.append( createField( cid, "ntcb", TEXT ) )
        fields.append( createField( cid, "priogrp", TEXT ) )
        fields.append( createField( cid, "priohead", TEXT ) )
        fields.append( createField( cid, "priosubgrp", TEXT ) )
        fields.append( createField( cid, "priosubmask", TEXT ) )
        fields.append( createField( cid, "pstate", TEXT ) )
        fields.append( createField( cid, "autoclean", TEXT ) )
        fields.append( createField( cid, "cleanfunc", TEXT ) )

        Table.__init__( self, cid, fields )

    def readRecord( self, cbPtr, debugSession ):

        cbMembers = cbPtr.dereferencePointer( ).getStructureMembers( )

        cells = [ createAddressCell( cbPtr.readAsAddress( ) ) ]
        cells.append( createTextCell( cbMembers[ "tc_name" ].readAsNullTerminatedString( ) ) )
        cells.append( createTextCell( longToHex( cbMembers[ "tc_entry" ].readAsNumber( ) ) ) )
        cells.append( createNumberCell( cbMembers[ "tc_argc" ].readAsNumber( ) ) )
        cells.append( createTextCell( longToHex( cbMembers[ "tc_argv" ].readAsNumber( ) ) ) )
        cells.append( createTextCell( longToHex( cbMembers[ "tc_ready_previous" ].readAsNumber( ) ) ) )
        cells.append( createTextCell( longToHex( cbMembers[ "tc_ready_next" ].readAsNumber( ) ) ) )
        if "tc_priority_group" in cbMembers:
            cells.append( createTextCell( longToHex( cbMembers[ "tc_priority_group" ].readAsNumber( ) ) ) )
        else:
            cells.append( createTextCell( longToHex( cbMembers[ "tc_primary_priority" ].readAsNumber( ) ) ) )
        cells.append( createTextCell( longToHex( cbMembers[ "tc_priority_head" ].readAsNumber( ) ) ) )
        cells.append( createTextCell( longToHex( cbMembers[ "tc_sub_priority_ptr" ].readAsNumber( ) ) ) )
        cells.append( createTextCell( longToHex( cbMembers[ "tc_sub_priority" ].readAsNumber( ) ) ) )
        cells.append( createTextCell( getTaskStatusText( cbMembers[ "tc_status" ].readAsNumber( ) ) ) )
        cells.append( createTextCell( getNoYesText( cbMembers[ "tc_auto_clean" ].readAsNumber( ) ) ) )
        cells.append( createTextCell( longToHex( cbMembers[ "tc_cleanup" ].readAsNumber( ) ) ) )

        return self.createRecord( cells )

    def getRecords( self, debugSession ):
        semaIter = listIter(debugSession, getFirstTask, getNextTask)
        return [self.readRecord(semaPtr, debugSession) for semaPtr in semaIter]


