################################################################################
#
# Copyright (C) 2014,2017 Arm Limited (or its affiliates). All rights reserved.
#
# Quadros RTXC
#
#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

from osapi import *
from utils import *

class Queues( Table ):

    def __init__( self ):

        cid = "queues"

        fields = [ createPrimaryField( cid, "id", DECIMAL ) ]

        fields.append( createField( cid, "name", TEXT ) )
        fields.append( createField( cid, "base", TEXT ) )
        fields.append( createField( cid, "current", DECIMAL ) )
        fields.append( createField( cid, "depth", DECIMAL ) )
        fields.append( createField( cid, "width", DECIMAL ) )
        fields.append( createField( cid, "worst", TEXT ) )
        fields.append( createField( cid, "usage", TEXT ) )
        fields.append( createField( cid, "order", TEXT ) )
        fields.append( createField( cid, "waiters", TEXT ) )

        Table.__init__( self, cid, fields )

    def readQueue( self, pqh, i, debugSession ):

        pqhMembers = pqh.dereferencePointer( ).getStructureMembers( )

        name = GetObjectName( QUEUE_KCLASS, i, debugSession )

        cells = [ createNumberCell( i ) ]

        cells.append( createTextCell( name ) )

        cells.append( createTextCell( longToHex( pqhMembers[ "base" ].readAsNumber( ) ) ) )

        cells.append( createNumberCell( pqhMembers[ "curndx" ].readAsNumber( ) ) )

        cells.append( createNumberCell( pqhMembers[ "depth" ].readAsNumber( ) ) )

        cells.append( createNumberCell( pqhMembers[ "width" ].readAsNumber( ) ) )

        if checkAttributes( QUEUE_KCLASS, ATTR_STATISTICS, debugSession ) and isMember( "worst", pqhMembers ):
            cells.append( createTextCell( str( pqhMembers[ "worst" ].readAsNumber( ) ) ) )
            cells.append( createTextCell( str( pqhMembers[ "usage" ].readAsNumber( ) ) ) )
        else:
            cells.append( createTextCell( "N/A" ) )
            cells.append( createTextCell( "N/A" ) )

        attr = pqhMembers[ "attributes" ].readAsNumber( )

        if attr & ATTR_FIFO_ORDER:
            cells.append( createTextCell( "FIFO" ) )
        else:
            cells.append( createTextCell( "Priority" ) )

        cells.append( createTextCell( getWaiters( pqhMembers, debugSession ) ) )

        return self.createRecord( cells )

    def getRecords( self, debugSession ):

        records = [ ]

        pocdt = getocdt( QUEUE_KCLASS, debugSession )

        n_statics = getStatics( pocdt, debugSession )
        n_objects = getObjects( pocdt, debugSession )

        for i in range( 1, n_statics + 1 ):
            records.append( self.readQueue( GETPQH( pocdt, debugSession, i ), i, debugSession ) )

        for i in range( n_statics + 1, n_objects + 1 ):
            j = i - n_statics - 1
            if isObjectInuse( pocdt, j, debugSession ):
                records.append( self.readQueue( GETPQH( pocdt, debugSession, i ), i, debugSession ) )

        return records
