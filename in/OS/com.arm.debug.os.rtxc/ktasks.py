################################################################################
#
# Copyright (C) 2014,2017 Arm Limited (or its affiliates). All rights reserved.
#
# Quadros RTXC
#
#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

from osapi import *
from utils import *

class Tasks( Table ):

    def __init__( self ):

        cid = "tasks"

        fields = [ createPrimaryField( cid, "id", DECIMAL ) ]

        fields.append( createField( cid, "name", TEXT ) )
        fields.append( createField( cid, "priority", DECIMAL ) )
        fields.append( createField( cid, "entry", TEXT ) )
        fields.append( createField( cid, "args", TEXT ) )
        fields.append( createField( cid, "state", TEXT ) )
        fields.append( createField( cid, "waitinfo", TEXT ) )
        fields.append( createField( cid, "tickslice", TEXT ) )
        fields.append( createField( cid, "vfpmode", TEXT ) )
        fields.append( createField( cid, "vfpregs", TEXT ) )

        Table.__init__( self, cid, fields )

    def readTask( self, tcbPtr, debugSession ):

        tcbMembers = tcbPtr.dereferencePointer( ).getStructureMembers( )

        taskId = tcbMembers[ "task" ].readAsNumber( )
        taskName = GetObjectName( TASK_KCLASS, taskId, debugSession )

        cells = [ createNumberCell( taskId ) ]
        cells.append( createTextCell( taskName ) )
        cells.append( createNumberCell( tcbMembers[ "priority" ].readAsNumber( ) ) )
        cells.append( createTextCell( longToHex( tcbMembers[ "pc_t0" ].readAsNumber( ) ) ) )
        cells.append( createTextCell( longToHex( tcbMembers[ "taskarg" ].readAsNumber( ) ) ) )
        status = tcbMembers[ "status" ].readAsNumber( )
        statusText = getTaskStatusText( status )

        atickoutInfo = ""
        objectsText = getTaskWaitingObjects( status, taskName, tcbMembers, debugSession )
        tickoutInfo = getTickoutInfo( tcbMembers, debugSession )
        if status & ALARM_WAIT:
            pwh = getPWH( tcbMembers, debugSession )
            pwhMembers = pwh.dereferencePointer( ).getStructureMembers( )
            atickoutInfo = getAlarmTickoutInfo( pwhMembers, debugSession )

        infoText = "N/A"

        if tickoutInfo:
            infoText = tickoutInfo

        if atickoutInfo:
            if infoText:
                infoText = infoText + ",(A)" + atickoutInfo
            else:
                infoText = atickoutInfo

        if objectsText:
            if tickoutInfo:
                infoText = infoText + ":" + objectsText
            else:
                infoText = objectsText

        cells.append( createTextCell( statusText ) )
        cells.append( createTextCell( infoText ) )

        if "tslice" in tcbMembers:
            ts = tcbMembers[ "tslice" ].readAsNumber( )
            ns = tcbMembers[ "newslice" ].readAsNumber( )
            cells.append( createTextCell( str( ts ) + "/" + str( ns )) )
        else:
            cells.append( createTextCell( "N/A" ) )

        if "vfpmode" in tcbMembers:
            cells.append( createTextCell( getVfpModeText( tcbMembers[ "vfpmode" ].readAsNumber( ) ) ) )
            cells.append( createTextCell( longToHex( tcbMembers[ "pvfpregs" ].readAsNumber( ) ) ) )
        else:
            cells.append( createTextCell( "N/A" ) )
            cells.append( createTextCell( "N/A" ) )

        return self.createRecord( cells )

    def getRecords( self, debugSession ):

        records = [ ]

        pocdt = getocdt( TASK_KCLASS, debugSession )

        n_statics = getStatics( pocdt, debugSession )
        n_objects = getObjects( pocdt, debugSession )

        for i in range( n_statics + 1 ):
            records.append( self.readTask( GETPTCB( pocdt, debugSession, i ), debugSession ) )

        for i in range( n_statics + 1, n_objects + 1 ):
            j = i - n_statics - 1
            if isObjectInuse( pocdt, j, debugSession ):
                records.append( self.readTask( GETPTCB( pocdt, debugSession, i ), debugSession ) )

        return records
