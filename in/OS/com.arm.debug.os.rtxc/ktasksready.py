################################################################################
#
# Copyright (C) 2014,2017 Arm Limited (or its affiliates). All rights reserved.
#
# Quadros RTXC
#
#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

from osapi import *
from utils import *

class Tasksready( Table ):

    def __init__( self ):

        cid = "tasksready"

        fields = [ createPrimaryField( cid, "id", DECIMAL ) ]

        fields.append( createField( cid, "name", TEXT ) )
        fields.append( createField( cid, "priority", DECIMAL ) )
        fields.append( createField( cid, "state", TEXT ) )

        Table.__init__( self, cid, fields )

    def readTask( self, tcbMembers, debugSession ):

        taskId = tcbMembers[ "task" ].readAsNumber( )
        taskName = GetObjectName( TASK_KCLASS, taskId, debugSession )

        cells = [ createNumberCell( taskId ) ]
        cells.append( createTextCell( taskName ) )
        cells.append( createNumberCell( tcbMembers[ "priority" ].readAsNumber( ) ) )
        cells.append( createTextCell( getTaskStatusText( tcbMembers[ "status" ].readAsNumber( ) ) ) )

        return self.createRecord( cells )

    def getRecords( self, debugSession ):

        records = [ ]

        pocdt = getocdt( TASK_KCLASS, debugSession )

        ptcb = gethipritsk( debugSession )

        while ptcb.readAsNumber( ):

            tcbMembers = ptcb.dereferencePointer( ).getStructureMembers( )

            records.append( self.readTask( tcbMembers, debugSession ) )

            ptcb = tcbMembers[ "flink" ]

        return records
