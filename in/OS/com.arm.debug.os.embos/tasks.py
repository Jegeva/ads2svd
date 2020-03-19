################################################################################
#
# Copyright (C) 2014,2017 Arm Limited (or its affiliates). All rights reserved.
#
# embOS - 3.88c ARM Cortex M / 3.88h ARM Cortex A
#
#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

from osapi import *
from utils import *
from globs import *

# Tasks class
class Tasks( Table ):

    # Class ID
    ID = "tasks"

    # Column definitions
    cols = \
    [
        [ OS_TASK_NAME,             FORMAT_STRING      ]
    ]

    # Column definitions 2
    cols2 = \
    [
        [ OS_TASK_PRIORITY,         FORMAT_NUMBER_STR  ],
        [ OS_TASK_STAT,             FORMAT_TASK_STATUS ],
        [ OS_TASK_TIMEOUT,          FORMAT_TIMEOUT     ],
        [ OS_TASK_NUMACTIVATIONS,   FORMAT_NUMBER_STR  ],
        [ OS_TASK_NUMPREEMPTIONS,   FORMAT_NUMBER_STR  ]
    ]

    # Column definitions 3
    cols3 = \
    [
        [ OS_TASK_PSTACK,           FORMAT_ADDRESS_STR ],
        [ OS_TASK_STACKSIZE,        FORMAT_NUMBER_STR  ],
        [ OS_TASK_PSTACKBOT,        FORMAT_ADDRESS_STR ],
        [ OS_TASK_PWAITLIST,        FORMAT_ADDRESS_STR ],
        [ OS_TASK_EVENTS,           FORMAT_HEX         ],
        [ OS_TASK_EVENT_MASK,       FORMAT_HEX         ],
        [ OS_TASK_EXECTOTAL,        FORMAT_NUMBER_STR  ],
        [ OS_TASK_EXECLAST,         FORMAT_NUMBER_STR  ],
        [ OS_TASK_LOAD,             FORMAT_NUMBER_STR  ],
        [ OS_TASK_TIMESLICEREM,     FORMAT_NUMBER_STR  ],
        [ OS_TASK_TIMESLICERELOAD,  FORMAT_NUMBER_STR  ],
        [ OS_TASK_PEXTENDCONTEXT,   FORMAT_ADDRESS_STR ],
        [ OS_TASK_PTLS,             FORMAT_ADDRESS_STR ],
        [ OS_TASK_ID,               FORMAT_NUMBER_STR  ],
        [ OS_TASK_PNEXT,            FORMAT_ADDRESS_STR ],
        [ OS_TASK_PPREV,            FORMAT_ADDRESS_STR ]
    ]

    # Class constructor
    def __init__( self ):

        # Class ID
        cid = self.ID

        # Create primary field
        fields = [ createPrimaryField( cid, OS_TASK, TEXT ) ]

        # Create task columns
        for col in self.cols:
            fields.append( createField( cid, col[ 0 ], TEXT ) )

        # Add FPU field to indicate if the task is using the FPU
        fields.append( createField( cid, "usingFPU", TEXT ) )

        # Add column to indicate if task was preempted
        fields.append( createField( cid, "intStackFrame", TEXT ) )

        # Create task columns
        for col in self.cols2:
            fields.append( createField( cid, col[ 0 ], TEXT ) )

        # Add stack usage column (current)
        fields.append( createField( cid, "stackUsed", TEXT ) )

        # Add stack usage column (maximum)
        fields.append( createField( cid, "stackUsedMax", TEXT ) )

        # Create task columns
        for col in self.cols3:
            fields.append( createField( cid, col[ 0 ], TEXT ) )

        # Create table
        Table.__init__( self, cid, fields )

    # Read task details
    def readTask( self, cid, members, debugSession ):

        # Populate primary field
        cells = [ createTextCell( cid ) ]

        # Populate task fields
        for col in self.cols:
            cells.append( createTextCell( getMemberValue( members, col[ 0 ], col[ 1 ], debugSession ) ) )

        # Indicate if the task is using the FPU
        stackPointer = members[ OS_TASK_PSTACK ].readAsAddress( )
        regMapName = getRegMapName( stackPointer, members, debugSession )
        cells.append( createTextCell( getFPUStatusText( regMapName ) ) )

        # Indicate if the stack frame was interrupted
        cells.append( createTextCell( getStackFrameText( regMapName ) ) )

        # Populate task fields
        for col in self.cols2:
            cells.append( createTextCell( getMemberValue( members, col[ 0 ], col[ 1 ], debugSession ) ) )

        # Get stack usage info
        stackUsed, stackUsedPc, stackUsedMax, stackUsedMaxPc =  getCurrentStackUsage( members, debugSession )
        cells.append( createTextCell( str( "%3d" % ( stackUsed ) ) + " (" + str( int( stackUsedPc ) ) + "%)" ) )
        cells.append( createTextCell( str( "%3d" % ( stackUsedMax ) ) + " (" + str( int( stackUsedMaxPc ) ) + "%)" ) )

        # Populate task fields
        for col in self.cols3:
            cells.append( createTextCell( getMemberValue( members, col[ 0 ], col[ 1 ], debugSession ) ) )

        # Populated record
        return self.createRecord( cells )

    # Get all running tasks
    def getRecords( self, debugSession ):

        # Blank records
        records = [ ]

        # Make sure OS is up and running
        if isOSRunning( debugSession ):

            # This points to the start of a linked list of all tasks
            pTask = debugSession.evaluateExpression( globCreateRef( [ OS_GLOBAL, OS_GLOBALS_PTASK ] ) )

            # Get all task
            while pTask.readAsNumber( ):

                # Use address of TCB as its id
                pTaskId = pTask.readAsAddress( ).toString( )

                # Get all structure members of the TCB
                pTaskMembers = pTask.dereferencePointer( ).getStructureMembers( )

                # Create task context and add to list
                records.append( self.readTask( pTaskId, pTaskMembers, debugSession ) )

                # Get pointer to next task
                pTask = pTaskMembers[ OS_TASK_PNEXT ]

        # Task records
        return records
