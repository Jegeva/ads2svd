################################################################################
#
# Copyright (C) 2014,2017 Arm Limited (or its affiliates). All rights reserved.
#
# Quadros RTXC
#
#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

from osapi import *
from utils import *

class Semaphores( Table ):

    def __init__( self ):

        cid = "semaphores"

        fields = [ createPrimaryField( cid, "id", DECIMAL ) ]

        fields.append( createField( cid, "name", TEXT ) )
        fields.append( createField( cid, "count", DECIMAL ) )
        fields.append( createField( cid, "usage", TEXT ) )
        fields.append( createField( cid, "signal", TEXT ) )
        fields.append( createField( cid, "order", TEXT ) )
        fields.append( createField( cid, "waiters", TEXT ) )

        Table.__init__( self, cid, fields )

    def readSemaphore( self, psh, i, debugSession ):

        pshMembers = psh.dereferencePointer( ).getStructureMembers( )

        semaName = GetObjectName( SEMA_KCLASS, i, debugSession )

        cells = [ createNumberCell( i ) ]

        cells.append( createTextCell( semaName ) )
        cells.append( createNumberCell( pshMembers[ "semacount" ].readAsNumber( ) ) )

        if checkAttributes( SEMA_KCLASS, ATTR_STATISTICS, debugSession ) and isMember( "usage", pshMembers ):
            cells.append( createTextCell( str( pshMembers[ "usage" ].readAsNumber( ) ) ) )
        else:
            cells.append( createTextCell( "N/A" ) )

        attr = pshMembers[ "attributes" ].readAsNumber( )

        if attr & ATTR_MULTIPLE_WAITERS:
            cells.append( createTextCell( "Gang" ) )
        else:
            cells.append( createTextCell( "Single" ) )

        if attr & ATTR_FIFO_ORDER:
            cells.append( createTextCell( "FIFO" ) )
        else:
            cells.append( createTextCell( "Priority" ) )

        tasksWaiting = getWaiters( pshMembers, debugSession )

        cells.append( createTextCell( tasksWaiting ) )

        return self.createRecord( cells )

    def getRecords( self, debugSession ):

        records = [ ]

        pocdt = getocdt( SEMA_KCLASS, debugSession )

        n_statics = getStatics( pocdt, debugSession )
        n_objects = getObjects( pocdt, debugSession )

        for i in range( 1, n_statics + 1 ):
            records.append( self.readSemaphore( GETPSH( pocdt, debugSession, i ), i, debugSession ) )

        for i in range( n_statics + 1, n_objects + 1 ):
            j = i - n_statics - 1
            if isObjectInuse( pocdt, j, debugSession ):
                records.append( self.readSemaphore( GETPSH( pocdt, debugSession, i ), i, debugSession ) )

        return records
