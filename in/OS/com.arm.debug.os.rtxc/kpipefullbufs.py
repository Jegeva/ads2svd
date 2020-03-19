################################################################################
#
# Copyright (C) 2014,2017 Arm Limited (or its affiliates). All rights reserved.
#
# Quadros RTXC
#
#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

from osapi import *
from utils import *

class Pipefullbufs( Table ):

    def __init__( self ):

        cid = "pipefb"

        fields = [ createPrimaryField( cid, "id", DECIMAL ) ]

        fields.append( createField( cid, "name", TEXT ) )
        fields.append( createField( cid, "addrsz", TEXT ) )

        Table.__init__( self, cid, fields )

    def readPipe( self, ppch, i, debugSession ):

        ppchMembers = ppch.dereferencePointer( ).getStructureMembers( )

        name = GetObjectName( PIPE_KCLASS, i, debugSession )

        cells = [ createNumberCell( i ) ]

        cells.append( createTextCell( name ) )

        fullBufCount = ppchMembers[ "currfull" ].readAsNumber( )

        fullsizes = ppchMembers[ "sizebase" ].readAsNumber( )

        fullbufs = ppchMembers[ "fullbase" ].readAsNumber( )

        addrsz = "N/A"

        for i in range( fullBufCount ):

            addr = debugSession.evaluateExpression( "*((unsigned long *)" + str( fullbufs ) + "+" + str ( i ) + ")" ).readAsNumber( )

            size = debugSession.evaluateExpression( "*((int *)" + str( fullsizes ) + "+" + str ( i ) + ")" ).readAsNumber( )

            pair = longToHex( addr ) + "/" +  str( size )

            if addrsz == "N/A":
                addrsz = pair
            else:
                addrsz = addrsz + ", " + pair

            if i == 7:
                addrsz = addrsz + " ..."
                break

        cells.append( createTextCell( addrsz ) )

        return self.createRecord( cells )

    def getRecords( self, debugSession ):

        records = [ ]

        pocdt = getocdt( PIPE_KCLASS, debugSession )

        n_statics = getStatics( pocdt, debugSession )
        n_objects = getObjects( pocdt, debugSession )

        for i in range( 1, n_statics + 1 ):
            records.append( self.readPipe( GETPPCH( pocdt, debugSession, i ), i, debugSession ) )

        for i in range( n_statics + 1, n_objects + 1 ):
            j = i - n_statics - 1
            if isObjectInuse( pocdt, j, debugSession ):
                records.append( self.readPipe( GETPPCH( pocdt, debugSession, i ), i, debugSession ) )

        return records
