################################################################################
#
# Copyright (C) 2014,2017 Arm Limited (or its affiliates). All rights reserved.
#
# Quadros RTXC
#
#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

from osapi import *
from utils import *

class Pipes( Table ):

    def __init__( self ):

        cid = "pipes"

        fields = [ createPrimaryField( cid, "id", DECIMAL ) ]

        fields.append( createField( cid, "name", TEXT ) )
        fields.append( createField( cid, "full", DECIMAL ) )
        fields.append( createField( cid, "empty", DECIMAL ) )
        fields.append( createField( cid, "nbufs", DECIMAL ) )
        fields.append( createField( cid, "bsize", DECIMAL ) )
        fields.append( createField( cid, "worst", TEXT ) )
        fields.append( createField( cid, "usage", TEXT ) )

        Table.__init__( self, cid, fields )

    def readPipe( self, ppch, i, debugSession ):

        ppchMembers = ppch.dereferencePointer( ).getStructureMembers( )

        name = GetObjectName( PIPE_KCLASS, i, debugSession )

        cells = [ createNumberCell( i ) ]

        cells.append( createTextCell( name ) )

        cells.append( createNumberCell( ppchMembers[ "currfull" ].readAsNumber( ) ) )

        cells.append( createNumberCell( ppchMembers[ "currfree" ].readAsNumber( ) ) )

        cells.append( createNumberCell( ppchMembers[ "numbufs" ].readAsNumber( ) ) )

        cells.append( createNumberCell( ppchMembers[ "bufsize" ].readAsNumber( ) ) )

        if checkAttributes( PIPE_KCLASS, ATTR_STATISTICS, debugSession ) and isMember( "worst", ppchMembers ):
            cells.append( createTextCell( str( ppchMembers[ "worst" ].readAsNumber( ) ) ) )
            cells.append( createTextCell( str( ppchMembers[ "usage" ].readAsNumber( ) ) ) )
        else:
            cells.append( createTextCell( "N/A" ) )
            cells.append( createTextCell( "N/A" ) )

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
