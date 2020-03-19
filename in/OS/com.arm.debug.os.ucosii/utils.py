# Copyright (C) 2013-2014,2017 Arm Limited (or its affiliates). All rights reserved.

from osapi import *
from globs import *

MEMBER_AS_ADDRESS           = 0
MEMBER_AS_CSTRING           = 1
MEMBER_AS_EVENT_COUNT       = 2
MEMBER_AS_EVENT_TASKS       = 3
MEMBER_AS_EVENT_TYPE        = 4
MEMBER_AS_FLAG_WAIT_TYPE    = 5
MEMBER_AS_HEX               = 6
MEMBER_AS_NUMBER            = 7
MEMBER_AS_PEND_STATE        = 8
MEMBER_AS_STRING            = 9
MEMBER_AS_TASK_NAME         = 10
MEMBER_AS_TASK_OPTS         = 11
MEMBER_AS_TASK_STATE        = 12
MEMBER_AS_TIMER_OPTS        = 13
MEMBER_AS_TIMER_STATE       = 14
MEMBER_AS_YES_NO            = 15

TASK_STATE_NAMES = \
[
    "RDY",              # 0
    "SEM",              # 1
    "MBOX",             # 2
    "QUEUE",            # 3
    "SUSPENDED",        # 4
    "MUTEX",            # 5
    "FLAG",             # 6
    "MULTI"             # 7
]

PENDING_STATE_NAMES = \
[
    "COMPLETE",         # 0
    "TIMEOUT",          # 1
    "ABORTED"           # 2
]

YES_NO_NAMES = \
[
    "NO",               # 0
    "YES"               # 1
]

TASK_FLAG_OPTIONS = \
[
    "NONE",             # 0
    "STK_CHK",          # 1
    "STK_CLR",          # 2
    "SAVE_FP"           # 3
]

FLAG_WAIT_TYPES = \
[
    "CLR-ALL",
    "CLR-ANY",
    "SET-ALL",
    "SET-ANY"
]

TIMER_OPTS = \
[
    "NONE",
    "ONE_SHOT",
    "PERIODIC",
    "CALLBACK",
    "CALLBACK_ARG"
]

TIMER_STATES = \
[
    "UNUSED",
    "STOPPED",
    "RUNNING",
    "COMPLETED"
]

OS_UN_MAP_TABLE = \
[
    0, 0, 1, 0, 2, 0, 1, 0, 3, 0, 1, 0, 2, 0, 1, 0,         # 0x00 to 0x0F
    4, 0, 1, 0, 2, 0, 1, 0, 3, 0, 1, 0, 2, 0, 1, 0,         # 0x10 to 0x1F
    5, 0, 1, 0, 2, 0, 1, 0, 3, 0, 1, 0, 2, 0, 1, 0,         # 0x20 to 0x2F
    4, 0, 1, 0, 2, 0, 1, 0, 3, 0, 1, 0, 2, 0, 1, 0,         # 0x30 to 0x3F
    6, 0, 1, 0, 2, 0, 1, 0, 3, 0, 1, 0, 2, 0, 1, 0,         # 0x40 to 0x4F
    4, 0, 1, 0, 2, 0, 1, 0, 3, 0, 1, 0, 2, 0, 1, 0,         # 0x50 to 0x5F
    5, 0, 1, 0, 2, 0, 1, 0, 3, 0, 1, 0, 2, 0, 1, 0,         # 0x60 to 0x6F
    4, 0, 1, 0, 2, 0, 1, 0, 3, 0, 1, 0, 2, 0, 1, 0,         # 0x70 to 0x7F
    7, 0, 1, 0, 2, 0, 1, 0, 3, 0, 1, 0, 2, 0, 1, 0,         # 0x80 to 0x8F
    4, 0, 1, 0, 2, 0, 1, 0, 3, 0, 1, 0, 2, 0, 1, 0,         # 0x90 to 0x9F
    5, 0, 1, 0, 2, 0, 1, 0, 3, 0, 1, 0, 2, 0, 1, 0,         # 0xA0 to 0xAF
    4, 0, 1, 0, 2, 0, 1, 0, 3, 0, 1, 0, 2, 0, 1, 0,         # 0xB0 to 0xBF
    6, 0, 1, 0, 2, 0, 1, 0, 3, 0, 1, 0, 2, 0, 1, 0,         # 0xC0 to 0xCF
    4, 0, 1, 0, 2, 0, 1, 0, 3, 0, 1, 0, 2, 0, 1, 0,         # 0xD0 to 0xDF
    5, 0, 1, 0, 2, 0, 1, 0, 3, 0, 1, 0, 2, 0, 1, 0,         # 0xE0 to 0xEF
    4, 0, 1, 0, 2, 0, 1, 0, 3, 0, 1, 0, 2, 0, 1, 0          # 0xF0 to 0xFF
]

