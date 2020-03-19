# Copyright (C) 2013-2014,2017 Arm Limited (or its affiliates). All rights reserved.

# Import all!
from osapi import *
from utils import *
from globs import *

# OS Events Class Definition
class Events( Table ):

    # Class ID
    ID = "events"

    # Event types
    OS_EVENT_TYPE_ALL       =  -1
    OS_EVENT_TYPE_UNUSED    =   0
    OS_EVENT_TYPE_MBOX      =   1
    OS_EVENT_TYPE_Q         =   2
    OS_EVENT_TYPE_SEM       =   3
    OS_EVENT_TYPE_MUTEX     =   4
    OS_EVENT_TYPE_FLAG      =   5
    OS_EVENT_TYPE_TMR       = 100

    # Column definitions
    cols = \
    [
        [ OS_EVENT_NAME, MEMBER_AS_STRING      ],
        [ OS_EVENT_TYPE, MEMBER_AS_EVENT_TYPE  ],
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

    def readEvent( self, id, members, debugSession ):

        cells = [ createTextCell( id ) ]
        for col in self.cols:
            cells.append( createTextCell( getMemberValue( members, col[ 0 ], col[ 1 ], debugSession ) ) )

        return self.createRecord( cells )

    def readEvents( self, eventType, debugSession ):

        records = [ ]

        osEventTbl = globGetName( OS_EVENT_TBL, debugSession )
        if osEventTbl:

            i = 0;
            events = debugSession.evaluateExpression( osEventTbl ).getArrayElements( )
            for event in events:

                members = event.getStructureMembers( )

                osEventTypeMember = getMemberName( OS_EVENT_TYPE, members )
                if not osEventTypeMember:
                    break

                if members[ osEventTypeMember ].readAsNumber( ) == eventType or eventType == self.OS_EVENT_TYPE_ALL:

                    eventPtr = debugSession.evaluateExpression( "&" + osEventTbl + "[" + str( i ) + "]" )
                    id = eventPtr.readAsAddress( ).toString( )
                    records.append( self.readEvent( id, members, debugSession ) )

                i = i + 1

        return records

    def getRecords( self, debugSession ):

        if isOSRunning( debugSession ):
            return self.readEvents( self.OS_EVENT_TYPE_ALL, debugSession )
