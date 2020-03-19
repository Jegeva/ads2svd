################################################################################
#
# Copyright (C) 2014,2017 Arm Limited (or its affiliates). All rights reserved.
#
# Quadros RTXC
#
#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

from osapi import *
from utils import *

class Eventsources( Table ):

    def __init__( self ):

        cid = "evsources"

        fields = [ createPrimaryField( cid, "id", DECIMAL ) ]

        fields.append( createField( cid, "name", TEXT ) )
        fields.append( createField( cid, "counters", TEXT ) )
        fields.append( createField( cid, "accum", DECIMAL ) )

        Table.__init__( self, cid, fields )

    def readEventSource( self, psch, i, debugSession ):

        pschMembers = psch.dereferencePointer( ).getStructureMembers( )

        name = GetObjectName( EVNTSRC_KCLASS, i, debugSession )

        cells = [ createNumberCell( i ) ]

        cells.append( createTextCell( name ) )

        pcch = pschMembers[ "pcch" ]

        counters = "N/A"

        while pcch.readAsNumber( ):

            pcchMembers = pcch.dereferencePointer( ).getStructureMembers( )

            counter = pcchMembers[ "counter" ].readAsNumber( )

            name = GetObjectName( COUNTER_KCLASS, counter, debugSession )
            name = name + "(" + str( counter ) + ")"

            if counters == "N/A":
                counters = name
            else:
                counters = counters + "," + name

            pcch = pcchMembers[ "flink" ]

        cells.append( createTextCell( counters ) )

        cells.append( createNumberCell( pschMembers[ "accumulator" ].readAsNumber( ) ) )

        return self.createRecord( cells )

    def getRecords( self, debugSession ):

        records = [ ]

        pocdt = getocdt( EVNTSRC_KCLASS, debugSession )

        n_statics = getStatics( pocdt, debugSession )
        n_objects = getObjects( pocdt, debugSession )

        for i in range( 1, n_statics + 1 ):
            records.append( self.readEventSource( GETPSCH( pocdt, debugSession, i ), i, debugSession ) )

        for i in range( n_statics + 1, n_objects + 1 ):
            j = i - n_statics - 1
            if isObjectInuse( pocdt, j, debugSession ):
                records.append( self.readEventSource( GETPSCH( pocdt, debugSession, i ), i, debugSession ) )

        return records
