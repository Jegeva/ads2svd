################################################################################
#
# Copyright (C) 2014,2017 Arm Limited (or its affiliates). All rights reserved.
#
# Quadros RTXC
#
#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

from osapi import *
from utils import *

class Taskstacks( Table ):

    def __init__( self ):

        cid = "taskstacks"

        fields = [ createPrimaryField( cid, "id", DECIMAL ) ]

        fields.append( createField( cid, "name", TEXT ) )
        fields.append( createField( cid, "sp", TEXT ) )
        fields.append( createField( cid, "base", TEXT ) )
        fields.append( createField( cid, "size", DECIMAL ) )
        fields.append( createField( cid, "used", DECIMAL ) )
        fields.append( createField( cid, "spare", DECIMAL ) )

        Table.__init__( self, cid, fields )

    def readStack( self, tcbPtr, fillChar, debugSession ):

        tcbMembers = tcbPtr.dereferencePointer( ).getStructureMembers( )

        taskId = tcbMembers[ "task" ].readAsNumber( )
        taskName = GetObjectName( TASK_KCLASS, taskId, debugSession )

        cells = [ createNumberCell( taskId ) ]
        cells.append( createTextCell( taskName ) )
        cells.append( createTextCell( longToHex( tcbMembers[ "sp" ].readAsNumber( ) ) ) )
        stackSize = tcbMembers[ "stacksize" ].readAsNumber( )
        cells.append( createTextCell( longToHex( tcbMembers[ "stackbase" ].readAsNumber( ) ) ) )
        cells.append( createNumberCell( stackSize ) )
        stackBase = tcbMembers[ "stackbase" ].readAsNumber( )
        stackEnd = stackBase + stackSize
        p = stackBase

        for p in range( stackBase, stackEnd, 4 ):
            val = debugSession.evaluateExpression( "*(unsigned long*)" + str( p ) ).readAsAddress( ).getLinearAddress( )
            if val != fillChar:
                break

        stackUnused = p - stackBase
        stackUsed = stackSize - stackUnused

        cells.append( createNumberCell( stackUsed ) )
        cells.append( createNumberCell( stackUnused ) )

        return self.createRecord( cells )

    def getRecords( self, debugSession ):

        records = [ ]

        pocdt = getocdt( TASK_KCLASS, debugSession )

        fillChar = getStackFillChar( debugSession )

        n_statics = getStatics( pocdt, debugSession )
        n_objects = getObjects( pocdt, debugSession )

        for i in range( n_statics + 1 ):
            records.append( self.readStack( GETPTCB( pocdt, debugSession, i ), fillChar, debugSession ) )

        for i in range( n_statics + 1, n_objects + 1 ):
            j = i - n_statics - 1
            if isObjectInuse( pocdt, j, debugSession ):
                records.append( self.readStack( GETPTCB( pocdt, debugSession, i ), fillChar, debugSession ) )

        return records
