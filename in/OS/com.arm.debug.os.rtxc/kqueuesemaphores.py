################################################################################
#
# Copyright (C) 2014,2017 Arm Limited (or its affiliates). All rights reserved.
#
# Quadros RTXC
#
#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

from osapi import *
from utils import *

class Queuesemaphores( Table ):

    def __init__( self ):

        cid = "queuesema4"

        fields = [ createPrimaryField( cid, "id", DECIMAL ) ]

        fields.append( createField( cid, "name", TEXT ) )
        fields.append( createField( cid, "semaphoreNE", TEXT ) )
        fields.append( createField( cid, "semaphoreNF", TEXT ) )

        Table.__init__( self, cid, fields )

    def readQueue( self, pqh, i, debugSession ):

        pqhMembers = pqh.dereferencePointer( ).getStructureMembers( )

        name = GetObjectName( QUEUE_KCLASS, i, debugSession )

        cells = [ createNumberCell( i ) ]

        cells.append( createTextCell( name ) )

        name = "N/A"
        if checkAttributes( QUEUE_KCLASS, ATTR_SEMAPHORES, debugSession ) and isMember( "nesema", pqhMembers ):
            nesema = pqhMembers[ "nesema" ].readAsNumber( )
            if nesema > 0:
                name = GetObjectName( SEMA_KCLASS, nesema, debugSession )
        cells.append( createTextCell( name ) )

        name = "N/A"
        if checkAttributes( QUEUE_KCLASS, ATTR_SEMAPHORES, debugSession ) and isMember( "nfsema", pqhMembers ):
            nfsema = pqhMembers[ "nfsema" ].readAsNumber( )
            if nfsema > 0:
                name = GetObjectName( SEMA_KCLASS, nfsema, debugSession )
        cells.append( createTextCell( name ) )

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
