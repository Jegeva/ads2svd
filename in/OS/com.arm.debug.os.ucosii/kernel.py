# Copyright (C) 2013-2014,2017 Arm Limited (or its affiliates). All rights reserved.

# Import all!
from osapi import *
from utils import *
from globs import *

# Kernel global variables and constants
KERNEL_ITEMS = \
[
    # Variables
    [ OS_VERSION_NBR,                  "number",       "OS version number"                              ],
    [ OS_CPU_USAGE,                    "number",       "Percentage of CPU used"                         ],
    [ OS_CTX_SW_CTR,                   "number",       "Counter of number of context switches"          ],
    [ OS_EVENT_FREE_LIST,              "address",      "Pointer to list of free EVENT control blocks"   ],
    [ OS_FLAG_FREE_LIST,               "address",      "Pointer to free list of event flag groups"      ],
    [ OS_IDLE_CTR_MAX,                 "number",       "Max. value that idle ctr can take in 1 sec."    ],
    [ OS_IDLE_CTR_RUN,                 "number",       "Val. reached by idle ctr at run time in 1 sec." ],
    [ OS_INT_NESTING,                  "number",       "Interrupt nesting level"                        ],
    [ OS_LOCK_NESTING,                 "number",       "Multitasking lock nesting level"                ],
    [ OS_MEM_FREE_LIST,                "address",      "Pointer to free list of memory partitions"      ],
    [ OS_PRIO_CUR,                     "number",       "Priority of current task"                       ],
    [ OS_PRIO_HIGH_RDY,                "number",       "Priority of highest priority task"              ],
    [ OS_Q_FREE_LIST,                  "address",      "Pointer to list of free QUEUE control blocks"   ],
    [ OS_RDY_GRP,                      "hex",          "Ready list group"                               ],
    [ OS_RUNNING,                      "number",       "Flag indicating that kernel is running"         ],
    [ OS_SAFETY_CRITIAL_START_FLAG,    "number",       "Safety critical flag"                           ],
    [ OS_STAT_RDY,                     "number",       "Flag indicating that the statistic task is rdy" ],
    [ OS_TASK_CTR,                     "number",       "Number of tasks created"                        ],
    [ OS_TASK_REG_NEXT_AVAIL_ID,       "number",       "Next available Task register ID"                ],
    [ OS_TCB_CUR,                      "task",         "Pointer to currently running TCB"               ],
    [ OS_TCB_FREE_LIST,                "address",      "Pointer to list of free TCBs"                   ],
    [ OS_TCB_HIGH_RDY,                 "task",         "Pointer to highest priority TCB R-to-R"         ],
    [ OS_TCB_LIST,                     "address",      "Pointer to doubly linked list of TCBs"          ],
    [ OS_TICK_STEP_STATE,              "number",       "Indicates the state of the tick step feature"   ],
    [ OS_TIME,                         "number",       "Current value of system time (in ticks)"        ],
    [ OS_TMR_FREE_LIST,                "address",      "Pointer to free list of timers"                 ],
    [ OS_TMR_FREE,                     "number",       "Number of free entries in the timer pool"       ],
    [ OS_TMR_SEM,                      "address",      "Sem. used to gain exclusive access to timers"   ],
    [ OS_TMR_SEM_SIGNAL,               "address",      "Sem. used to signal the update of timers"       ],
    [ OS_TMR_TIME,                     "number",       "Current timer time"                             ],
    [ OS_TMR_USED,                     "number",       "Number of timers used"                          ],
    # Constants
    [ OS_CPU_ARM_FP_EN,                "number",       "ARM floating point unit enable flag"            ],
    [ OS_DEBUG_EN,                     "number",       "Debug enable flag"                              ],
    [ OS_ENDLIANNESS_TEST,             "number",       "Variable to test CPU endianness"                ],
    [ OS_EVENT_EN,                     "number",       "Events enable flag"                             ],
    [ OS_EVENT_MAX,                    "number",       "Number of event control blocks"                 ],
    [ OS_EVENT_MULTI_EN,               "number",       "Events multi enable flag"                       ],
    [ OS_EVENT_NAME_EN,                "number",       "Event name enable flag"                         ],
    [ OS_EVENT_SIZE,                   "number",       "Size in Bytes of OS_EVENT"                      ],
    [ OS_EVENT_TBL_SIZE,               "number",       "Size of OSEventTbl[ ] in bytes"                 ],
    [ OS_FLAG_EN,                      "number",       "Flag groups enable flag"                        ],
    [ OS_FLAG_GRP_SIZE,                "number",       "Size in Bytes of OS_FLAG_GRP"                   ],
    [ OS_FLAG_MAX,                     "number",       "Maximum number of flags allowed"                ],
    [ OS_FLAG_NAME_EN,                 "number",       "Flag name enable flag"                          ],
    [ OS_FLAG_NODE_SIZE,               "number",       "Size in Bytes of OS_FLAG_NODE"                  ],
    [ OS_FLAG_WIDTH,                   "number",       "Width (in bytes) of OS_FLAGS"                   ],
    [ OS_LOWEST_PRIO,                  "number",       "Lowest priority task number"                    ],
    [ OS_MBOX_EN,                      "number",       "Mailbox enable flag"                            ],
    [ OS_MEM_EN,                       "number",       "Memory enable flag"                             ],
    [ OS_MEM_MAX,                      "number",       "Number of memory partitions"                    ],
    [ OS_MEM_NAME_EN,                  "number",       "Memory name enable flag"                        ],
    [ OS_MEM_SIZE,                     "number",       "Memory Partition header sine (bytes)"           ],
    [ OS_MEM_TBL_SIZE,                 "number",       "Size of memory table"                           ],
    [ OS_MULTI_EN,                     "number",       "Mutex enable flag"                              ],
    [ OS_PTR_SIZE,                     "number",       "Size in Bytes of a pointer"                     ],
    [ OS_Q_EN,                         "number",       "Queue enable flag"                              ],
    [ OS_Q_MAX,                        "number",       "Number of queues"                               ],
    [ OS_Q_SIZE,                       "number",       "Size in bytes of OS_Q structure"                ],
    [ OS_RDY_TBL_SIZE,                 "number",       "Number of bytes in the ready table"             ],
    [ OS_SEM_EN,                       "number",       "Semaphore enable flag"                          ],
    [ OS_STK_WIDTH,                    "number",       "Size in Bytes of a stack entry"                 ],
    [ OS_TASK_CREATE_EN,               "number",       "Task creation enable flag"                      ],
    [ OS_TASK_CREATE_EXT_EN,           "number",       "Task (extended) creation enable flag"           ],
    [ OS_TASK_DEL_EN,                  "number",       "Task delete enable flag"                        ],
    [ OS_TASK_IDLE_STK_SIZE,           "number",       "Idle task stack size"                           ],
    [ OS_TASK_MAX,                     "number",       "Total max. number of tasks"                     ],
    [ OS_TASK_NAME_EN,                 "number",       "Task name enable flag"                          ],
    [ OS_TASK_PROFILE_EN,              "number",       "Task profiling enable"                          ],
    [ OS_TASK_STAT_EN,                 "number",       "Statistics task enable flag"                    ],
    [ OS_TASK_STAT_STK_CHK_EN,         "number",       "Statistics task stack checking enable flag"     ],
    [ OS_TASK_STAT_STK_SIZE,           "number",       "Statistics task stack size"                     ],
    [ OS_TASK_SW_HOOK_EN,              "number",       "Task hooks enable flag"                         ],
    [ OS_TCB_PRIO_TBL_MAX,             "number",       "Number of entries in OSTCBPrioTbl[ ]"           ],
    [ OS_TCB_SIZE,                     "number",       "Size in Bytes of OS_TCB"                        ],
    [ OS_TICKS_PER_SEC,                "number",       "Ticks per second"                               ],
    [ OS_TIME_TICK_HOOK_EN,            "number",       "Timer tick hook enable"                         ],
    [ OS_TLS_TBL_SIZE,                 "number",       "Size of TLS storage"                            ],
    [ OS_TMR_CFG_MAX,                  "number",       "Max. number of timers"                          ],
    [ OS_TMR_CFG_NAME_EN,              "number",       "Timer configuration name enable flag"           ],
    [ OS_TMR_CFG_TICKS_PER_SEC,        "number",       "Timer configuration ticks per seconds"          ],
    [ OS_TMR_CFG_WHEEL_SIZE,           "number",       "Timer configuration wheel size"                 ],
    [ OS_TMR_EN,                       "number",       "Timer enable"                                   ],
    [ OS_TMR_SIZE,                     "number",       "Timer size"                                     ],
    [ OS_TMR_TBL_SIZE,                 "number",       "Timer table size"                               ],
    [ OS_TMR_WHEEL_SIZE,               "number",       "Timer wheel size"                               ],
    [ OS_TMR_WHEEL_TBL_SIZE,           "number",       "Timer wheel table size"                         ]
]

