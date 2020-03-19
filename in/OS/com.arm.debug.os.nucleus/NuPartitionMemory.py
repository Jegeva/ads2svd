################################################################################
#
# Copyright (C) 2014,2017 Arm Limited (or its affiliates). All rights reserved.
#
#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

from osapi import *
from utils import *

class NuPartitionMemory( Table ):

    def __init__( self ):

        cid = "pm"

        fields = [ createPrimaryField( cid, "cb", ADDRESS ) ]

        fields.append( createField( cid, "name", TEXT ) )
        fields.append( createField( cid, "saddr", TEXT ) )
        fields.append( createField( cid, "psize", DECIMAL ) )
        fields.append( createField( cid, "tsize", DECIMAL ) )
        fields.append( createField( cid, "available", DECIMAL ) )
        fields.append( createField( cid, "alloc", DECIMAL ) )
        fields.append( createField( cid, "fifo", TEXT ) )
        fields.append( createField( cid, "tasks", DECIMAL ) )
        fields.append( createField( cid, "alist", TEXT ) )

        Table.__init__( self, cid, fields )

    def readRecord( self, cbPtr, debugSession ):

        cbMembers = cbPtr.dereferencePointer( ).getStructureMembers( )

        cells = [ createAddressCell( cbPtr.readAsAddress( ) ) ]
        cells.append( createTextCell( cbMembers[ "pm_name" ].readAsNullTerminatedString( ) ) )
        cells.append( createTextCell( longToHex( cbMembers[ "pm_start_address" ].readAsNumber( ) ) ) )
        cells.append( createNumberCell( cbMembers[ "pm_pool_size" ].readAsNumber( ) ) )
        cells.append( createNumberCell( cbMembers[ "pm_partition_size" ].readAsNumber( ) ) )
        cells.append( createNumberCell( cbMembers[ "pm_available" ].readAsNumber( ) ) )
        cells.append( createNumberCell( cbMembers[ "pm_allocated" ].readAsNumber( ) ) )
        cells.append( createTextCell( getNoYesText( cbMembers[ "pm_fifo_suspend" ].readAsNumber( ) ) ) )
        cells.append( createNumberCell( cbMembers[ "pm_tasks_waiting" ].readAsNumber( ) ) )
        cells.append( createTextCell( longToHex( cbMembers[ "pm_available_list" ].readAsNumber( ) ) ) )

        return self.createRecord( cells )

    def getRecords( self, debugSession ):
        cbIter = listIter(debugSession, getFirstPartition, getNextPartition)
        return [self.readRecord(cbPtr, debugSession) for cbPtr in cbIter]
