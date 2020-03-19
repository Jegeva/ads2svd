################################################################################
#
# Copyright (C) 2014,2017 Arm Limited (or its affiliates). All rights reserved.
#
# Quadros RTXC
#
#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

from osapi import *
from utils import *

class Queuentries( Table ):

    def __init__( self ):

        cid = "queue"

        fields = [ createPrimaryField( cid, "id", DECIMAL ) ]

        fields.append( createField( cid, "name", TEXT ) )
        fields.append( createField( cid, "entries", DECIMAL ) )
        fields.append( createField( cid, "addr", TEXT ) )

        Table.__init__( self, cid, fields )

    def readQueue( self, pqh, i, debugSession ):

        pqhMembers = pqh.dereferencePointer( ).getStructureMembers( )

        name = GetObjectName( QUEUE_KCLASS, i, debugSession )

        cells = [ createNumberCell( i ) ]

        cells.append( createTextCell( name ) )

        entries = pqhMembers[ "curndx" ].readAsNumber( )
        cells.append( createNumberCell( entries ) )

        addresses = "None"

        next = pqhMembers[ "base" ]

        width = pqhMembers[ "width" ].readAsNumber( )

        for i in range( entries ):

            val = next.readAsNumber( )

            if addresses == "None":
                addresses = longToHex( val )
            else:
                addresses = addresses + ", " + longToHex( val )

            next = debugSession.evaluateExpression( "(unsigned char*)" + str( val ) + " + " + str( width ) )

        cells.append( createTextCell( addresses ) )

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
