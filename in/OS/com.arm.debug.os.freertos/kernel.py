# ###############################################################################
#
# Copyright (C) 2014,2017 Arm Limited (or its affiliates). All rights reserved.
#
# FreeRTOS - V7.6.0 / V8.0.0RC ARM Cortex M / A
#
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

# Import all!
from osapi import *
from utils import *
from globs import *

# Table headings (defined in messages.properties)
ITEM_HEADING    = "item"
VALUE_HEADING   = "value"
DESC_HEADING    = "desc"

# Kernel global variables and constants
KERNEL_ITEMS = \
[
    [ [ TSKKERNEL_VERSION_NUMBER              ], FORMAT_STRING,      "OS version number"                                            ],
    [ [ PX_CURRENT_TCB                        ], FORMAT_ADDRESS_STR, "Pointer to TCB of task currently runing"                      ],
    [ [ UX_TASKS_DELETED                      ], FORMAT_NUMBER_STR,  "Tasks that have been deleted, but their memory not yet freed" ],
    [ [ UX_CURRENT_NUMBER_OF_TASKS            ], FORMAT_NUMBER_STR,  "Number of running tasks"                                      ],
    [ [ X_TICK_COUNT                          ], FORMAT_NUMBER_STR,  "Current tick count"                                           ],
    [ [ UX_TOP_READY_PRIORITY                 ], FORMAT_NUMBER_STR,  "Top ready priority"                                           ],
    [ [ X_SCHEDULER_RUNNING                   ], FORMAT_NUMBER_STR,  "Scheduler running flag"                                       ],
    [ [ UX_SCHEDULER_SUSPENDED                ], FORMAT_NUMBER_STR,  "Scheduler suspended flag"                                     ],
    [ [ UX_PENDED_TICKS                       ], FORMAT_NUMBER_STR,  "Number of pending ticks"                                      ],
    [ [ X_YIELD_PENDING                       ], FORMAT_NUMBER_STR,  "Yield pending flag"                                           ],
    [ [ X_NUM_OF_OVERFLOWS                    ], FORMAT_NUMBER_STR,  "Number of overflows"                                          ],
    [ [ UX_TASK_NUMBER                        ], FORMAT_NUMBER_STR,  "Current task number"                                          ],
    [ [ X_NEXT_TASK_UNBLOCK_TIME              ], FORMAT_NUMBER_STR,  "Next task unblock time"                                       ],
    [ [ UL_TASK_SWITCHED_IN_TIME              ], FORMAT_NUMBER_STR,  "Task switched in time"                                        ],
    [ [ UL_TOTAL_RUN_TIME                     ], FORMAT_NUMBER_STR,  "Total run time"                                               ],
    [ [ PX_DELAYED_TASKLIST                   ], FORMAT_ADDRESS_STR, "Pointer to list of delayed tasks"                             ],
    [ [ PX_OVERFLOW_DELAYED_TASK_LIST         ], FORMAT_ADDRESS_STR, "Pointer to list of delayed tasks (overflowed)"                ],
    [ [ UL_CRITICAL_NESTING                   ], FORMAT_NUMBER_STR,  "Critical nesting count"                                       ],
    [ [ UL_PORT_TASK_HAS_FPU_CONTEXT          ], FORMAT_NUMBER_STR,  "Task has floating point enabled"                              ],
    [ [ UL_PORT_YIELD_REQUIRED                ], FORMAT_NUMBER_STR,  "Port yield required"                                          ],
    [ [ UL_PORT_INTERRUPT_NESTING             ], FORMAT_NUMBER_STR,  "Port interrupt nesting count"                                 ],
    [ [ PX_READY_TASKS_LISTS                  ], FORMAT_TASK_LISTS,  "List of list of ready tasks"                                  ],
    [ [ X_DELAYED_TASK_LIST1                  ], FORMAT_TASK_LIST,   "Delayed tasks list 1"                                         ],
    [ [ X_DELAYED_TASK_LIST2                  ], FORMAT_TASK_LIST,   "Delayed tasks list 2"                                         ],
    [ [ X_PENDING_READY_LIST                  ], FORMAT_TASK_LIST,   "List of pending ready tasks"                                  ],
    [ [ X_TASKS_WAITING_TERMINATION           ], FORMAT_TASK_LIST,   "List of tasks waiting for termination"                        ],
    [ [ X_SUSPENDED_TASK_LIST                 ], FORMAT_TASK_LIST,   "List of suspended tasks"                                      ],
    [ [ X_QUEUE_REGISTRY                      ], FORMAT_LOCATION,    "Queue registry"                                               ],
    [ [ PX_CURRENT_TIMER_LIST                 ], FORMAT_ADDRESS_STR, "Current timer list"                                           ],
    [ [ PX_OVERFLOW_TIMER_LIST                ], FORMAT_ADDRESS_STR, "Overflow timer list"                                          ],
    [ [ TSKIDLE_PRIORITY                      ], FORMAT_NUMBER_STR,  "Defines the priority used by the idle task"                   ],
    [ [ TMRCOMMAND_EXECUTE_CALLBACK           ], FORMAT_NUMBER_STR,  "Queue ID value"                                               ],
    [ [ TMRCOMMAND_START                      ], FORMAT_NUMBER_STR,  "Queue ID value"                                               ],
    [ [ TMRCOMMAND_STOP                       ], FORMAT_NUMBER_STR,  "Queue ID value"                                               ],
    [ [ TMRCOMMAND_CHANGE_PERIOD              ], FORMAT_NUMBER_STR,  "Queue ID value"                                               ],
    [ [ TMRCOMMAND_DELETE                     ], FORMAT_NUMBER_STR,  "Queue ID value"                                               ],
    [ [ PDFALSE                               ], FORMAT_NUMBER_STR,  "Value for FALSE"                                              ],
    [ [ PDTRUE                                ], FORMAT_NUMBER_STR,  "Value for TRUE"                                               ],
    [ [ PDPASS                                ], FORMAT_NUMBER_STR,  "Value for PASS"                                               ],
    [ [ PDFAIL                                ], FORMAT_NUMBER_STR,  "Value for FAIL"                                               ],
    [ [ ERRQUEUE_EMPTY                        ], FORMAT_NUMBER_STR,  "Queue empty error"                                            ],
    [ [ ERRQUEUE_FULL                         ], FORMAT_NUMBER_STR,  "Queue full error"                                             ],
    [ [ ERRCOULD_NOT_ALLOCATE_REQUIRED_MEMORY ], FORMAT_NUMBER_STR,  "Cannot allocate memory error"                                 ],
    [ [ ERRQUEUE_BLOCKED                      ], FORMAT_NUMBER_STR,  "Queue blocked error"                                          ],
    [ [ ERRQUEUE_YIELD                        ], FORMAT_NUMBER_STR,  "Queue yield error"                                            ],
    [ [ QUEUE_SEND_TO_BACK                    ], FORMAT_NUMBER_STR,  "Queue send to back value"                                     ],
    [ [ QUEUE_SEND_TO_FRONT                   ], FORMAT_NUMBER_STR,  "Queue send to front value"                                    ],
    [ [ QUEUE_OVER_WRITE                      ], FORMAT_NUMBER_STR,  "Queue overwrite value"                                        ],
    [ [ QUEUE_QUEUE_TYPE_BASE                 ], FORMAT_NUMBER_STR,  "Queue type base value"                                        ],
    [ [ QUEUE_QUEUE_TYPE_SET                  ], FORMAT_NUMBER_STR,  "Queue type set value"                                         ],
    [ [ QUEUE_QUEUE_TYPE_MUTEX                ], FORMAT_NUMBER_STR,  "Queue type mutex value"                                       ],
    [ [ QUEUE_QUEUE_TYPE_COUNTING_SEMAPHORE   ], FORMAT_NUMBER_STR,  "Queue type counting semaphore value"                          ],
    [ [ QUEUE_QUEUE_TYPE_BINARY_SEMAPHORE     ], FORMAT_NUMBER_STR,  "Queue type binary semaphore value"                            ],
    [ [ QUEUE_QUEUE_TYPE_RECURSIVE_MUTEX      ], FORMAT_NUMBER_STR,  "Queue type recursive mutex value"                             ],
    [ [ SEM_BINARY_SEMAPHORE_QUEUE_LENGTH     ], FORMAT_NUMBER_STR,  "Binary semaphore queue length"                                ],
    [ [ SEM_SEMAPHORE_QUEUE_ITEM_LENGTH       ], FORMAT_NUMBER_STR,  "Semaphore queue item length"                                  ],
    [ [ SEM_GIVE_BLOCK_TIME                   ], FORMAT_NUMBER_STR,  "Semaphore give block time"                                    ]
]

