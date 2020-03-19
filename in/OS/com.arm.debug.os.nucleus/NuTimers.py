################################################################################
#
# Copyright (C) 2014,2017 Arm Limited (or its affiliates). All rights reserved.
#
#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

from osapi import *
from utils import *

class NuTimers( Table ):

    def __init__( self ):

        cid = "tm"

        fields = [ createPrimaryField( cid, "cb", ADDRESS ) ]

        fields.append( createField( cid, "name", TEXT ) )
        fields.append( createField( cid, "routine", TEXT ) )
        fields.append( createField( cid, "expid", DECIMAL ) )
        fields.append( createField( cid, "enabled", TEXT ) )
        fields.append( createField( cid, "paused", TEXT ) )
        fields.append( createField( cid, "expirations", DECIMAL ) )
        fields.append( createField( cid, "initial", DECIMAL ) )
        fields.append( createField( cid, "reshed", DECIMAL ) )
        fields.append( createField( cid, "pausetm", DECIMAL ) )
        fields.append( createField( cid, "type", TEXT ) )
        fields.append( createField( cid, "remaining", DECIMAL ) )

        Table.__init__( self, cid, fields )

    def readRecord( self, cbPtr, debugSession ):

        cbMembers = cbPtr.dereferencePointer( ).getStructureMembers( )

        cells = [ createAddressCell( cbPtr.readAsAddress( ) ) ]
        cells.append( createTextCell( cbMembers[ "tm_name" ].readAsNullTerminatedString( ) ) )
        cells.append( createTextCell( longToHex( cbMembers[ "tm_expiration_routine" ].readAsNumber( ) ) ) )
        cells.append( createNumberCell( cbMembers[ "tm_expiration_id" ].readAsNumber( ) ) )
        cells.append( createTextCell( getNoYesText( cbMembers[ "tm_enabled" ].readAsNumber( ) ) ) )
        cells.append( createTextCell( getNoYesText( cbMembers[ "tm_paused_status" ].readAsNumber( ) ) ) )
        cells.append( createNumberCell( cbMembers[ "tm_expirations" ].readAsNumber( ) ) )
        cells.append( createNumberCell( cbMembers[ "tm_initial_time" ].readAsNumber( ) ) )
        cells.append( createNumberCell( cbMembers[ "tm_reschedule_time" ].readAsNumber( ) ) )
        cells.append( createNumberCell( cbMembers[ "tm_paused_time" ].readAsNumber( ) ) )

        tbMembers = cbMembers[ "tm_actual_timer" ].getStructureMembers( )
        timerType = tbMembers[ "tm_timer_type" ].readAsNumber( )

        cells.append( createTextCell( getTimerTypeText( timerType ) ) )
        cells.append( createNumberCell( tbMembers[ "tm_remaining_time" ].readAsNumber( ) ) )

        return self.createRecord( cells )

    def getRecords( self, debugSession ):
        semaIter = listIter(debugSession, getFirstTimer, getNextTimer)
        return [self.readRecord(semaPtr, debugSession) for semaPtr in semaIter]
