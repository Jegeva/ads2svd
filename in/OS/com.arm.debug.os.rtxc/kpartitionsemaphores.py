################################################################################
#
# Copyright (C) 2014,2017 Arm Limited (or its affiliates). All rights reserved.
#
# Quadros RTXC
#
#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

from osapi import *
from utils import *

class Partitionsemaphores( Table ):

    def __init__( self ):

        cid = "partsema4"

        fields = [ createPrimaryField( cid, "id", DECIMAL ) ]

        fields.append( createField( cid, "name", TEXT ) )
        fields.append( createField( cid, "semaphore", TEXT ) )

        Table.__init__( self, cid, fields )

    def readPartition( self, pph, i, debugSession ):

        pphMembers = pph.dereferencePointer( ).getStructureMembers( )

        name = GetObjectName( PART_KCLASS, i, debugSession )

        cells = [ createNumberCell( i ) ]

        cells.append( createTextCell( name ) )

        name = "N/A"
        if checkAttributes( PART_KCLASS, ATTR_SEMAPHORES, debugSession ) and isMember( "nesema", pphMembers ):
            nesema = pphMembers[ "nesema" ].readAsNumber( )
            if nesema > 0:
                name = GetObjectName( SEMA_KCLASS, nesema, debugSession )

        cells.append( createTextCell( name ) )

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
