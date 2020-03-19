################################################################################
#
# Copyright (C) 2014,2017 Arm Limited (or its affiliates). All rights reserved.
#
# Quadros RTXC
#
#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

from osapi import *
from utils import *

class Counters( Table ):

    def __init__( self ):

        cid = "counters"

        fields = [ createPrimaryField( cid, "id", DECIMAL ) ]

        fields.append( createField( cid, "name", TEXT ) )
        fields.append( createField( cid, "evsrc", TEXT ) )
        fields.append( createField( cid, "accum", DECIMAL ) )
        fields.append( createField( cid, "count", DECIMAL ) )
        fields.append( createField( cid, "modulus", DECIMAL ) )

        Table.__init__( self, cid, fields )

    def readCounter( self, pcch, i, debugSession ):

        pcchMembers = pcch.dereferencePointer( ).getStructureMembers( )

        name = GetObjectName( COUNTER_KCLASS, i, debugSession )

        cells = [ createNumberCell( i ) ]

        cells.append( createTextCell( name ) )

        evntsrc = pcchMembers[ "evntsrc" ].readAsNumber( )
        name = GetObjectName( EVNTSRC_KCLASS, evntsrc, debugSession )
        cells.append( createTextCell( name ) )

        cells.append( createNumberCell( pcchMembers[ "accumulator" ].readAsNumber( ) ) )

        cells.append( createNumberCell( pcchMembers[ "count" ].readAsNumber( ) ) )

        cells.append( createNumberCell( pcchMembers[ "modulus" ].readAsNumber( ) ) )

        return self.createRecord( cells )

    def getRecords( self, debugSession ):

        records = [ ]

        pocdt = getocdt( COUNTER_KCLASS, debugSession )

        n_statics = getStatics( pocdt, debugSession )
        n_objects = getObjects( pocdt, debugSession )

        for i in range( 1, n_statics + 1 ):
            records.append( self.readCounter( GETPCCH( pocdt, debugSession, i ), i, debugSession ) )

        for i in range( n_statics + 1, n_objects + 1 ):
            j = i - n_statics - 1
            if isObjectInuse( pocdt, j, debugSession ):
                records.append( self.readCounter( GETPCCH( pocdt, debugSession, i ), i, debugSession ) )

        return records