# Kernel data
class KernelData( Table ):

    # Constructor
    def __init__( self ):

        # Id name
        tid = "kernel"

        # Configure headings
        fields = \
        [
            createField( tid, ITEM_HEADING,  TEXT ),
            createField( tid, VALUE_HEADING, TEXT ),
            createField( tid, DESC_HEADING,  TEXT )
        ]

        # Create table
        Table.__init__( self, tid, fields )

    # Read table entry
    def readRecord( self, itemIndex, debugSession ):

        # Get item details
        itemRefs   = KERNEL_ITEMS[ itemIndex ][ 0 ]      # Item reference
        itemType   = KERNEL_ITEMS[ itemIndex ][ 1 ]      # Item format type
        itemDesc   = KERNEL_ITEMS[ itemIndex ][ 2 ]      # Item description

        # Create reference to be evaluated
        itemRef = globCreateRef( itemRefs )

        # Make sure reference exist?
        if debugSession.symbolExists( itemRef ):

            # Evaluate expression
            expr = debugSession.evaluateExpression( itemRef )

            # Format expression
            itemValue = formatExpr( expr, itemType, debugSession, "" )

            # Value created?
            if len( itemValue ):

                # Yes, create entry in table
                cells = [ createTextCell( itemRef ), createTextCell( itemValue ), createTextCell( itemDesc ) ]

                # Create recored entry
                return self.createRecord( cells )

    # Get all kernel configuration data
    def getRecords( self, debugSession ):

        # Clear records
        records = [ ]

        # Get maximum number of items
        j = len( KERNEL_ITEMS )

        # Get each item
        for i in range( j ):
            record = self.readRecord( i, debugSession )
            if record:
                records.append( record )

        # All items
        return records
