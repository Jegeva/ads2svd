# Copyright (C) 2013-2014,2017 Arm Limited (or its affiliates). All rights reserved.

from osapi import *
from utils import *
from events import *

class Queues( Table ):

    # Class ID
    ID = "queues"

    # Column definitions - events
    evCols = \
    [
        [ OS_EVENT_NAME, MEMBER_AS_STRING  ],
        [ OS_EVENT_PTR,  MEMBER_AS_ADDRESS ]
    ]

    # Column definitions - queues
    quCols = \
    [
        [ OS_Q_PTR,     MEMBER_AS_ADDRESS ],
        [ OS_Q_START,   MEMBER_AS_ADDRESS ],
        [ OS_Q_END,     MEMBER_AS_ADDRESS ],
        [ OS_Q_IN,      MEMBER_AS_ADDRESS ],
        [ OS_Q_OUT,     MEMBER_AS_ADDRESS ],
        [ OS_Q_SIZE,    MEMBER_AS_ADDRESS ],
        [ OS_Q_ENTRIES, MEMBER_AS_ADDRESS ]
    ]

    def __init__( self ):

        id = self.ID

        fields = [ createPrimaryField( id, OS_EVENT, TEXT ) ]

        for col in self.evCols:
            fields.append( createField( id, col[ 0 ][ 0 ], TEXT ) )

        for col in self.quCols:
            fields.append( createField( id, col[ 0 ][ 0 ], TEXT ) )

        Table.__init__( self, id, fields )

    def readQueue( self, id, members, debugSession ):

        quMembers = [ ]
        osEventPtr = int( getMemberValue( members, OS_EVENT_PTR, MEMBER_AS_NUMBER, debugSession, "0" ) )
        if osEventPtr != 0:
            queuePtr = debugSession.evaluateExpression( "(" + OS_Q + "*)" + str( osEventPtr ) )
            quMembers = queuePtr.dereferencePointer( ).getStructureMembers( )

        cells = [ createTextCell( id ) ]

        for col in self.evCols:
            cells.append( createTextCell( getMemberValue( members, col[ 0 ], col[ 1 ], debugSession ) ) )

        for col in self.quCols:
                cells.append( createTextCell( getMemberValue( quMembers, col[ 0 ], col[ 1 ], debugSession ) ) )

        return self.createRecord( cells )

    def getRecords( self, debugSession ):

        records = [ ]

        if isOSRunning( debugSession ):

            osEventTbl = globGetName( OS_EVENT_TBL, debugSession )
            if osEventTbl:

                i = 0;
                events = debugSession.evaluateExpression( osEventTbl ).getArrayElements( )

                for event in events:

                    members = event.getStructureMembers( )

                    osEventTypeMember = getMemberName( OS_EVENT_TYPE, members )
                    if not osEventTypeMember:
                        break

                    if members[ osEventTypeMember ].readAsNumber( ) == Events.OS_EVENT_TYPE_Q:

                        eventPtr = debugSession.evaluateExpression( "&" + osEventTbl + "[" + str( i ) + "]" )
                        if eventPtr != 0:
                            id = eventPtr.readAsAddress( ).toString( )
                            records.append( self.readQueue( id, members, debugSession ) )

                    i = i + 1

        return records
