################################################################################
#
# Copyright (C) 2014,2017 Arm Limited (or its affiliates). All rights reserved.
#
#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

from osapi import *
from utils import *

class NuTasks( Table ):

    def __init__( self ):

        cid = "ts"

        fields = [ createPrimaryField( cid, "cb", ADDRESS ) ]

        fields.append( createField( cid, "name", TEXT ) )
        fields.append( createField( cid, "state", TEXT ) )
        fields.append( createField( cid, "delayed", TEXT ) )
        fields.append( createField( cid, "priority", TEXT ) )
        fields.append( createField( cid, "preemption", TEXT ) )
        fields.append( createField( cid, "interrupted", TEXT ) )
        fields.append( createField( cid, "runcount", DECIMAL ) )
        fields.append( createField( cid, "timeslice", TEXT ) )
        fields.append( createField( cid, "timeractive", TEXT ) )
        fields.append( createField( cid, "sigact", TEXT ) )
        fields.append( createField( cid, "signals", DECIMAL ) )
        fields.append( createField( cid, "sigenabled", TEXT ) )
        fields.append( createField( cid, "sighandl", TEXT ) )
        fields.append( createField( cid, "semacount", DECIMAL ) )

        Table.__init__( self, cid, fields )

    def readRecord( self, cbPtr, debugSession ):

        cbMembers = cbPtr.dereferencePointer( ).getStructureMembers( )

        cells = [ createAddressCell( cbPtr.readAsAddress( ) ) ]
        cells.append( createTextCell( cbMembers[ "tc_name" ].readAsNullTerminatedString( ) ) )
        cells.append( createTextCell( getTaskStatusText( cbMembers[ "tc_status" ].readAsNumber( ) ) ) )
        cells.append( createTextCell( getNoYesText( cbMembers[ "tc_delayed_suspend" ].readAsNumber( ) ) ) )
        cells.append( createTextCell( str( cbMembers[ "tc_priority" ].readAsNumber( ) ) + "/" + str( cbMembers[ "tc_base_priority" ].readAsNumber( ) ) ) )
        cells.append( createTextCell( getNoYesText( cbMembers[ "tc_preemption" ].readAsNumber( ) ) ) )
        cells.append( createTextCell( getNoYesText( isTaskInterruptFrame( cbMembers, debugSession ) ) ) )
        cells.append( createNumberCell( cbMembers[ "tc_scheduled" ].readAsNumber( ) ) )
        cells.append( createTextCell( str( cbMembers[ "tc_cur_time_slice" ].readAsNumber( ) ) + "/" + str( cbMembers[ "tc_time_slice" ].readAsNumber( ) ) ) )
        cells.append( createTextCell( getNoYesText( cbMembers[ "tc_timer_active" ].readAsNumber( ) ) ) )
        cells.append( createTextCell( getNoYesText( cbMembers[ "tc_signal_active" ].readAsNumber( ) ) ) )
        cells.append( createNumberCell( cbMembers[ "tc_signals" ].readAsNumber( ) ) )
        cells.append( createTextCell( getNoYesText( cbMembers[ "tc_enabled_signals" ].readAsNumber( ) ) ) )
        cells.append( createTextCell( longToHex( cbMembers[ "tc_signal_handler" ].readAsNumber( ) ) ) )
        cells.append( createNumberCell( cbMembers[ "tc_semaphore_count" ].readAsNumber( ) ) )

        return self.createRecord( cells )

    def getRecords( self, debugSession ):
        taskIter = listIter(debugSession, getFirstTask, getNextTask)
        return [self.readRecord(taskPtr, debugSession) for taskPtr in taskIter]
