################################################################################
#
# Copyright (C) 2014,2017 Arm Limited (or its affiliates). All rights reserved.
#
# Quadros RTXC
#
#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

from osapi import *
from utils import *

class Kernel( Table ):

    def __init__( self ):

        cid = "kernel"

        fields = [ createField( cid, "item", TEXT ), createField( cid, "value", TEXT ) ]

        Table.__init__( self, cid, fields )

    def getRecords( self, debugSession ):

        records = [ ]

        psysprop = KWS_sysprop( debugSession )

        psyspropMembers = psysprop.dereferencePointer( ).getStructureMembers( )

        version = psyspropMembers[ "version" ].readAsNumber( )

        records.append( self.createRecord( [ createTextCell( "Version" ), createTextCell( longToHex( version ) ) ] ) )

        sysrambase = KWS_sysrambase( debugSession ).readAsNumber( )
        records.append( self.createRecord( [ createTextCell( "System RAM base" ), createTextCell( longToHex( sysrambase ) ) ] ) )

        sysramsize = psyspropMembers[ "sysramsize" ].readAsNumber( )
        records.append( self.createRecord( [ createTextCell( "System RAM size" ), createTextCell( str( sysramsize ) ) ] ) )

        sysramunused = KWS_sysramsize( debugSession ).readAsNumber( )
        records.append( self.createRecord( [ createTextCell( "System RAM unused" ), createTextCell( str( sysramunused ) ) ] ) )

        kernelstacksize = psyspropMembers[ "kernelstacksize" ].readAsNumber( )
        records.append( self.createRecord( [ createTextCell( "Stack size" ), createTextCell( str( kernelstacksize ) ) ] ) )

        kernelstackbase = KWS_prtxcstk( debugSession ).readAsNumber( ) - kernelstacksize
        records.append( self.createRecord( [ createTextCell( "Stack base" ), createTextCell( longToHex( kernelstackbase ) ) ] ) )

        kernelstackEnd = kernelstackbase + kernelstacksize

        p = kernelstackbase

        for p in range( kernelstackbase, kernelstackEnd, 4 ):
            val = debugSession.evaluateExpression( "*(unsigned long*)" + str( p ) ).readAsAddress( ).getLinearAddress( )
            if val != 0L:
                break

        kernelstackUnused = p - kernelstackbase
        records.append( self.createRecord( [ createTextCell( "Stack unused" ), createTextCell( str( kernelstackUnused ) ) ] ) )

        noschedflg = KWS_noschedflg( debugSession ).readAsNumber( )
        if noschedflg == 0:
            records.append( self.createRecord( [ createTextCell( "Task Scheduling" ), createTextCell( "On" ) ] ) )
        else:
            records.append( self.createRecord( [ createTextCell( "Task Scheduling" ), \
                                                 createTextCell( "Off: Nest Depth = " + str( noschedflg ) ) ] ) )

        return records