def getEventType( eventType ):

    name = "ILLEGAL"

    if eventType == 0:
        name = "UNUSED"
    elif eventType == 1:
        name = "MBOX"
    elif eventType == 2:
        name = "QUEUE"
    elif eventType == 3:
        name = "SEMA4"
    elif eventType == 4:
        name = "MUTEX"
    elif eventType == 5:
        name = "FLAG"
    elif eventType == 100:
        name = "TIMER"

    return name

def getBitOptNames( bitOptNames, stateVal ):

    opts = bitOptNames[ 0 ]
    i = 1
    j = 0
    m = 1

    for opt in bitOptNames:

        if stateVal & m:

            if j == 0:
                opts = ""
            elif j > 0:
                opts = opts + "+"

            opts = opts + bitOptNames[ i ]

            j = j + 1

        m = m * 2
        i = i + 1

    return opts

def getStateName( stateNames, stateVal ):

    if stateVal < 0 or stateVal > ( len( stateNames ) - 1 ):
        return str( stateVal )
    else:
        return stateNames[ int( stateVal ) ]

def getTaskNameUsingPriority( priority, defName, debugSession ):

    taskName = defName

    osTCBPrioTblName = globGetName( OS_TCB_PRIO_TBL, debugSession )
    if osTCBPrioTblName:

        taskPtr = debugSession.evaluateExpression( osTCBPrioTblName ).getArrayElements( )[ priority ]

        if taskPtr.readAsNumber( ) > 0:

            taskMembers = taskPtr.dereferencePointer( ).getStructureMembers( )
            taskName = getMemberValue( taskMembers, OS_TCB_TASKNAME, MEMBER_AS_STRING, debugSession )

    return taskName

def getEventHighestWaitingTaskPriority( members, debugSession ):

    priority = 0

    osEventGrpName      = getMemberName( OS_EVENT_GRP, members )
    osEventTblName      = getMemberName( OS_EVENT_TBL, members )

    osLowestPrioName    = globGetName( OS_LOWEST_PRIO, debugSession )

    if osEventGrpName and osEventTblName and osLowestPrioName:

        if debugSession.evaluateExpression( osLowestPrioName ).readAsNumber( ) <= 63:

            y = OS_UN_MAP_TABLE[ members[ osEventGrpName ].readAsNumber( ) ]
            x = OS_UN_MAP_TABLE[ members[ osEventTblName ].getArrayElements( )[ y ].readAsNumber( ) ]

            priority = ( y << 3 ) + x

        else:

            eventGroup = members[ osEventGrpName ].readAsNumber( )

            if eventGroup & 0xFF != 0:
                y = OS_UN_MAP_TABLE[ eventGroup & 0xFF ]
            else:
                y = OS_UN_MAP_TABLE[ ( eventGroup >> 8 ) & 0xFF ] + 8

            ptbl = members[ osEventTblName ].getArrayElements( )[ y ].readAsNumber( )

            if ptbl & 0xFF != 0:
                x = OS_UN_MAP_TABLE[ ptbl & 0xFF ]
            else:
                y = OS_UN_MAP_TABLE[ ( ptbl >> 8 ) & 0xFF ] + 8

            priority = ( y << 4 ) + x

    return priority

