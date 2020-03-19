################################################################################
#
# Copyright (C) 2014,2017 Arm Limited (or its affiliates). All rights reserved.
#
# Quadros RTXC
#
#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

from osapi import *
from utils import *

class Partitionentries( Table ):

    def __init__( self ):

        cid = "parte"

        fields = [ createPrimaryField( cid, "id", DECIMAL ) ]

        fields.append( createField( cid, "name", TEXT ) )
        fields.append( createField( cid, "avail", DECIMAL ) )
        fields.append( createField( cid, "addr", TEXT ) )

        Table.__init__( self, cid, fields )

    def readPartitionEntries( self, pph, i, debugSession ):

        pphMembers = pph.dereferencePointer( ).getStructureMembers( )

        name = GetObjectName( PART_KCLASS, i, debugSession )

        cells = [ createNumberCell( i ) ]

        cells.append( createTextCell( name ) )

        cells.append( createNumberCell( pphMembers[ "cur" ].readAsNumber( ) ) )

        addresses = "None"
        next = pphMembers[ "first" ]
        while next.readAsNumber( ):

            val = next.readAsNumber( )

            if addresses == "None":
                addresses = longToHex( val )
            else:
                addresses = addresses + ", " + longToHex( val )

            members = next.dereferencePointer( ).getStructureMembers( )

            next = members[ "next" ]

        cells.append( createTextCell( addresses ) )

        return self.createRecord( cells )

    def getRecords( self, debugSession ):

        records = [ ]

        pocdt = getocdt( PART_KCLASS, debugSession )

        n_statics = getStatics( pocdt, debugSession )
        n_objects = getObjects( pocdt, debugSession )

        for i in range( 1, n_statics + 1 ):
            records.append( self.readPartitionEntries( GETPPH( pocdt, debugSession, i ), i, debugSession ) )

        for i in range( n_statics + 1, n_objects + 1 ):
            j = i - n_statics - 1
            if isObjectInuse( pocdt, j, debugSession ):
                records.append( self.readPartitionEntries( GETPPH( pocdt, debugSession, i ), i, debugSession ) )

        return records
