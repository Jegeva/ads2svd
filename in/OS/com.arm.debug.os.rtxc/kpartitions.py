################################################################################
#
# Copyright (C) 2014,2017 Arm Limited (or its affiliates). All rights reserved.
#
# Quadros RTXC
#
#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

from osapi import *
from utils import *

class Partitions( Table ):

    def __init__( self ):

        cid = "part"

        fields = [ createPrimaryField( cid, "id", DECIMAL ) ]

        fields.append( createField( cid, "name", TEXT ) )
        fields.append( createField( cid, "base", TEXT ) )
        fields.append( createField( cid, "avail", DECIMAL ) )
        fields.append( createField( cid, "total", DECIMAL ) )
        fields.append( createField( cid, "bsize", DECIMAL ) )
        fields.append( createField( cid, "worst", TEXT ) )
        fields.append( createField( cid, "usage", TEXT ) )
        fields.append( createField( cid, "order", TEXT ) )
        fields.append( createField( cid, "waiters", TEXT ) )

        Table.__init__( self, cid, fields )

    def readPartition( self, pph, i, debugSession ):

        pphMembers = pph.dereferencePointer( ).getStructureMembers( )

        name = GetObjectName( PART_KCLASS, i, debugSession )

        cells = [ createNumberCell( i ) ]

        cells.append( createTextCell( name ) )

        cells.append( createTextCell( longToHex( pphMembers[ "base" ].readAsNumber( ) ) ) )

        cells.append( createNumberCell( pphMembers[ "cur" ].readAsNumber( ) ) )

        cells.append( createNumberCell( pphMembers[ "count" ].readAsNumber( ) ) )

        cells.append( createNumberCell( pphMembers[ "size" ].readAsNumber( ) ) )

        if checkAttributes( PART_KCLASS, ATTR_STATISTICS, debugSession ) and isMember( "worst", pphMembers ):
            cells.append( createTextCell( str( pphMembers[ "worst" ].readAsNumber( ) ) ) )
            cells.append( createTextCell( str( pphMembers[ "usage" ].readAsNumber( ) ) ) )
        else:
            cells.append( createTextCell( "N/A" ) )
            cells.append( createTextCell( "N/A" ) )

        attr = pphMembers[ "attributes" ].readAsNumber( )

        if attr & ATTR_FIFO_ORDER:
            cells.append( createTextCell( "FIFO" ) )
        else:
            cells.append( createTextCell( "Priority" ) )

        cells.append( createTextCell( getWaiters( pphMembers, debugSession ) ) )

        return self.createRecord( cells )

    def getRecords( self, debugSession ):

        records = [ ]

        pocdt = getocdt( PART_KCLASS, debugSession )

        n_statics = getStatics( pocdt, debugSession )
        n_objects = getObjects( pocdt, debugSession )

        for i in range( 1, n_statics + 1 ):
            records.append( self.readPartition( GETPPH( pocdt, debugSession, i ), i, debugSession ) )

        for i in range( n_statics + 1, n_objects + 1 ):
            j = i - n_statics - 1
            if isObjectInuse( pocdt, j, debugSession ):
                records.append( self.readPartition( GETPPH( pocdt, debugSession, i ), i, debugSession ) )

        return records
