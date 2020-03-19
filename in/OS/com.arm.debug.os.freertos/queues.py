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

# Queues class
class Queues( Table ):

    # Class ID
    ID = "queues"

    # Column definitions (Queue Item)
    cols_item = \
    [
        [ QUEUE_I_PC_QUEUE_NAME,            FORMAT_STRING,      TEXT    ],
        [ QUEUE_I_X_HANDLE,                 FORMAT_ADDRESS_STR, TEXT    ]
    ]

    # Column definitions (Queue Structure)
    cols_st = \
    [
        [ QUEUE_UX_QUEUE_NUMBER,            FORMAT_NUMBER_STR,  TEXT    ],
        [ QUEUE_UC_QUEUE_TYPE,              FORMAT_QUEUE_TYPE,  TEXT    ],
        [ QUEUE_UX_LENGTH,                  FORMAT_NUMBER_STR,  TEXT    ],
        [ QUEUE_UX_MESSAGES_WAITING,        FORMAT_NUMBER_STR,  TEXT    ],
        [ QUEUE_UX_ITEM_SIZE,               FORMAT_NUMBER_STR,  TEXT    ],
        [ QUEUE_X_RX_LOCK,                  FORMAT_NUMBER_STR,  TEXT    ],
        [ QUEUE_X_TX_LOCK,                  FORMAT_NUMBER_STR,  TEXT    ],
        [ QUEUE_PC_HEAD,                    FORMAT_ADDRESS_STR, TEXT    ],
        [ QUEUE_PC_TAIL,                    FORMAT_ADDRESS_STR, TEXT    ],
        [ QUEUE_PC_WRITE_TO,                FORMAT_ADDRESS_STR, TEXT    ],
        [ QUEUE_PX_QUEUE_SET_CONTAINER,     FORMAT_ADDRESS_STR, TEXT    ],
        [ QUEUE_X_TASKS_WAITING_TO_SEND,    FORMAT_TASK_LIST,   TEXT    ],
        [ QUEUE_X_TASKS_WAITING_TO_RECEIVE, FORMAT_TASK_LIST,   TEXT    ]
    ]

    # Column definitions (Queue Structure 2)
    cols_st2 = \
    [
        [ QUEUE_PC_READ_FROM,               FORMAT_ADDRESS_STR, TEXT    ],
    ]

    # Class constructor
    def __init__( self ):

        # Class ID
        cid = self.ID

        # Create primary field
        fields = [ createPrimaryField( cid, QUEUE, TEXT ) ]

        # Create queue item columns
        for col in self.cols_item:
            fields.append( createField( cid, col[ 0 ], col[ 2 ] ) )

        # Create queue structure columns
        for col in self.cols_st:
            fields.append( createField( cid, col[ 0 ], col[ 2 ] ) )
        for col in self.cols_st2:
            fields.append( createField( cid, col[ 0 ], col[ 2 ] ) )

        # Create table
        Table.__init__( self, cid, fields )

    # Read queue
    def readQueue( self, cid, members, queueStMembers, debugSession ):

        # Populate primary field
        cells = [ createTextCell( cid ) ]

        # Populate queue fields
        for col in self.cols_item:
            createCell( cells, members, col[ 0 ], col[ 1 ], col[ 2 ], debugSession )

        # Populate queue fields
        for col in self.cols_st:
            createCell( cells, queueStMembers, col[ 0 ], col[ 1 ], col[ 2 ], debugSession )

        # The following items are in a 'union' and are displayed differently depending on the type of object in the queue
        if "u" in queueStMembers:
            queueSt2Members = queueStMembers[ "u" ].getStructureMembers( )
            queueType = queueStMembers[ QUEUE_UC_QUEUE_TYPE ].readAsNumber( )
            createCell( cells, queueSt2Members, self.cols_st2[ 0 ][ 0 ], self.cols_st2[ 0 ][ 1 ], self.cols_st2[ 0 ][ 2 ], debugSession )
        else:
            cells.append( createTextCell( "N/A" ) )

        # Populated record
        return self.createRecord( cells )

    # Get queues
    def getRecords( self, debugSession ):

        # Blank records
        records = [ ]

        # Make sure queue registry is present?
        if debugSession.symbolExists( X_QUEUE_REGISTRY ):

            # Get items in the registry
            queueItems = debugSession.evaluateExpression( X_QUEUE_REGISTRY ).getArrayElements( )

            # Process all items
            for queueItem in queueItems:

                # The address of the queue item is used as the ID
                queueItemId = hex( addressExprsToLong( queueItem ) )

                # Get all structure members
                queueItemMembers = queueItem.getStructureMembers( )

                # Get the handle (pointer) to actual object referenced by the queue item
                queueItemHandle = queueItemMembers[ QUEUE_I_X_HANDLE ]

                # Make sure handle is valid
                if queueItemHandle.readAsNumber( ) > 0:

                    # Now get queue structure
                    queueSt = queueItemHandle.dereferencePointer( QUEUE + "*" )

                    # Finally get its members
                    queueStMembers = queueSt.getStructureMembers( )

                    # Only show queues
                    if queueStMembers[ QUEUE_PC_HEAD ].readAsNumber( ) and queueStMembers[ QUEUE_UX_ITEM_SIZE ].readAsNumber( ):

                        # Read queue object and add to records
                        records.append( self.readQueue( queueItemId, queueItemMembers, queueStMembers, debugSession ) )

        # All queue items
        return records
