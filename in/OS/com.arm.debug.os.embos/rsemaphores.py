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

# Semaphore (Resource) Class
class Rsemaphores( Table ):

    # Class ID
    ID = "rsemaphores"

    # Column definitions
    cols = \
    [
        [ OS_RSEMA_PTASK,       FORMAT_TASK_NAME    ],
        [ OS_RSEMA_USECNT,      FORMAT_NUMBER_STR   ],
        [ OS_RSEMA_PNEXT,       FORMAT_ADDRESS_STR  ],
        [ OS_RSEMA_ID,          FORMAT_NUMBER_STR   ]
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
        fields = [ createPrimaryField( cid, OS_RSEMA, TEXT ) ]

        # Create sema4 columns
        for col in self.cols:
            fields.append( createField( cid, col[ 0 ], TEXT ) )

        # Create waiting list columns
        for colWlo in self.colsWlo:
            fields.append( createField( cid, OS_RSEMA_WAITOBJ + colWlo[ 0 ], TEXT ) )

        # Create table
        Table.__init__( self, cid, fields )

    # Read sema4 details
    def readSema4( self, cid, members, debugSession ):

        # Populate primary field
        cells = [ createTextCell( cid ) ]

        # Populate sema4 fields
        for col in self.cols:
            cells.append( createTextCell( getMemberValue( members, col[ 0 ], col[ 1 ], debugSession ) ) )

        # Populate waiting list fields
        waitListMembers = members[ OS_RSEMA_WAITOBJ ].getStructureMembers( )
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

    # Read sems4's
    def getRecords( self, debugSession ):

        # Blank records
        records = [ ]

        # Make sure OS is up and running
        if isOSRunning( debugSession ):

            # This points to the start of a linked list of all resource sema4's
            pSema4r = debugSession.evaluateExpression( OS_PRSEMA )

            # Get all sema4's
            while pSema4r.readAsNumber( ):

                # Use address of OS_RSEMA as its id
                pSema4rId = pSema4r.readAsAddress( ).toString( )

                # Get all structure members of OS_RSEMA
                pSema4rMembers = pSema4r.dereferencePointer( ).getStructureMembers( )

                # Create sema4r record and add it to the list
                records.append( self.readSema4( pSema4rId, pSema4rMembers, debugSession ) )

                # Get pointer to next sema4r
                pSema4r = pSema4rMembers[ OS_RSEMA_PNEXT ]

        # Sema4 records
        return records
