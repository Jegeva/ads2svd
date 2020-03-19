################################################################################
#
# Copyright (C) 2014,2017 Arm Limited (or its affiliates). All rights reserved.
#
#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

from osapi import *
from utils import *

class NuDynamicMemory( Table ):

    def __init__( self ):

        cid = "dm"

        fields = [ createPrimaryField( cid, "cb", ADDRESS ) ]

        fields.append( createField( cid, "name", TEXT ) )
        fields.append( createField( cid, "saddr", TEXT ) )
        fields.append( createField( cid, "psize", DECIMAL ) )
        fields.append( createField( cid, "minalloc", DECIMAL ) )
        fields.append( createField( cid, "available", DECIMAL ) )
        fields.append( createField( cid, "memlist", TEXT ) )
        fields.append( createField( cid, "fifo", TEXT ) )
        fields.append( createField( cid, "tasks", DECIMAL ) )

        Table.__init__( self, cid, fields )

    def readRecord( self, cbPtr, debugSession ):

        cbMembers = cbPtr.dereferencePointer( ).getStructureMembers( )

        cells = [ createAddressCell( cbPtr.readAsAddress( ) ) ]
        cells.append( createTextCell( cbMembers[ "dm_name" ].readAsNullTerminatedString( ) ) )
        cells.append( createTextCell( longToHex( cbMembers[ "dm_start_address" ].readAsNumber( ) ) ) )
        cells.append( createNumberCell( cbMembers[ "dm_pool_size" ].readAsNumber( ) ) )
        cells.append( createNumberCell( cbMembers[ "dm_min_allocation" ].readAsNumber( ) ) )
        cells.append( createNumberCell( cbMembers[ "dm_available" ].readAsNumber( ) ) )
        cells.append( createTextCell( longToHex( cbMembers[ "dm_memory_list" ].readAsNumber( ) ) ) )
        cells.append( createTextCell( getNoYesText( cbMembers[ "dm_fifo_suspend" ].readAsNumber( ) ) ) )
        cells.append( createNumberCell( cbMembers[ "dm_tasks_waiting" ].readAsNumber( ) ) )

        return self.createRecord( cells )

    def getRecords( self, debugSession ):
        cbIter = listIter(debugSession, getFirstDynamic, getNextDynamic)
        return [self.readRecord(cbPtr, debugSession) for cbPtr in cbIter]
