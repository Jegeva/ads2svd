################################################################################
#
# Copyright (C) 2014,2017 Arm Limited (or its affiliates). All rights reserved.
#
# Quadros RTXC
#
#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

from osapi import *
from utils import *

class Exceptions( Table ):

    def __init__( self ):

        cid = "except"

        fields = [ createPrimaryField( cid, "id", DECIMAL ) ]

        fields.append( createField( cid, "name", TEXT ) )
        fields.append( createField( cid, "vector", DECIMAL ) )
        fields.append( createField( cid, "level", DECIMAL ) )
        fields.append( createField( cid, "handl", TEXT ) )

        Table.__init__( self, cid, fields )

    def readException( self, peh, i, debugSession ):

        pehMembers = peh.dereferencePointer( ).getStructureMembers( )

        name = GetObjectName( EXCPTN_KCLASS, i, debugSession )

        cells = [ createNumberCell( i ) ]

        cells.append( createTextCell( name ) )

        cells.append( createNumberCell( pehMembers[ "vector" ].readAsNumber( ) ) )

        cells.append( createNumberCell( pehMembers[ "level" ].readAsNumber( ) ) )

        cells.append( createTextCell( longToHex( pehMembers[ "old_handler" ].readAsNumber( ) ) ) )

        return self.createRecord( cells )

    def getRecords( self, debugSession ):

        records = [ ]

        pocdt = getocdt( EXCPTN_KCLASS, debugSession )

        n_statics = getStatics( pocdt, debugSession )
        n_objects = getObjects( pocdt, debugSession )

        for i in range( 1, n_statics + 1 ):
            records.append( self.readException( GETPEH( pocdt, debugSession, i ), i, debugSession ) )

        for i in range( n_statics + 1, n_objects + 1 ):
            j = i - n_statics - 1
            if isObjectInuse( pocdt, j, debugSession ):
                records.append( self.readException( GETPEH( pocdt, debugSession, i ), i, debugSession ) )

        return records
