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

# Memory Pool Class
class Mempools( Table ):

    # Class ID
    ID = "mempools"

    # Column definitions
    cols = \
    [
        [ OS_MEMF_PNEXT,           FORMAT_ADDRESS_STR  ],
        [ OS_MEMF_PPOOL,           FORMAT_ADDRESS_STR  ],
        [ OS_MEMF_NUMBLOCKS,       FORMAT_NUMBER_STR   ],
        [ OS_MEMF_BLOCKSIZE,       FORMAT_NUMBER_STR   ],
        [ OS_MEMF_NUMFREEBLOCKS,   FORMAT_NUMBER_STR   ],
        [ OS_MEMF_MAXUSED,         FORMAT_NUMBER_STR   ],
        [ OS_MEMF_PFREE,           FORMAT_ADDRESS_STR  ],
        [ OS_MEMF_ID,              FORMAT_NUMBER_STR   ]
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
        fields = [ createPrimaryField( cid, OS_MEMF, TEXT ) ]

        # Create memory pool columns
        for col in self.cols:
            fields.append( createField( cid, col[ 0 ], TEXT ) )

        # Create waiting list columns
        for colWlo in self.colsWlo:
            fields.append( createField( cid, OS_MEMF_WAITOBJ + colWlo[ 0 ], TEXT ) )

        # Create table
        Table.__init__( self, cid, fields )

    # Read pool details
    def readPool( self, cid, members, debugSession ):

        # Populate primary field
        cells = [ createTextCell( cid ) ]

        # Populate pool fields
        for col in self.cols:
            cells.append( createTextCell( getMemberValue( members, col[ 0 ], col[ 1 ], debugSession ) ) )

        # Populate waiting list fields
        waitListMembers = members[ OS_MEMF_WAITOBJ ].getStructureMembers( )
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

    # Read memory pools
    def getRecords( self, debugSession ):

        # Blank records
        records = [ ]

        # Make sure OS is up and running
        if isOSRunning( debugSession ):

            # This points to the start of a linked list of all memory pools
            pPool = debugSession.evaluateExpression( OS_PMEMF )

            # Get all pools
            while pPool.readAsNumber( ):

                # Use address of OS_MEMF as its id
                pPoolId = pPool.readAsAddress( ).toString( )

                # Get all structure members of OS_MEMF
                pPoolMembers = pPool.dereferencePointer( ).getStructureMembers( )

                # Create memory pool record and add it to the list
                records.append( self.readPool( pPoolId, pPoolMembers, debugSession ) )

                # Get pointer to next Queue
                pPool = pPoolMembers[ OS_MEMF_PNEXT ]

        # Pool records
        return records