def getEventHighestWaitingTaskPriorityName( members, defName, debugSession ):

    priority = getHighestWaitingTaskPriority( members, debugSession )
    taskName = getTaskNameUsingPriority( priority, defName, debugSession )

    return taskName

def getEventListOfWaitingTasks( members, debugSession ):

    tasks = [ ]

    osEventGrpName      = getMemberName( OS_EVENT_GRP, members )
    osEventTblName      = getMemberName( OS_EVENT_TBL, members )

    osLowestPrioName    = globGetName( OS_LOWEST_PRIO, debugSession )

    if osEventGrpName and osEventTblName and osLowestPrioName:

        group = members[ osEventGrpName ].readAsNumber( )
        table = members[ osEventTblName ].getArrayElements( )

        if debugSession.evaluateExpression( osLowestPrioName ).readAsNumber( ) <= 63:
            k = 8
        else:
            k = 16;

        l = len( table )
        for i in range( k ):

            if group & ( 1 << i ):

                for j in range( l ):

                    if table[ i ].readAsNumber( ) & ( 1 << j ):

                        priority = ( i * k ) + j
                        taskName = getTaskNameUsingPriority( priority, "", debugSession )

                        if len( taskName ):
                            tasks.append( taskName )

        return ', '.join( tasks )

def getFlagListOfWaitingNodeTasks( osFlagNodePtr, debugSession ):

    tasks = [ ]

    while osFlagNodePtr.readAsNumber( ) != 0:

        members = osFlagNodePtr.dereferencePointer( ).getStructureMembers( )

        osFlagNodeTCBName   = getMemberName( OS_FLAG_NODE_TCB, members )
        osFlagNodeNextName  = getMemberName( OS_FLAG_NODE_NEXT, members )

        if not ( osFlagNodeTCBName and osFlagNodeNextName ):
            break

        OSFlagNodeTCBPtr = debugSession.evaluateExpression( "(" + OS_TCB + "*)" + str( members[ osFlagNodeTCBName ].readAsNumber( ) ) )

        if OSFlagNodeTCBPtr.readAsNumber( ) != 0:

            taskMembers = OSFlagNodeTCBPtr.dereferencePointer( ).getStructureMembers( )
            OSTCBTaskName = getMemberValue( taskMembers, OS_TCB_TASKNAME, MEMBER_AS_STRING, debugSession, "" )

            if len( OSTCBTaskName ):
                tasks.append( OSTCBTaskName )

        osFlagNodePtr = debugSession.evaluateExpression( "(" + OS_FLAG_NODE + "*)" + str( members[ osFlagNodeNextName ].readAsNumber( ) ) )

    return ', '.join( tasks )

def getFlagWaitOptionStr( value ):

    if value >= len( FLAG_WAIT_TYPES ):
        return "INVALID OPTIONS"

    return FLAG_WAIT_TYPES[ value ]

def readExpression( expr, exprType, debugSession ):
    val = ""
    if debugSession.symbolExists( expr ):
        if exprType == "address":
            val = debugSession.evaluateExpression( expr ).readAsAddress( ).toString( )
        elif exprType == "number":
            val = str( debugSession.evaluateExpression( expr ).readAsNumber( ) )
        elif exprType == "hex":
            val = hex( debugSession.evaluateExpression( expr ).readAsNumber( ) )
        elif exprType == "string":
            val = debugSession.evaluateExpression( expr ).readAsNullTerminatedString( )
        elif exprType == "task":
            taskPtr = debugSession.evaluateExpression( "(" + OS_TCB + "*)" + str( expr ) )
            taskMembers = taskPtr.dereferencePointer( ).getStructureMembers( )
            val = getMemberValue( taskMembers, OS_TCB_TASKNAME, MEMBER_AS_STRING, debugSession )
        else:
            pass
    return val

