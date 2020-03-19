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

# Queues Class
class Queues( Table ):

    # Class ID
    ID = "queues"

    # Column definitions
    cols = \
    [
        [ OS_Q_PNEXT,           FORMAT_ADDRESS_STR  ],
        [ OS_Q_PDATA,           FORMAT_ADDRESS_STR  ],
        [ OS_Q_SIZE,            FORMAT_NUMBER_STR   ],
        [ OS_Q_MSGCNT,          FORMAT_NUMBER_STR   ],
        [ OS_Q_OFFFIRST,        FORMAT_NUMBER_STR   ],
        [ OS_Q_OFFLAST,         FORMAT_NUMBER_STR   ],
        [ OS_Q_INUSE,           FORMAT_NUMBER_STR   ],
        [ OS_Q_INPROGRESSCNT,   FORMAT_NUMBER_STR   ],
        [ OS_Q_ID,              FORMAT_NUMBER_STR   ]
    ]

    # Column definitions (Wait list object)
    colsWlo = \
    [
        [ OS_WAIT_LIST_PNEXT,       FORMAT_ADDRESS_STR  ],
        [ OS_WAIT_LIST_PPREV,       FORMAT_ADDRESS_STR  ],
        [ OS_WAIT_LIST_PWAITOBJ,    FORMAT_ADDRESS_STR  ],
        [ OS_WAIT_LIST_PTASK,       FORMAT_TASK_NAME    ]
    ]

    # Constructor
    def __init__( self ):

        # Id name
        cid = self.ID

        # Create primary field
        fields = [ createPrimaryField( cid, OS_Q, TEXT ) ]

        # Create queue columns
        for col in self.cols:
            fields.append( createField( cid, col[ 0 ], TEXT ) )

        # Create waiting list columns
        for colWlo in self.colsWlo:
            fields.append( createField( cid, OS_Q_WAITOBJ + colWlo[ 0 ], TEXT ) )

        # Create table
        Table.__init__( self, cid, fields )

    # Read queue details
    def readQueue( self, cid, members, debugSession ):

        # Populate primary field
        cells = [ createTextCell( cid ) ]

        # Populate queue fields
        for col in self.cols:
            cells.append( createTextCell( getMemberValue( members, col[ 0 ], col[ 1 ], debugSession ) ) )

        # Populate waiting list fields
        waitListMembers = members[ OS_Q_WAITOBJ ].getStructureMembers( )
        waitListPtr = waitListMembers[ OS_WAIT_OBJ_PWAITLIST ]

        # Wait list configured?
        if waitListPtr.readAsNumber( ) > 0:
            waitListMembers = waitListPtr.dereferencePointer( ).getStructureMembers( )
            for colWlo in self.colsWlo:
                cells.append( createTextCell( getMemberValue( waitListMembers, colWlo[ 0 ], colWlo[ 1 ], debugSession ) ) )
        # No, just populate dummy values
        else:
            for colWlo in self.colsWlo:
                cells.append( createTextCell( "N/A" ) )

        # Populated record
        return self.createRecord( cells )

    # Read queues
    def getRecords( self, debugSession ):

        # Blank records
        records = [ ]

        # Make sure OS is up and running
        if isOSRunning( debugSession ):

            # This points to the start of a linked list of all queues
            pQueue = debugSession.evaluateExpression( OS_PQHEAD )

            # Get all queues
            while pQueue.readAsNumber( ):

                # Use address of OS_Q as its id
                pQueueId = pQueue.readAsAddress( ).toString( )

                # Get all structure members of OS_Q
                pQueueMembers = pQueue.dereferencePointer( ).getStructureMembers( )

                # Create Queue record and add it to the list
                records.append( self.readQueue( pQueueId, pQueueMembers, debugSession ) )

                # Get pointer to next Queue
                pQueue = pQueueMembers[ OS_RSEMA_PNEXT ]

        # Queue records
        return records
