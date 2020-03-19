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

# Timers class
class Timers( Table ):

    # Class ID
    ID = "timers"

    # Column definitions
    cols_item = \
    [
        [ TIMER_PC_TIMER_NAME,        FORMAT_STRING      ],
        [ TIMER_XTIMERPERIODINTICKS,  FORMAT_NUMBER_STR  ],
        [ TIMER_UX_AUTO_RELOAD,       FORMAT_YES_NO      ],
        [ TIMER_PV_TIMER_ID,          FORMAT_HEX         ],
        [ TIMER_PX_CALLBACK_FUNCTION, FORMAT_ADDRESS_STR ]
    ]

    # Class constructor
    def __init__( self ):

        # Class ID
        cid = self.ID

        # Create primary field
        fields = [ createPrimaryField( cid, TIMER, TEXT ) ]

        # Create queue item columes
        for col in self.cols_item:
            fields.append( createField( cid, col[ 0 ], TEXT ) )

        # Create table
        Table.__init__( self, cid, fields )

    # Read timer
    def readTimer( self, cid, members, debugSession ):

        # Populate primary field
        cells = [ createTextCell( cid ) ]

        # Populate queue fields
        for col in self.cols_item:
            cells.append( createTextCell( getMemberValue( members, col[ 0 ], col[ 1 ], debugSession ) ) )

        # Populated record
        return self.createRecord( cells )

    # Read timers
    def readTimers( self, timerList, records, debugSession ):

        # Make sure symbol exists
        if debugSession.symbolExists( timerList ):

            # Get pointer to current timer list
            timerListPtr = debugSession.evaluateExpression( timerList )

            # Empty?
            if timerListPtr.readAsNumber( ) > 0:

                # No, get items in list
                timerList = timerListPtr.dereferencePointer( )

                # Now read them as timers
                timers = readListItems( timerList, TIMER )

                # Process each timer
                for timer in timers:

                    # Create timer ID (address of structure)
                    timerId = hex( addressExprsToLong( timer ) )

                    # Get timer structure members
                    timerMembers = timer.getStructureMembers( )

                    # Create timer record
                    records.append( self.readTimer( timerId, timerMembers, debugSession ) )

    # Get queues
    def getRecords( self, debugSession ):

        # Initilaise timers
        records = [ ]

        # Get timers from current list
        self.readTimers( PX_CURRENT_TIMER_LIST, records, debugSession )

        # Get timers from overflow list
        self.readTimers( PX_OVERFLOW_TIMER_LIST, records, debugSession )

        # Timer records
        return records
