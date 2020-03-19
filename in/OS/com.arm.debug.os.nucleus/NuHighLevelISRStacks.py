################################################################################
#
# Copyright (C) 2014,2017 Arm Limited (or its affiliates). All rights reserved.
#
#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

from osapi import *
from utils import *

class NuHighLevelISRStacks( Table ):

    def __init__( self ):

        cid = "hlis"

        fields = [ createPrimaryField( cid, "cb", ADDRESS ) ]

        fields.append( createField( cid, "name", TEXT ) )
        fields.append( createField( cid, "current", TEXT ) )
        fields.append( createField( cid, "start", TEXT ) )
        fields.append( createField( cid, "end", TEXT ) )
        fields.append( createField( cid, "size", DECIMAL ) )
        fields.append( createField( cid, "minimum", DECIMAL ) )

        Table.__init__( self, cid, fields )

    def readRecord( self, cbPtr, debugSession ):

        cbMembers = cbPtr.dereferencePointer( ).getStructureMembers( )

        cells = [ createAddressCell( cbPtr.readAsAddress( ) ) ]
        cells.append( createTextCell( cbMembers[ "tc_name" ].readAsNullTerminatedString( ) ) )
        cells.append( createTextCell( longToHex( cbMembers[ "tc_stack_pointer" ].readAsNumber( ) ) ) )
        cells.append( createTextCell( longToHex( cbMembers[ "tc_stack_start" ].readAsNumber( ) ) ) )
        cells.append( createTextCell( longToHex( cbMembers[ "tc_stack_end" ].readAsNumber( ) ) ) )
        cells.append( createNumberCell( cbMembers[ "tc_stack_size" ].readAsNumber( ) ) )
        cells.append( createNumberCell( cbMembers[ "tc_stack_minimum" ].readAsNumber( ) ) )

        return self.createRecord( cells )

    def getRecords( self, debugSession ):
        cbIter = listIter(debugSession, getFirstHisr, getNextHisr)
        return [self.readRecord(cbPtr, debugSession) for cbPtr in cbIter]
