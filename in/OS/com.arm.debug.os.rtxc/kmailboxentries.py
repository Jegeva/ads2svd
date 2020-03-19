################################################################################
#
# Copyright (C) 2014,2017 Arm Limited (or its affiliates). All rights reserved.
#
# Quadros RTXC
#
#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

from osapi import *
from utils import *

class Mailboxentries( Table ):

    def __init__( self ):

        cid = "mailboxe"

        fields = [ createPrimaryField( cid, "id", DECIMAL ) ]

        fields.append( createField( cid, "name", TEXT ) )
        fields.append( createField( cid, "priority", TEXT ) )
        fields.append( createField( cid, "task", TEXT ) )
        fields.append( createField( cid, "state", TEXT ) )
        fields.append( createField( cid, "addr", TEXT ) )
        fields.append( createField( cid, "msg", TEXT ) )

        Table.__init__( self, cid, fields )

    def readMailBoxEntry(self, name, flinkMembers, i, debugSession ):

        cells = [ createNumberCell( i ) ]

        cells.append( createTextCell( name ) )

        priority = flinkMembers[ "priority" ].readAsNumber( )
        cells.append( createTextCell( getMsgPriText( priority ) ) )

        task = flinkMembers[ "task" ].readAsNumber( )
        if task == 0:
            cells.append( createTextCell( "ACKed" ) )
        else:
            cells.append( createTextCell( GetObjectName( TASK_KCLASS, task, debugSession ) ) )

        state = flinkMembers[ "state" ].readAsNumber( )
        cells.append( createTextCell( getEnvelopText( state ) ) )

        pdata = flinkMembers[ "pdata" ]
        cells.append( createTextCell( longToHex( pdata.readAsNumber( ) ) ) )

        val = debugSession.evaluateExpression( "*(unsigned long*)" + str( pdata.readAsNumber( ) ) ).readAsNumber( )
        cells.append( createTextCell( longToHex( val ) ) )

        return self.createRecord( cells )

    def readMailboxEntries( self, pmh, i, records, debugSession ):

        pmhMembers = pmh.dereferencePointer( ).getStructureMembers( )

        name = GetObjectName( MBOX_KCLASS, i, debugSession )

        flink = pmhMembers[ "flink" ]
        while flink.readAsNumber( ):

            flinkMembers = flink.dereferencePointer( ).getStructureMembers( )

            records.append( self.readMailBoxEntry( name, flinkMembers, i, debugSession ) )

            flink = flinkMembers[ "flink" ]

        return records

    def getRecords( self, debugSession ):

        records = [ ]

        pocdt = getocdt( MBOX_KCLASS, debugSession )

        n_statics = getStatics( pocdt, debugSession )
        n_objects = getObjects( pocdt, debugSession )

        for i in range( 1, n_statics + 1 ):
            self.readMailboxEntries( GETPMH( pocdt, debugSession, i ), i, records, debugSession )

        for i in range( n_statics + 1, n_objects + 1 ):
            j = i - n_statics - 1
            if isObjectInuse( pocdt, j, debugSession ):
                self.readMailboxEntries( GETPMH( pocdt, debugSession, i ), i, records, debugSession )

        return records
