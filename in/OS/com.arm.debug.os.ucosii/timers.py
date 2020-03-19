# Copyright (C) 2013-2014,2017 Arm Limited (or its affiliates). All rights reserved.

from osapi import *
from utils import *
from events import *

class Timers( Table ):

    # Class ID
    ID = "timers"

    # Timer structure field names (if there are multiple possible names, add each one to the list)
    # Note: the first name must match the column heading in messages.properties file

    # Column definitions
    cols = \
    [
        [ OS_TMR_NAME,        MEMBER_AS_STRING      ],
        [ OS_TMR_CALLBACK,    MEMBER_AS_ADDRESS     ],
        [ OS_TMR_CALLBACKARG, MEMBER_AS_CSTRING     ],
        [ OS_TMR_NEXT,        MEMBER_AS_ADDRESS     ],
        [ OS_TMR_PREV,        MEMBER_AS_ADDRESS     ],
        [ OS_TMR_MATCH,       MEMBER_AS_HEX         ],
        [ OS_TMR_DLY,         MEMBER_AS_NUMBER      ],
        [ OS_TMR_PERIOD,      MEMBER_AS_HEX         ],
        [ OS_TMR_OPT,         MEMBER_AS_TIMER_OPTS  ],
        [ OS_TMR_STATE,       MEMBER_AS_TIMER_STATE ]
    ]

    def __init__( self ):

        id = self.ID

        fields = [ createPrimaryField( id, OS_TMR, TEXT ) ]

        for col in self.cols:
            fields.append( createField( id, col[ 0 ][ 0 ], TEXT ) )

        Table.__init__( self, id, fields )

    # read timer details
    def readTimer( self, id, members, debugSession ):

        cells = [ createTextCell( id ) ]

        for col in self.cols:
            cells.append( createTextCell( getMemberValue( members, col[ 0 ], col[ 1 ], debugSession ) ) )

        return self.createRecord( cells )

    # read timers
    def getRecords( self, debugSession ):

        # no records
        records = [ ]

        # make sure uCOS-II is running
        if isOSRunning( debugSession ):

            # check if timers are enabled, test for .OSTmrTbl
            osTmrTbl = globGetName( OS_TMR_TBL, debugSession )
            if osTmrTbl:

                # timer index number
                i = 0;

                # get timer table
                timers = debugSession.evaluateExpression( osTmrTbl ).getArrayElements( )

                # step through timer table
                for timer in timers:

                    # get all members of timer structure
                    members = timer.getStructureMembers( )

                    osTmrTypeMember = getMemberName( OS_TMR_TYPE, members )
                    if not osTmrTypeMember:
                        break

                    # all timers should have type as OS_TMR_TYPE
                    if members[ osTmrTypeMember ].readAsNumber( ) == Events.OS_EVENT_TYPE_TMR:

                        # get a pointer to timer record
                        timerPtr = debugSession.evaluateExpression( "&"+ osTmrTbl + "[" + str( i ) + "]" )
                        if timerPtr != 0:

                            # get address of timer and use as id
                            id = timerPtr.readAsAddress( ).toString( )

                            # populate timer details
                            records.append( self.readTimer( id, members, debugSession ) )

                    # keep track of number of timers
                    i = i + 1

        # Here is complete timer details
        return records
