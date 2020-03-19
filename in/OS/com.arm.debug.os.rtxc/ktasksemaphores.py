################################################################################
#
# Copyright (C) 2014,2017 Arm Limited (or its affiliates). All rights reserved.
#
# Quadros RTXC
#
#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

from osapi import *
from utils import *

class Tasksemaphores( Table ):

    def __init__( self ):

        cid = "tasksema4"

        fields = [ createPrimaryField( cid, "id", DECIMAL ) ]

        fields.append( createField( cid, "name", TEXT ) )
        fields.append( createField( cid, "sname", TEXT ) )

        Table.__init__( self, cid, fields )

    def readTask( self, tcbPtr, debugSession ):

        tcbMembers = tcbPtr.dereferencePointer( ).getStructureMembers( )

        taskId = tcbMembers[ "task" ].readAsNumber( )
        taskName = GetObjectName( TASK_KCLASS, taskId, debugSession )

        cells = [ createNumberCell( taskId ) ]
        cells.append( createTextCell( taskName ) )

        taskSema = tcbMembers[ "sema" ].readAsNumber( )
        if( taskSema != 0 ):
            cells.append( createTextCell( GetObjectName( SEMA_KCLASS, taskSema, debugSession ) ) )
        else:
            cells.append( createTextCell( "N/A" ) )

        return self.createRecord( cells )

    def getRecords( self, debugSession ):

        records = [ ]

        pocdt = getocdt( TASK_KCLASS, debugSession )

        n_statics = getStatics( pocdt, debugSession )
        n_objects = getObjects( pocdt, debugSession )

        for i in range( n_statics + 1 ):
            records.append( self.readTask( GETPTCB( pocdt, debugSession, i ), debugSession ) )

        for i in range( n_statics + 1, n_objects + 1 ):
            j = i - n_statics - 1
            if isObjectInuse( pocdt, j, debugSession ):
                records.append( self.readTask( GETPTCB( pocdt, debugSession, i ), debugSession ) )

        return records
