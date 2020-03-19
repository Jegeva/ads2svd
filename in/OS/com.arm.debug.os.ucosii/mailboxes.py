# Copyright (C) 2013-2014,2017 Arm Limited (or its affiliates). All rights reserved.

from osapi import *
from utils import *
from events import *

class Mailboxes( Table ):

    # Class ID
    ID = "mailboxes"

    # Column definitions - flags
    cols = \
    [
        [ OS_EVENT_NAME, MEMBER_AS_STRING      ],
        [ OS_EVENT_PTR,  MEMBER_AS_ADDRESS     ],
        [ OS_EVENT_CNT,  MEMBER_AS_NUMBER      ],
        [ OS_EVENT_GRP,  MEMBER_AS_HEX         ],
        [ OS_EVENT_TBL,  MEMBER_AS_EVENT_TASKS ]
    ]

    def __init__( self ):

        id = self.ID

        fields = [ createPrimaryField( id, OS_EVENT, TEXT ) ]
        for col in self.cols:
            fields.append( createField( id, col[ 0 ][ 0 ], TEXT ) )

        Table.__init__( self, id, fields )

    def readMailbox( self, id, members, debugSession ):

        cells = [ createTextCell( id ) ]
        for col in self.cols:
            cells.append( createTextCell( getMemberValue( members, col[ 0 ], col[ 1 ], debugSession ) ) )

        return self.createRecord( cells )

    def getRecords( self, debugSession ):

        records = [ ]

        if isOSRunning( debugSession ):

            osEventTbl = globGetName( OS_EVENT_TBL, debugSession )
            if osEventTbl:

                i = 0;
                mailboxes = debugSession.evaluateExpression( osEventTbl ).getArrayElements( )

                for mailbox in mailboxes:

                    members = mailbox.getStructureMembers( )

                    osEventTypeMember = getMemberName( OS_EVENT_TYPE, members )
                    if not osEventTypeMember:
                        break

                    if members[ osEventTypeMember ].readAsNumber( ) == Events.OS_EVENT_TYPE_MBOX:

                        eventPtr = debugSession.evaluateExpression( "&" + osEventTbl + "[" + str( i ) + "]" )
                        if eventPtr != 0:
                            id = eventPtr.readAsAddress( ).toString( )
                            records.append( self.readMailbox( id, members, debugSession ) )

                    i = i + 1

        return records
