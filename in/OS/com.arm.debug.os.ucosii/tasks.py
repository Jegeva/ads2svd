# Copyright (C) 2013-2014,2017 Arm Limited (or its affiliates). All rights reserved.

from osapi import *
from utils import *
from globs import *

class Tasks( Table ):

    # Class ID
    ID = "tasks"

    # Column definitions
    cols = \
    [
        [ OS_TCB_TASKNAME,      MEMBER_AS_STRING     ],
        [ OS_TCB_ID,            MEMBER_AS_NUMBER     ],
        [ OS_TCB_PRIO,          MEMBER_AS_NUMBER     ],
        [ OS_TCB_STAT,          MEMBER_AS_TASK_STATE ],
        [ OS_TCB_STATPEND,      MEMBER_AS_PEND_STATE ],
        [ OS_TCB_DLY,           MEMBER_AS_NUMBER     ],
        [ OS_TCB_OPT,           MEMBER_AS_TASK_OPTS  ],
        [ OS_TCB_STKUSED,       MEMBER_AS_NUMBER     ],
        [ OS_TCB_STKBASE,       MEMBER_AS_ADDRESS    ],
        [ OS_TCB_STKPTR,        MEMBER_AS_ADDRESS    ],
        [ OS_TCB_STKBOTTOM,     MEMBER_AS_ADDRESS    ],
        [ OS_TCB_STKSIZE,       MEMBER_AS_NUMBER     ],
        [ OS_TCB_EXTPTR,        MEMBER_AS_ADDRESS    ],
        [ OS_TCB_NEXT,          MEMBER_AS_ADDRESS    ],
        [ OS_TCB_PREV,          MEMBER_AS_ADDRESS    ],
        [ OS_TCB_EVENTPTR,      MEMBER_AS_ADDRESS    ],
        [ OS_TCB_EVENTMULTIPTR, MEMBER_AS_ADDRESS    ],
        [ OS_TCB_MSG,           MEMBER_AS_ADDRESS    ],
        [ OS_TCB_FLAGNODE,      MEMBER_AS_ADDRESS    ],
        [ OS_TCB_FLAGSRDY,      MEMBER_AS_HEX        ],
        [ OS_TCB_DELREQ,        MEMBER_AS_YES_NO     ],
        [ OS_TCB_CTXSWCTR,      MEMBER_AS_NUMBER     ],
        [ OS_TCB_CYCLESTOT,     MEMBER_AS_NUMBER     ],
        [ OS_TCB_CYCLESSTART,   MEMBER_AS_NUMBER     ],
        [ OS_TCB_X,             MEMBER_AS_HEX        ],
        [ OS_TCB_Y,             MEMBER_AS_HEX        ],
        [ OS_TCB_BITX,          MEMBER_AS_HEX        ],
        [ OS_TCB_BITY,          MEMBER_AS_HEX        ],
        [ OS_TCB_TLS,           MEMBER_AS_ADDRESS    ]
    ]

    def __init__( self ):

        id = self.ID

        fields = [ createPrimaryField( id, OS_TCB, TEXT ) ]

        for col in self.cols:
            fields.append( createField( id, col[ 0 ][ 0 ], TEXT ) )

        Table.__init__( self, id, fields )

    def readTask( self, id, members, debugSession ):

        cells = [ createTextCell( id ) ]
        for col in self.cols:
            cells.append( createTextCell( getMemberValue( members, col[ 0 ], col[ 1 ], debugSession ) ) )

        return self.createRecord( cells )

    def getRecords( self, debugSession ):

        records = [ ]

        if isOSRunning( debugSession ):

            osTCBPrioTbl = globGetName( OS_TCB_PRIO_TBL, debugSession )
            if osTCBPrioTbl:

                taskPtrs = debugSession.evaluateExpression( osTCBPrioTbl ).getArrayElements( )

                for taskPtr in taskPtrs:

                    if taskPtr.readAsNumber( ) > 1:

                        id = taskPtr.readAsAddress( ).toString( )
                        members = taskPtr.dereferencePointer( ).getStructureMembers( )
                        records.append( self.readTask( id, members, debugSession ) )

        return records
