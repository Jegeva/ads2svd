################################################################################
#
# Copyright (C) 2014,2017 Arm Limited (or its affiliates). All rights reserved.
#
# Quadros RTXC
#
#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

from osapi import *
from utils import *

class Pipeemptybufs( Table ):

    def __init__( self ):

        cid = "pipeeb"

        fields = [ createPrimaryField( cid, "id", DECIMAL ) ]

        fields.append( createField( cid, "name", TEXT ) )
        fields.append( createField( cid, "addr", TEXT ) )

        Table.__init__( self, cid, fields )

    def readPipe( self, ppch, i, debugSession ):

        ppchMembers = ppch.dereferencePointer( ).getStructureMembers( )

        name = GetObjectName( PIPE_KCLASS, i, debugSession )

        cells = [ createNumberCell( i ) ]

        cells.append( createTextCell( name ) )

        freeBufCount = ppchMembers[ "currfree" ].readAsNumber( )

        freebufs = ppchMembers[ "freebase" ].readAsNumber( )

        addresses = "N/A"

        for i in range( freeBufCount ):

            addr = debugSession.evaluateExpression( "*((unsigned long *)" + str( freebufs ) + "+" + str ( i ) + ")" ).readAsNumber( )

            if addresses == "N/A":
                addresses = longToHex( addr )
            else:
                addresses = addresses + ", " + longToHex( addr )

            if i == 7:
                addresses = addresses + " ..."
                break

        cells.append( createTextCell( addresses ) )

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
