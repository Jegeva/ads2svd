################################################################################
#
# Copyright (C) 2014,2017 Arm Limited (or its affiliates). All rights reserved.
#
# Quadros RTXC
#
#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

from osapi import *
from utils import *

class Mailboxsemaphores( Table ):

    def __init__( self ):

        cid = "mailboxsema4"

        fields = [ createPrimaryField( cid, "id", DECIMAL ) ]

        fields.append( createField( cid, "name", TEXT ) )
        fields.append( createField( cid, "semaphore", TEXT ) )

        Table.__init__( self, cid, fields )

    def readMailbox( self, pmh, i, debugSession ):

        pmhMembers = pmh.dereferencePointer( ).getStructureMembers( )

        name = GetObjectName( MBOX_KCLASS, i, debugSession )

        cells = [ createNumberCell( i ) ]

        cells.append( createTextCell( name ) )

        name = "N/A"
        if checkAttributes( MBOX_KCLASS, ATTR_SEMAPHORES, debugSession ) and isMember( "nesema", pmhMembers ):
            nesema = pmhMembers[ "nesema" ].readAsNumber( )
            if nesema > 0:
                name = GetObjectName( SEMA_KCLASS, nesema, debugSession )

        cells.append( createTextCell( name ) )

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