# Get value of member
def getMemberVal( members, member, exprType, debugSession, defVal="N/A" ):
    # Assign default return value (used when no value can be found)
    val = defVal
    # Check if we have a valid member
    if member in members:

        # Get member expression
        expr = members[ member ]

        # Get value based to type specified
        if exprType == MEMBER_AS_ADDRESS:
            val = expr.readAsAddress( ).toString( )

        elif exprType == MEMBER_AS_CSTRING:
            addr = expr.readAsNumber( )
            if addr != 0:
                val = debugSession.evaluateExpression( "(char*)" + str( addr ) ).readAsNullTerminatedString( )

        elif exprType == MEMBER_AS_EVENT_COUNT:
            valNum =  expr.readAsNumber( ) & 0xFF
            if valNum != 0xFF:
                val = str( valNum )

        elif exprType == MEMBER_AS_EVENT_TASKS:
            val = getEventListOfWaitingTasks( members, debugSession )
            if( len( val ) == 0 ):
                val = "None"

        elif exprType == MEMBER_AS_EVENT_TYPE:
            val = getEventType( expr.readAsNumber( ) )

        elif exprType == MEMBER_AS_FLAG_WAIT_TYPE:
            val = getFlagWaitOptionStr( expr.readAsNumber( ) )

        elif exprType == MEMBER_AS_HEX:
            val = hex( expr.readAsNumber( ) )

        elif exprType == MEMBER_AS_NUMBER:
            val = str( expr.readAsNumber( ) )

        elif exprType == MEMBER_AS_PEND_STATE:
            valNum = expr.readAsNumber( )
            val = getBitOptNames( PENDING_STATE_NAMES, valNum )

        elif exprType == MEMBER_AS_STRING:
            val = expr.readAsNullTerminatedString( )

        elif exprType == MEMBER_AS_TASK_NAME:
            address = expr.readAsNumber( )
            taskPtr = debugSession.evaluateExpression( "(" + OS_TCB + "*)" + str( address ) )
            taskMembers = taskPtr.dereferencePointer( ).getStructureMembers( )
            val = getMemberValue( taskMembers, OS_TCB_TASKNAME, MEMBER_AS_STRING, debugSession )

        elif exprType == MEMBER_AS_TASK_OPTS:
            valNum = expr.readAsNumber( )
            val = getBitOptNames( TASK_FLAG_OPTIONS, valNum )

        elif exprType == MEMBER_AS_TASK_STATE:
            valNum = expr.readAsNumber( )
            val = getBitOptNames( TASK_STATE_NAMES, valNum )

        elif exprType == MEMBER_AS_TIMER_OPTS:
            valNum = expr.readAsNumber( )
            val = getStateName( TIMER_OPTS, valNum )

        elif exprType == MEMBER_AS_TIMER_STATE:
            valNum = expr.readAsNumber( )
            val = getStateName( TIMER_STATES, valNum )

        elif exprType == MEMBER_AS_YES_NO:
            valNum = expr.readAsNumber( )
            val = getBitOptNames( YES_NO_NAMES, valNum )

        else:
            pass

    return val

# Get value of a member based on a number of possible names
def getMemberValue( members, names, exprType, debugSession, defVal="N/A" ):
    # Assign default return value (used when no value can be found)
    val = defVal
    # Check member is valid
    if len( names ) > 0:
        # Step through list of names until a match is found
        for name in names:
            # Try to read member value
            val = getMemberVal( members, name, exprType, debugSession, defVal )
            # Found value?
            if val != defVal:
                break;      # Yes, we can leave
    # Member value
    return val

# Get member name from list of members
def getMemberName( member, members ):
    name = ""
    for m in member:
        if m in members:
            name = m
            break
    return name

# Is uCOS-II up and running
def isOSRunning( debugSession ):
    osRunning = globGetName( OS_RUNNING, debugSession )
    if osRunning:
        return debugSession.evaluateExpression( osRunning ).readAsNumber( ) == 1

def make_reg_list(offset, size, *reg_names):
    result = [("%s" % reg_names[x], long(offset + x*size)) for x in xrange(len(reg_names))]
    return result

def make_reg_range(offset, size, prefix, start, count):
    result = [("%s%d" % (prefix, x+start), long(offset + x*size)) for x in xrange(0, count)]
    return result

