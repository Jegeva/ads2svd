################################################################################
#
# Copyright (C) 2014,2017 Arm Limited (or its affiliates). All rights reserved.
#
# Quadros RTXC
#
#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

from osapi import *
from utils import *

class Mutexsemaphores( Table ):

    def __init__( self ):

        cid = "mutexsema4"

        fields = [ createPrimaryField( cid, "id", DECIMAL ) ]

        fields.append( createField( cid, "name", TEXT ) )
        fields.append( createField( cid, "semaphore", TEXT ) )

        Table.__init__( self, cid, fields )

    def readMutex( self, puh, i, debugSession ):

        puhMembers = puh.dereferencePointer( ).getStructureMembers( )

        name = GetObjectName( MUTX_KCLASS, i, debugSession )

        cells = [ createNumberCell( i ) ]

        cells.append( createTextCell( name ) )

        name = "N/A"
        if checkAttributes( MUTX_KCLASS, ATTR_SEMAPHORES, debugSession ) and isMember( "sema", puhMembers ):
            sema = puhMembers[ "sema" ].readAsNumber( )
            if sema > 0:
                name = GetObjectName( SEMA_KCLASS, sema, debugSession )

        cells.append( createTextCell( name ) )

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