class KernelData( Table ):

    def __init__( self ):

        id = "kernel"

        fields = \
        [
            createField( id, "item",  TEXT ),
            createField( id, "value", TEXT ),
            createField( id, "desc",  TEXT )
        ]

        Table.__init__( self, id, fields )

    def readRecord( self, itemIndex, debugSession ):

        # Get item details
        itemNames = KERNEL_ITEMS[ itemIndex ][ 0 ]      # List of possible item names
        itemType  = KERNEL_ITEMS[ itemIndex ][ 1 ]      # Item format type
        itemDesc  = KERNEL_ITEMS[ itemIndex ][ 2 ]      # Item description

        # Search for item name (will fnd first on in list)
        itemName  = globGetName( itemNames, debugSession )

        if len( itemName ):

            # Read item value and format as required
            itemValue = readExpression( itemName, itemType, debugSession )

            # Value created?
            if len( itemValue ):

                # Yes, create entry in table
                cells = [ createTextCell( itemName ), createTextCell( itemValue ), createTextCell( itemDesc ) ]
                return self.createRecord( cells )

    def getRecords( self, debugSession ):

        records = [ ]

        j = len( KERNEL_ITEMS )
        for i in range( j ):
            record = self.readRecord( i, debugSession )
            if record:
                records.append( record )

        return records
