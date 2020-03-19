# Copyright (C) 2013-2014,2017 Arm Limited (or its affiliates). All rights reserved.

# Import all!
from osapi import *
from utils import *
from events import *

# OS Flags Class Definition
class Flags( Table ):

    # Class ID
    ID = "flags"

    # Column definitions - flags
    flagCols = \
    [
        [ OS_FLAG_NAME,      MEMBER_AS_STRING  ],
        [ OS_FLAG_FLAGS,     MEMBER_AS_HEX     ],
        [ OS_FLAG_WAIT_LIST, MEMBER_AS_ADDRESS ]
    ]

    # Column definitions - nodes
    nodeCols = \
    [
        [ OS_FLAG_NODE_TCB,       MEMBER_AS_TASK_NAME      ],
        [ OS_FLAG_NODE_FLAGS,     MEMBER_AS_HEX            ],
        [ OS_FLAG_NODE_WAIT_TYPE, MEMBER_AS_FLAG_WAIT_TYPE ],
        [ OS_FLAG_NODE_NEXT,      MEMBER_AS_ADDRESS        ],
        [ OS_FLAG_NODE_PREV,      MEMBER_AS_ADDRESS        ]
    ]

    def __init__( self ):

        id = self.ID

        fields = [ createPrimaryField( id, OS_FLAG_GRP, TEXT ) ]

        for col in self.flagCols:
            fields.append( createField( id, col[ 0 ][ 0 ], TEXT ) )

        for col in self.nodeCols:
            fields.append( createField( id, col[ 0 ][ 0 ], TEXT ) )

        Table.__init__( self, id, fields )

    # read flag details
    def readFlag( self, id, flagMembers, nodeMembers, debugSession ):

        cells = [ createTextCell( id ) ]

        for col in self.flagCols:
            cells.append( createTextCell( getMemberValue( flagMembers, col[ 0 ], col[ 1 ], debugSession ) ) )

        for col in self.nodeCols:
                cells.append( createTextCell( getMemberValue( nodeMembers, col[ 0 ], col[ 1 ], debugSession ) ) )

        return self.createRecord( cells )

    # read flag details
    def readFlags( self, id, members, records, debugSession ):

        osFlagWaitListAddr = int( getMemberValue( members, OS_FLAG_WAIT_LIST, MEMBER_AS_NUMBER, debugSession, "0" ) )
        osFlagNodePtr = debugSession.evaluateExpression( "("+ OS_FLAG_NODE + "*)" + str( osFlagWaitListAddr ) )

        while 1:

            nodeMembers = [ ]
            if osFlagNodePtr.readAsNumber( ) != 0:
                nodeMembers = osFlagNodePtr.dereferencePointer( ).getStructureMembers( )

            records.append( self.readFlag( id, members, nodeMembers, debugSession ) )
            if osFlagNodePtr.readAsNumber( ) != 0:

                nextNodeAddr = int( getMemberValue( nodeMembers, OS_FLAG_NODE_NEXT, MEMBER_AS_NUMBER, debugSession, "0" ) )
                if nextNodeAddr != 0:
                    osFlagNodePtr = debugSession.evaluateExpression( "("+ OS_FLAG_NODE + "*)" + str( nextNodeAddr ) )
                else:
                    break

            if osFlagNodePtr.readAsNumber( ) == 0:
                break

    # read flags
    def getRecords( self, debugSession ):

        # no records
        records = [ ]

        # make sure uCOS-II is running
        if isOSRunning( debugSession ):

            osFlagTbl = globGetName( OS_FLAG_TBL, debugSession )
            if osFlagTbl:

                # flag index number
                i = 0;

                # get flag group table
                flags = debugSession.evaluateExpression( osFlagTbl ).getArrayElements( )

                # step through flag group table
                for flag in flags:

                    # get all members of timer structure
                    members = flag.getStructureMembers( )

                    osFlagTypeMember = getMemberName( OS_FLAG_TYPE, members )
                    if not osFlagTypeMember:
                        break

                    # all flags should have type as 5
                    if members[ osFlagTypeMember ].readAsNumber( ) == Events.OS_EVENT_TYPE_FLAG:

                        # get a pointer to flag group record
                        flagPtr = debugSession.evaluateExpression( "&" + osFlagTbl + "[" + str( i ) + "]" )

                        # get address of flag group and use as id
                        id = flagPtr.readAsAddress( ).toString( )

                        # populate flag group details
                        self.readFlags( id, members, records, debugSession )

                    # keep track of number of flag groups
                    i = i + 1

        # Here is complete flag group details
        return records
