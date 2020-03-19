################################################################################
#
# Copyright (C) 2014,2017 Arm Limited (or its affiliates). All rights reserved.
#
# Quadros RTXC
#
#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

from osapi import *
from utils import *

class Exceptbacktrace( Table ):

    def __init__( self ):

        cid = "exceptbt"

        fields = [ createPrimaryField( cid, "id", DECIMAL ) ]

        fields.append( createField( cid, "name", TEXT ) )
        fields.append( createField( cid, "r0", TEXT ) )
        fields.append( createField( cid, "r1", TEXT ) )
        fields.append( createField( cid, "r2", TEXT ) )
        fields.append( createField( cid, "r3", TEXT ) )
        fields.append( createField( cid, "r4", TEXT ) )
        fields.append( createField( cid, "r5", TEXT ) )
        fields.append( createField( cid, "r6", TEXT ) )
        fields.append( createField( cid, "r7", TEXT ) )
        fields.append( createField( cid, "r8", TEXT ) )
        fields.append( createField( cid, "r9", TEXT ) )
        fields.append( createField( cid, "r10", TEXT ) )
        fields.append( createField( cid, "r11", TEXT ) )
        fields.append( createField( cid, "r12", TEXT ) )
        fields.append( createField( cid, "r14", TEXT ) )
        fields.append( createField( cid, "pc", TEXT ) )
        fields.append( createField( cid, "cpsr", TEXT ) )

        Table.__init__( self, cid, fields )

    def readExecptbt( self, members, i, debugSession ):

        excptn = members[ "excptn" ].readAsNumber( )
        if excptn:
            name = GetObjectName( EXCPTN_KCLASS, excptn, debugSession )
        else:
            name = "kernel"

        cells = [ createNumberCell( i ) ]

        cells.append( createTextCell( name ) )

        cells.append( createTextCell( longToHex( members[ "pksnum" ].readAsNumber( ) ) ) )
        cells.append( createTextCell( longToHex( members[ "r1" ].readAsNumber( ) ) ) )
        cells.append( createTextCell( longToHex( members[ "r2" ].readAsNumber( ) ) ) )
        cells.append( createTextCell( longToHex( members[ "r3" ].readAsNumber( ) ) ) )
        cells.append( createTextCell( longToHex( members[ "r4" ].readAsNumber( ) ) ) )
        cells.append( createTextCell( longToHex( members[ "r5" ].readAsNumber( ) ) ) )
        cells.append( createTextCell( longToHex( members[ "r6" ].readAsNumber( ) ) ) )
        cells.append( createTextCell( longToHex( members[ "r7" ].readAsNumber( ) ) ) )
        cells.append( createTextCell( longToHex( members[ "r8" ].readAsNumber( ) ) ) )
        cells.append( createTextCell( longToHex( members[ "r9" ].readAsNumber( ) ) ) )
        cells.append( createTextCell( longToHex( members[ "r10" ].readAsNumber( ) ) ) )
        cells.append( createTextCell( longToHex( members[ "r11" ].readAsNumber( ) ) ) )
        cells.append( createTextCell( longToHex( members[ "r12" ].readAsNumber( ) ) ) )
        cells.append( createTextCell( longToHex( members[ "r14" ].readAsNumber( ) ) ) )
        cells.append( createTextCell( longToHex( members[ "pc" ].readAsNumber( ) ) ) )
        if isMember( "cpsr", members ):
            cells.append( createTextCell( longToHex( members[ "cpsr" ].readAsNumber( ) ) ) )
        elif isMember( "psr", members ):
            cells.append( createTextCell( longToHex( members[ "psr" ].readAsNumber( ) ) ) )
        else:
            cells.append( createTextCell( "N/A" ) )

        return self.createRecord( cells )

    def getRecords( self, debugSession ):

        records = [ ]

        pframe = KWS_peframe( debugSession )

        i = 0

        while pframe.readAsNumber( ) > 1:

            pframeMembers = pframe.dereferencePointer( ).getStructureMembers( )
            if not isMember( "peframe", pframeMembers ):
                break

            records.append( self.readExecptbt( pframeMembers, i, debugSession ) )

            pframe = pframeMembers[ "peframe" ]

            i = i + 1

        return records
