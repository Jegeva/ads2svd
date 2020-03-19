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

# Timers Class
class Timers( Table ):

    # Class ID
    ID = "timers"

    # Column definitions
    cols = \
    [
        [ OS_TIMER_PNEXT,       FORMAT_ADDRESS_STR  ],
        [ OS_TIMER_HOOK,        FORMAT_ADDRESS_STR  ],
        [ OS_TIMER_TIME,        FORMAT_NUMBER_STR   ],
        [ OS_TIMER_PERIOD,      FORMAT_NUMBER_STR   ],
        [ OS_TIMER_ACTIVE,      FORMAT_NUMBER_STR   ],
        [ OS_TIMER_ID,          FORMAT_NUMBER_STR   ]
    ]

    # Column definitions (Ex timer)
    colsEx = \
    [
        [ OS_TIMER_EX_PFUSER,   FORMAT_ADDRESS_STR  ],
        [ OS_TIMER_EX_PDATA,    FORMAT_ADDRESS_STR  ]
    ]

    # Constructor
    def __init__( self ):

        # Id name
        cid = self.ID

        # Create primary field
        fields = [ createPrimaryField( cid, OS_TIMER, TEXT ) ]

        # Create timer columns
        for col in self.cols:
            fields.append( createField( cid, col[ 0 ], TEXT ) )

        # Create timer (extended) columns
        for colEx in self.colsEx:
            fields.append( createField( cid, colEx[ 0 ], TEXT ) )

        # Create table
        Table.__init__( self, cid, fields )

    # Read timer details
    def readTimer( self, timer, members, debugSession ):

        # Populate primary field
        cells = [ createTextCell( timer.readAsAddress().toString( ) ) ]

        # Populate timer fields
        for col in self.cols:
            cells.append( createTextCell( getMemberValue( members, col[ 0 ], col[ 1 ], debugSession ) ) )

        # Determine if this is an extended timer
        hookFunctionAddr = members[ OS_TIMER_HOOK ].readAsNumber( )

        # Extended timer function callback
        timerExFunc = '"OSTIMERX.c"::_OS_cbTimerEx'

        # Make sure function exists
        if debugSession.symbolExists( timerExFunc ):

            # Get address of function
            timerExFuncAddr = debugSession.evaluateExpression( timerExFunc ).getLocationAddress( ).getLinearAddress( )

            # If this points to hook function then it must be an extended timer!
            if ( timerExFuncAddr >= ( hookFunctionAddr - 1 ) ) and ( timerExFuncAddr <= ( hookFunctionAddr + 1 ) ):

                # Get pointer to timer structure
                timerPtr = timer.readAsNumber( )

                # Cast this to an extended timer
                timer = debugSession.evaluateExpression( "(OS_TIMER_EX*)" + str( timerPtr ) )

                # Get structure members
                members = timer.dereferencePointer( ).getStructureMembers( )

        # Populate timer (possibility extended) fields
        for colEx in self.colsEx:
            cells.append( createTextCell( getMemberValue( members, colEx[ 0 ], colEx[ 1 ], debugSession ) ) )

        # Populated record
        return self.createRecord( cells )

    # Read timers
    def getRecords( self, debugSession ):

        # Blank records
        records = [ ]

        # Make sure OS is up and running
        if isOSRunning( debugSession ):

            osGlobal = debugSession.evaluateExpression( OS_GLOBAL )
            osGlobalMembers = osGlobal.getStructureMembers( )

            if OS_GLOBALS_PTIMER in osGlobalMembers:

                # This points to the start of a linked list of all timers
                pTimer = osGlobalMembers[ OS_GLOBALS_PTIMER ]

                # Get all timers
                while pTimer.readAsNumber( ):

                    # Get timer members
                    pTimerMembers = pTimer.dereferencePointer( ).getStructureMembers( )

                    # Create timer record and add to list
                    records.append( self.readTimer( pTimer, pTimerMembers, debugSession ) )

                    # Get pointer to next timer
                    pTimer = pTimerMembers[ OS_TIMER_PNEXT ]

        # Timer records
        return records
