################################################################################
#
# Copyright (C) 2014,2017 Arm Limited (or its affiliates). All rights reserved.
#
# Quadros RTXC
#
#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

from osapi import *
from utils import *

class Mailboxes( Table ):

    def __init__( self ):

        cid = "mailboxes"

        fields = [ createPrimaryField( cid, "id", DECIMAL ) ]

        fields.append( createField( cid, "name", TEXT ) )
        fields.append( createField( cid, "current", DECIMAL ) )
        fields.append( createField( cid, "usage", TEXT ) )
        fields.append( createField( cid, "order", TEXT ) )
        fields.append( createField( cid, "waiters", TEXT ) )

        Table.__init__( self, cid, fields )

    def readMailbox( self, pmh, i, debugSession ):

        pmhMembers = pmh.dereferencePointer( ).getStructureMembers( )

        name = GetObjectName( MBOX_KCLASS, i, debugSession )

        cells = [ createNumberCell( i ) ]

        cells.append( createTextCell( name ) )

        cells.append( createNumberCell( pmhMembers[ "cur" ].readAsNumber( ) ) )

        if checkAttributes( MBOX_KCLASS, ATTR_STATISTICS, debugSession ) and isMember( "usage", pmhMembers ):
            cells.append( createTextCell( str( pmhMembers[ "usage" ].readAsNumber( ) ) ) )
        else:
            cells.append( createTextCell( "N/A" ) )

        attr = pmhMembers[ "attributes" ].readAsNumber( )

        if attr & ATTR_FIFO_ORDER:
            cells.append( createTextCell( "FIFO" ) )
        else:
            cells.append( createTextCell( "Priority" ) )

        cells.append( createTextCell( getWaiters( pmhMembers, debugSession ) ) )

        return self.createRecord( cells )

    def getRecords( self, debugSession ):

        records = [ ]

        pocdt = getocdt( MBOX_KCLASS, debugSession )

        n_statics = getStatics( pocdt, debugSession )
        n_objects = getObjects( pocdt, debugSession )

        for i in range( 1, n_statics + 1 ):
            records.append( self.readMailbox( GETPMH( pocdt, debugSession, i ), i, debugSession ) )

        for i in range( n_statics + 1, n_objects + 1 ):
            j = i - n_statics - 1
            if isObjectInuse( pocdt, j, debugSession ):
                records.append( self.readMailbox( GETPMH( pocdt, debugSession, i ), i, debugSession ) )

        return records
