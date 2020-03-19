################################################################################
#
# Copyright (C) 2014,2017 Arm Limited (or its affiliates). All rights reserved.
#
# Quadros RTXC
#
#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

from osapi import *
from utils import *

class Alarms( Table ):

    def __init__( self ):

        cid = "alarms"

        fields = [ createPrimaryField( cid, "id", DECIMAL ) ]

        fields.append( createField( cid, "name", TEXT ) )
        fields.append( createField( cid, "state", TEXT ) )
        fields.append( createField( cid, "initial", DECIMAL ) )
        fields.append( createField( cid, "recycle", DECIMAL ) )
        fields.append( createField( cid, "remain", DECIMAL ) )
        fields.append( createField( cid, "expsema", TEXT ) )
        fields.append( createField( cid, "abtsema", TEXT ) )
        fields.append( createField( cid, "waiters", TEXT ) )

        Table.__init__( self, cid, fields )

    def readAlarm( self, pach, i, debugSession ):

        pachMembers = pach.dereferencePointer( ).getStructureMembers( )

        name = GetObjectName( ALARM_KCLASS, i, debugSession )

        cells = [ createNumberCell( i ) ]

        cells.append( createTextCell( name ) )

        state = pachMembers[ "state" ].readAsNumber( )
        cells.append( createTextCell( getAlarmStatusText( state ) ) )

        cells.append( createNumberCell( pachMembers[ "initial" ].readAsNumber( ) ) )

        cells.append( createNumberCell( pachMembers[ "recycle" ].readAsNumber( ) ) )

        pcch = pachMembers[ "pcch" ]
        if pcch.readAsNumber( ):
            accumulator = pcch.dereferencePointer( ).getStructureMembers( )[ "accumulator" ].readAsNumber( )
        else:
            accumulator = 0
        expiration = pachMembers[ "expiration" ].readAsNumber( )

        remaining = expiration - accumulator
        cells.append( createNumberCell( remaining ) )

        esema = asema = 0
        if checkAttributes( ALARM_KCLASS, ATTR_SEMAPHORES, debugSession ) and isMember( "esema", pachMembers ):
            esema = pachMembers[ "esema" ].readAsNumber( )
            asema = pachMembers[ "asema" ].readAsNumber( )

        if esema:
            cells.append( createTextCell( GetObjectName( SEMA_KCLASS, esema, debugSession ) ) )
        else:
            cells.append( createTextCell( "N/A" ) )

        if asema:
            cells.append( createTextCell( GetObjectName( SEMA_KCLASS, asema, debugSession ) ) )
        else:
            cells.append( createTextCell( "N/A" ) )

        cells.append( createTextCell( getWaiters( pachMembers, debugSession ) ) )

        return self.createRecord( cells )

    def getRecords( self, debugSession ):

        records = [ ]

        pocdt = getocdt( ALARM_KCLASS, debugSession )

        n_statics = getStatics( pocdt, debugSession )
        n_objects = getObjects( pocdt, debugSession )

        for i in range( 1, n_statics + 1 ):
            records.append( self.readAlarm( GETPACH( pocdt, debugSession, i ), i, debugSession ) )

        for i in range( n_statics + 1, n_objects + 1 ):
            j = i - n_statics - 1
            if isObjectInuse( pocdt, j, debugSession ):
                records.append( self.readAlarm( GETPACH( pocdt, debugSession, i ), i, debugSession ) )

        return records
