################################################################################
#
# Copyright (C) 2014,2017 Arm Limited (or its affiliates). All rights reserved.
#
# Quadros RTXC
#
#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

from osapi import *
from utils import *

class Mutexes( Table ):

    def __init__( self ):

        cid = "mutexes"

        fields = [ createPrimaryField( cid, "id", DECIMAL ) ]

        fields.append( createField( cid, "name", TEXT ) )
        fields.append( createField( cid, "owner", TEXT ) )
        fields.append( createField( cid, "level", TEXT ) )
        fields.append( createField( cid, "conflicts", TEXT ) )
        fields.append( createField( cid, "order", TEXT ) )
        fields.append( createField( cid, "inversion", TEXT ) )
        fields.append( createField( cid, "waiters", TEXT ) )

        Table.__init__( self, cid, fields )

    def readMutex( self, puh, i, debugSession ):

        puhMembers = puh.dereferencePointer( ).getStructureMembers( )

        name = GetObjectName( MUTX_KCLASS, i, debugSession )

        cells = [ createNumberCell( i ) ]

        cells.append( createTextCell( name ) )

        owner = puhMembers[ "owner" ]
        if owner.readAsNumber( ):
            task = owner.dereferencePointer( ).getStructureMembers( )[ "task" ].readAsNumber( )
            cells.append( createTextCell( GetObjectName( TASK_KCLASS, task, debugSession ) ) )
            cells.append( createTextCell( str( puhMembers[ "level" ].readAsNumber( ) ) ) )
        else:
            cells.append( createTextCell( "N/A" ) )
            cells.append( createTextCell( "N/A" ) )

        if checkAttributes( MUTX_KCLASS, ATTR_STATISTICS, debugSession ) and isMember( "usage", puhMembers ):
            cells.append( createTextCell( str( puhMembers[ "usage" ].readAsNumber( ) ) ) )
        else:
            cells.append( createTextCell( "N/A" ) )

        attr = puhMembers[ "attributes" ].readAsNumber( )

        if attr & ATTR_FIFO_ORDER:
            cells.append( createTextCell( "FIFO" ) )
        else:
            cells.append( createTextCell( "Priority" ) )

        if attr & ATTR_INVERSION:
            cells.append( createTextCell( "Yes" ) )
        else:
            cells.append( createTextCell( "No" ) )

        cells.append( createTextCell( getWaiters( puhMembers, debugSession ) ) )

        return self.createRecord( cells )

    def getRecords( self, debugSession ):

        records = [ ]

        pocdt = getocdt( MUTX_KCLASS, debugSession )

        n_statics = getStatics( pocdt, debugSession )
        n_objects = getObjects( pocdt, debugSession )

        for i in range( 1, n_statics + 1 ):
            records.append( self.readMutex( GETPUH( pocdt, debugSession, i ), i, debugSession ) )

        for i in range( n_statics + 1, n_objects + 1 ):
            j = i - n_statics - 1
            if isObjectInuse( pocdt, j, debugSession ):
                records.append( self.readMutex( GETPUH( pocdt, debugSession, i ), i, debugSession ) )

        return records
