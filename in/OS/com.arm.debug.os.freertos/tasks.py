# ###############################################################################
#
# Copyright (C) 2014,2017 Arm Limited (or its affiliates). All rights reserved.
#
# FreeRTOS - V7.6.0 / V8.0.0RC ARM Cortex M / A
#
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

from osapi import *
from utils import *
from globs import *

# Tasks class
class Tasks( Table ):

    # Constants
    NO_DEFEF    = False
    DEREF       = True

    # Class ID
    ID = "tasks"

    # Column definitions
    cols = \
    [
        [ TCB_PC_TASK_NAME,         FORMAT_STRING,      TEXT    ]
    ]

    # Column definitions 2
    cols2 = \
    [
        [ TCB_UX_TCB_NUMBER,        FORMAT_NUMBER_STR,  TEXT    ],
        [ TCB_UX_TASK_NUMBER,       FORMAT_NUMBER_STR,  TEXT    ],
        [ TCB_UL_RUN_TIME_COUNTER,  FORMAT_NUMBER_STR,  TEXT    ],
        [ TCB_X_MPU_SETTINGS,       FORMAT_NUMBER_STR,  TEXT    ],
        [ TCB_UX_PRIORITY,          FORMAT_NUMBER,      DECIMAL ],
        [ TCB_PX_TOP_OF_STACK,      FORMAT_ADDRESS,     ADDRESS ],
        [ TCB_PX_STACK,             FORMAT_ADDRESS,     ADDRESS ],
        [ TCB_PX_END_OF_STACK,      FORMAT_ADDRESS_STR, TEXT    ],
        [ TCB_UX_CRITICAL_NESTING,  FORMAT_NUMBER_STR,  TEXT    ],
        [ TCB_UX_BASE_PRIORITY,     FORMAT_NUMBER_STR,  TEXT    ],
        [ TCB_PX_TASK_TAG,          FORMAT_ADDRESS_STR, TEXT    ],
        [ TCB_X_NEWLIB_REENT,       FORMAT_ADDRESS_STR, TEXT    ]
    ]

    # Column definitions 3
    cols3 = \
    [
        [ XLISTI_PV_CONTAINER,      FORMAT_ADDRESS_STR, TEXT    ],
        [ XLISTI_X_ITEM_VALUE,      FORMAT_HEX,         TEXT    ],
        [ XLISTI_PV_OWNER,          FORMAT_TASK_NAME,   TEXT    ]
    ]

    # Class constructor
    def __init__( self ):

        # Class ID
        cid = self.ID

        # Create primary field
        fields = [ createPrimaryField( cid, TCB_T, TEXT ) ]

        # Add task name
        for col in self.cols:
            fields.append( createField( cid, col[ 0 ], col[ 2 ] ) )

        # Add state field (this does not exist in the TCB, but determined from list)
        fields.append( createField( cid, "state", TEXT ) )

        # Add FPU field to indicate if the task is using the FPU
        fields.append( createField( cid, "usingFPU", TEXT ) )

        # Create task columns
        for col in self.cols2:
            fields.append( createField( cid, col[ 0 ], col[ 2 ] ) )
        for col in self.cols3:
            fields.append( createField( cid, col[ 0 ], col[ 2 ] ) )

        fields.append( createField( cid, "tasksWaiting", TEXT ) )

        # Create table
        Table.__init__( self, cid, fields )

    # Read task details
    def readTask( self, cid, members, state, debugSession ):

        # Populate primary field
        cells = [ createTextCell( cid ) ]

        # Populate task fields
        for col in self.cols:
            createCell( cells, members, col[ 0 ], col[ 1 ], col[ 2 ], debugSession )

        # Set task state
        cells.append( createTextCell( state ) )

        # Indicate if the task is using the FPU
        stackPointer = members[ TCB_PX_TOP_OF_STACK ].readAsAddress( )
        regMapName = getRegMapName( stackPointer, debugSession )
        cells.append( createTextCell( getFPUStatusText( regMapName ) ) )

        # Populate task fields
        for col in self.cols2:
            createCell( cells, members, col[ 0 ], col[ 1 ], col[ 2 ], debugSession )

        # Get event list item structure members
        eventListItemMembers = members[ TCB_X_EVENT_LIST_ITEM ].getStructureMembers( )

        # Is event list item being used?
        if eventListItemMembers[ XLISTI_PV_CONTAINER ].readAsNumber( ) == 0:

            # No, all remaining columns are not valid
            for col in self.cols3:
                cells.append( createTextCell( "N/A" ) )
            cells.append( createTextCell( "N/A" ) )

        else:

            # Yes, display ebent list information
            for col in self.cols3:
                cells.append( createTextCell( getMemberValue( eventListItemMembers, col[ 0 ], col[ 1 ], debugSession ) ) )

            # Get event list
            eventList = eventListItemMembers[ XLISTI_PV_CONTAINER ].dereferencePointer( XLIST + "*" )

            # Get task names in the list
            cells.append( createTextCell( getItemNamesFromList( eventList, TCB_T, TCB_PC_TASK_NAME, debugSession ) ) )

        # Populated record
        return self.createRecord( cells )

    # Add task to record
    def addTask( self, tcb, taskState, records, debugSession ):

        # Get TCB address and use it as the task ID
        pTaskId = hex( tcb.getLocationAddress( ).getLinearAddress( ) )

        # Get the TCB structure members
        pTaskMembers = tcb.getStructureMembers( )

        # Create task record
        records.append( self.readTask( pTaskId, pTaskMembers, taskState, debugSession ) )


    # Create task records for all tasks in a list
    def readTasks( self, listName, records, debugSession, deRef=NO_DEFEF ):

        # Make sure list exists
        if debugSession.symbolExists( listName ):

            # Get task list
            taskList = debugSession.evaluateExpression( listName )

            # Is list a pointer to a list?
            if deRef == self.DEREF:

                # Make sure valid before doing dereference
                if taskList.readAsNumber( ) == 0:
                    return      # error, cannot dereference

                # Get task list from pointer
                taskList = taskList.dereferencePointer( )

            # Determine task state from list
            taskState = getStateNameFromList( listName )

            # Reads all tasks in the list
            tcbListItems = readTCBItems( taskList )

            # Create task records
            for tcb in tcbListItems :
                self.addTask( tcb, taskState, records, debugSession )

    # Get all running tasks
    def getRecords( self, debugSession ):

        # Blank records
        records = [ ]

        # Make sure OS is up and running
        if debugSession.evaluateExpression( X_SCHEDULER_RUNNING ).readAsNumber( ) == 1:

            # Get current task context
            currentTCBPtr = debugSession.evaluateExpression( PX_CURRENT_TCB )

            # Get ready tasks
            listName = PX_READY_TASKS_LISTS
            readyLists = debugSession.evaluateExpression( listName ).getArrayElements( )
            taskState = getStateNameFromList( listName )

            # Process each ready (priority) list
            for readyList in readyLists:

                # Get tasks in the list
                tcbListItems = readTCBItems( readyList )

                # Create task records
                for tcb in tcbListItems :

                    # Determine which task is the running task
                    if tcb.getLocationAddress( ).getLinearAddress( ) == currentTCBPtr.readAsNumber( ):
                        ts = "RUNNING"
                    else:
                        ts = taskState

                    # Create task record
                    self.addTask( tcb, ts, records, debugSession )

            # Get delayed
            self.readTasks( PX_DELAYED_TASKLIST, records, debugSession, self.DEREF )

            # Get delayed (over-flowed) tasks
            self.readTasks( PX_OVERFLOW_DELAYED_TASK_LIST, records, debugSession, self.DEREF )

            # Get pending ready tasks
            self.readTasks( X_PENDING_READY_LIST, records, debugSession )

            # Get tasks waiting termination
            self.readTasks( X_TASKS_WAITING_TERMINATION, records, debugSession )

            # Get suspended tasks
            self.readTasks( X_SUSPENDED_TASK_LIST, records, debugSession )

        # Task records
        return records
