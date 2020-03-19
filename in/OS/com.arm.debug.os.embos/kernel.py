################################################################################
#
# Copyright (C) 2014,2017 Arm Limited (or its affiliates). All rights reserved.
#
# embOS - 3.88c ARM Cortex M / 3.88h ARM Cortex A
#
#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

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
    [ [ OS_VERSION                                                   ], FORMAT_NUMBER_STR,  "OS version number"                                          ],
    [ [ OS_GLOBAL, OS_GLOBALS_COUNTERS, "Cnt", OS_COUNTERS_REGION    ], FORMAT_NUMBER_STR,  "Region count"                                               ],
    [ [ OS_GLOBAL, OS_GLOBALS_COUNTERS, "Cnt", OS_COUNTERS_DI        ], FORMAT_NUMBER_STR,  "DI count"                                                   ],
    [ [ OS_GLOBAL, OS_GLOBALS_PENDING, "Flag", OS_PENDING_ROUNDROBIN ], FORMAT_NUMBER_STR,  "Round robin pending"                                        ],
    [ [ OS_GLOBAL, OS_GLOBALS_PENDING, "Flag", OS_PENDING_TASKSWITCH ], FORMAT_NUMBER_STR,  "Task switch pending"                                        ],
    [ [ OS_GLOBAL, OS_GLOBALS_PCURRENTTASK                           ], FORMAT_ADDRESS_STR, "Pointer to current task"                                    ],
    [ [ OS_GLOBAL, OS_GLOBALS_IPL_DI                                 ], FORMAT_NUMBER_STR,  "Interrupt priority disbale"                                 ],
    [ [ OS_GLOBAL, OS_GLOBALS_IPL_EI                                 ], FORMAT_NUMBER_STR,  "Interrupt priority enable"                                  ],
    [ [ OS_GLOBAL, OS_GLOBALS_PTASK                                  ], FORMAT_ADDRESS_STR, "Linked list of all Tasks"                                   ],
    [ [ OS_GLOBAL, OS_GLOBALS_PACTIVETASK                            ], FORMAT_ADDRESS_STR, "Pointer to active task"                                     ],
    [ [ OS_GLOBAL, OS_GLOBALS_PTIMER                                 ], FORMAT_ADDRESS_STR, "Linked list of all active timers"                           ],
    [ [ OS_GLOBAL, OS_GLOBALS_PCURRENTTIMER                          ], FORMAT_ADDRESS_STR, "Actual expired timer which called callback"                 ],
    [ [ OS_GLOBAL, OS_GLOBALS_PFCHECKTIMER                           ], FORMAT_ADDRESS_STR, "Timer handler function, set when OS_StartTimer() is called" ],
    [ [ OS_GLOBAL, OS_GLOBALS_TIME                                   ], FORMAT_NUMBER_STR,  "Current time"                                               ],
    [ [ OS_GLOBAL, OS_GLOBALS_TIMEDEX                                ], FORMAT_NUMBER_STR,  "Current time ex"                                            ],
    [ [ OS_GLOBAL, OS_GLOBALS_TIMESLICE                              ], FORMAT_NUMBER_STR,  "Current time slice"                                         ],
    [ [ OS_GLOBAL, OS_GLOBALS_TIMESLICEATSTART                       ], FORMAT_NUMBER_STR,  "Time slice at start"                                        ],
    [ [ OS_INTMSINC                                                  ], FORMAT_NUMBER_STR,  ""                                                           ],
    [ [ OS_STATUS                                                    ], FORMAT_ERROR_TEXT,  "OS error code"                                              ],
    [ [ OS_RUNNING                                                   ], FORMAT_NUMBER_STR,  "OS running flag"                                            ],
    [ [ OS_INITIALSUSPENDCNT                                         ], FORMAT_NUMBER_STR,  "Inital task suspend count"                                  ],
    [ [ OS_ININT                                                     ], FORMAT_NUMBER_STR,  "Curent interrupt nesting count"                             ],
    [ [ OS_TICKSTEP                                                  ], FORMAT_NUMBER_STR,  "Tick step enable flag"                                      ],
    [ [ OS_TICKSTEPTIME                                              ], FORMAT_NUMBER_STR,  "Tick step time"                                             ],
    [ [ OS_TICKSPERMS                                                ], FORMAT_NUMBER_STR,  "Tick step per ms"                                           ],
    [ [ OS_INTTICKSINC                                               ], FORMAT_NUMBER_STR,  "Tick step increment"                                        ],
    [ [ OS_TS_EXECSTART                                              ], FORMAT_NUMBER_STR,  "Time stamp execution time"                                  ],
    [ [ PROFILINGON                                                  ], FORMAT_NUMBER_STR,  "Profiling enable flag"                                      ],
    [ [ OS_INTIMER                                                   ], FORMAT_NUMBER_STR,  "In a timer flag"                                            ],
    [ [ OS_INITCALLED                                                ], FORMAT_NUMBER_STR,  "Init has been called"                                       ],
    [ [ OS_POWER_LEVELS + "[0]"                                      ], FORMAT_NUMBER_STR,  "Power level 0"                                              ],
    [ [ OS_POWER_LEVELS + "[1]"                                      ], FORMAT_NUMBER_STR,  "Power level 1"                                              ],
    [ [ OS_POWER_LEVELS + "[2]"                                      ], FORMAT_NUMBER_STR,  "Power level 2"                                              ],
    [ [ OS_POWER_LEVELS + "[3]"                                      ], FORMAT_NUMBER_STR,  "Power level 3"                                              ],
    [ [ OS_POWER_LEVELS + "[4]"                                      ], FORMAT_NUMBER_STR,  "Power level 4"                                              ],
    [ [ OS_CPU_LOAD                                                  ], FORMAT_NUMBER_STR,  "CPU load %"                                                 ],
    [ [ OS_IDLECNT                                                   ], FORMAT_NUMBER_STR,  "Idle count"                                                 ],
    [ [ OS_PRSEMA                                                    ], FORMAT_ADDRESS_STR, "Linked list of all resource semaphores"                     ],
    [ [ OS_PQHEAD                                                    ], FORMAT_ADDRESS_STR, "Linked list of all queues"                                  ],
    [ [ OS_PMAILBOX                                                  ], FORMAT_ADDRESS_STR, "Linked list of all mailboxes"                               ],
    [ [ OS_PCSEMA                                                    ], FORMAT_ADDRESS_STR, "Linked list of all counting semaphores"                     ],
    [ [ OS_PMEMF                                                     ], FORMAT_ADDRESS_STR, "Linked list of all fixed sized memory pools"                ],
    [ [ OS_PTICKHOOK                                                 ], FORMAT_ADDRESS_STR, "Linked list of all tick hook functions"                     ],
    [ [ OS_PTLS                                                      ], FORMAT_NUMBER_STR,  "Global pointer to thread local storage"                     ],
    [ [ OS_PFONTERMINATE                                             ], FORMAT_ADDRESS_STR, "Task terminate hook function"                               ],
    [ [ OS_SYSSTACKBASEADDR                                          ], FORMAT_ADDRESS_STR, "System stack base address"                                  ],
    [ [ OS_SYSSTACKSIZE                                              ], FORMAT_NUMBER_STR,  "System stack size"                                          ],
    [ [ OS_SYSSTACKLIMIT                                             ], FORMAT_ADDRESS_STR, "System stack limit"                                         ],
    [ [ SYSTEMCORECLOCK                                              ], FORMAT_NUMBER_STR,  "System core frequency"                                      ],
    [ [ STACK_MEM                                                    ], FORMAT_ADDRESS_STR, "Startup stack memory"                                       ],
    [ [ STACK_SIZE                                                   ], FORMAT_NUMBER_STR,  "Startup stack memory size"                                  ],
    [ [ STACK_LIMIT                                                  ], FORMAT_ADDRESS_STR, "Startup stack memory limit"                                 ],
    [ [ VECTORS                                                      ], FORMAT_ADDRESS_STR, "Vectors"                                                    ],
    [ [ OS_JLINKMEM_BUFFERSIZE                                       ], FORMAT_NUMBER_STR,  "JLink interface buffer size"                                ],
    [ [ OS_COUNTOFTRACEBUFFER                                        ], FORMAT_NUMBER_STR,  "Trace buffer size"                                          ],
    [ [ OS_PTRACEBUFFER                                              ], FORMAT_ADDRESS_STR, "Trace buffer address"                                       ],
    [ [ OS_COM_OUTBUFFERCNT                                          ], FORMAT_ADDRESS_STR, "Output buffer count"                                        ],
    [ [ OS_COM_STRINGLEN                                             ], FORMAT_NUMBER_STR,  "Output buffer string length"                                ]
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

        try:

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
        except:

            # Expression evaluation failed, field must not be present
            pass

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
