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

# Mailbox class
class Mailboxes( Table ):

    # Class ID
    ID = "mailboxes"

    # Column definitions
    cols = \
    [
        [ OS_MAILBOX_PNEXT,       FORMAT_ADDRESS_STR  ],
        [ OS_MAILBOX_PDATA,       FORMAT_ADDRESS_STR  ],
        [ OS_MAILBOX_NOFMSG,      FORMAT_NUMBER_STR   ],
        [ OS_MAILBOX_MAXMSG,      FORMAT_NUMBER_STR   ],
        [ OS_MAILBOX_IRD,         FORMAT_NUMBER_STR   ],
        [ OS_MAILBOX_SIZEOFMSG,   FORMAT_NUMBER_STR   ],
        [ OS_MAILBOX_ID,          FORMAT_NUMBER_STR   ]
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
        fields = [ createPrimaryField( cid, OS_MAILBOX, TEXT ) ]

        # Create mailbox columns
        for col in self.cols:
            fields.append( createField( cid, col[ 0 ], TEXT ) )

        # Create waiting list columns
        for colWlo in self.colsWlo:
            fields.append( createField( cid, OS_MAILBOX_WAITOBJ + colWlo[ 0 ], TEXT ) )

        # Create table
        Table.__init__( self, cid, fields )

    # Read mailbox details
    def readMailbox( self, cid, members, debugSession ):

        # Populate primary field
        cells = [ createTextCell( cid ) ]

        # Populate mailbox fields
        for col in self.cols:
            cells.append( createTextCell( getMemberValue( members, col[ 0 ], col[ 1 ], debugSession ) ) )

        # Populate waiting list fields
        waitListMembers = members[ OS_MAILBOX_WAITOBJ ].getStructureMembers( )
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

    # Read mailboxes
    def getRecords( self, debugSession ):

        # Blank records
        records = [ ]

        # Make sure OS is up and running
        if isOSRunning( debugSession ):

            # This points to the start of a linked list of all mailboxes
            pMailbox = debugSession.evaluateExpression( OS_PMAILBOX )

            # Get all mailboxes
            while pMailbox.readAsNumber( ):

                # Use address of OS_MAILBOX as its id
                pMailboxId = pMailbox.readAsAddress( ).toString( )

                # Get all structure members of OS_MAILBOX
                pMailboxMembers = pMailbox.dereferencePointer( ).getStructureMembers( )

                # Create mailbox record and add it to the list
                records.append( self.readMailbox( pMailboxId, pMailboxMembers, debugSession ) )

                # Get pointer to next mailbox
                pMailbox = pMailboxMembers[ OS_MAILBOX_PNEXT ]

        # Mailbox records
        return records
