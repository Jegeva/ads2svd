# Copyright (C) 2013-2014,2017 Arm Limited (or its affiliates). All rights reserved.

from osapi import *
from utils import *

class MemPartitions( Table ):

    # Class ID
    ID = "mempartitions"

    # Column definitions
    cols = \
    [
        [ OS_MEM_NAME,     MEMBER_AS_STRING  ],
        [ OS_MEM_ADDR,     MEMBER_AS_ADDRESS ],
        [ OS_MEM_FREELIST, MEMBER_AS_ADDRESS ],
        [ OS_MEM_BLKSIZE,  MEMBER_AS_NUMBER  ],
        [ OS_MEM_NBLKS,    MEMBER_AS_NUMBER  ],
        [ OS_MEM_NFREE,    MEMBER_AS_NUMBER  ]
    ]

    def __init__( self ):

        id = self.ID

        fields = [ createPrimaryField( id, OS_MEM, TEXT ) ]

        for col in self.cols:
            fields.append( createField( id, col[ 0 ][ 0 ], TEXT ) )

        Table.__init__( self, id, fields )

    def readMem( self, id, members, debugSession ):

        cells = [ createTextCell( id ) ]
        for col in self.cols:
            cells.append( createTextCell( getMemberValue( members, col[ 0 ], col[ 1 ], debugSession ) ) )

        return self.createRecord( cells )

    def getRecords( self, debugSession ):

        records = [ ]

        if isOSRunning( debugSession ):

            osMemTbl = globGetName( OS_MEM_TBL, debugSession )
            if osMemTbl:

                i = 0;
                memTable = debugSession.evaluateExpression( osMemTbl ).getArrayElements( )

                for memBlock in memTable:

                    members = memBlock.getStructureMembers( )
                    memPtr = debugSession.evaluateExpression( "&" + osMemTbl + "[" + str( i ) + "]" )
                    if memPtr != 0:
                        id = memPtr.readAsAddress( ).toString( )
                        records.append( self.readMem( id, members, debugSession ) )
                        i = i + 1

        return records
