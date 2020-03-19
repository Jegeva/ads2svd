################################################################################
#
# Copyright (C) 2014,2017 Arm Limited (or its affiliates). All rights reserved.
#
# embOS - 3.88c ARM Cortex M / 3.88h ARM Cortex A
#
#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

from globs import *


# Object format codes
FORMAT_ADDRESS_STR     = 1
FORMAT_HEX             = 2
FORMAT_NUMBER          = 3
FORMAT_NUMBER_STR      = 4
FORMAT_STRING          = 5
FORMAT_STRING_PTR      = 6
FORMAT_TASK_STATUS     = 7
FORMAT_TASK_NAME       = 8
FORMAT_ERROR_TEXT      = 9
FORMAT_TIMEOUT         = 10

# Event reset options
OS_EVENT_RESET = \
[
    "SEMIAUTO",
    "MANUAL",
    "AUTO",
    "COUNT"
]

# Task states
OS_TS_TEXT = \
[
    "READY",
    "WAIT EVENT",
    "WAIT SEMAZ",
    "WAIT ANY",
    "WAIT SEMANZ",
    "WAIT MEMF",
    "WAIT QUEUE",
    "WAIT MBNF",
    "WAIT MBNE",
    "WAIT EVOBJ",
    "WAIT QNF"
]

# FPU status text
FPUSUPPORT = \
{
    REG_MAP_V7MVFP       : "Yes",
    REG_MAP_V7MBASIC     : "No",
    REG_MAP_V7ABASIC     : "No",
    REG_MAP_V7ANEONINT   : "Yes",
    REG_MAP_V7ANEON      : "Yes",
    REG_MAP_V7AFPU16INT  : "Yes",
    REG_MAP_V7AFPU16     : "Yes",
    REG_MAP_V7ABASICINT  : "No"
}

# Interrupt stack frame
INTSTACKFRAME = \
{
    REG_MAP_V7MVFP       : "N/A",
    REG_MAP_V7MBASIC     : "N/A",
    REG_MAP_V7ABASIC     : "No",
    REG_MAP_V7ANEONINT   : "Yes",
    REG_MAP_V7ANEON      : "No",
    REG_MAP_V7AFPU16INT  : "Yes",
    REG_MAP_V7AFPU16     : "No",
    REG_MAP_V7ABASICINT  : "Yes"
}

# Get task status text
def getTaskStatusText( taskStatus ):
    if taskStatus & 0x04:
        return "TIMEOUT"
    scnt = taskStatus & 0x03
    if scnt > 0:
        return "SUSPENDED(" + str(scnt) + ")"
    taskStatus = taskStatus & 0xf8
    taskStatusIndex = taskStatus >> 3
    if taskStatusIndex <= 10:
        return OS_TS_TEXT[ taskStatusIndex ]
    else:
        return str( taskStatusIndex )

# Format expression
def formatExpr( expr, exprType, debugSession, defVal="N/A" ):

    # Assign default return value (used when no value can be found)
    val = defVal

    if exprType == FORMAT_ADDRESS_STR:
        val = expr.readAsAddress( ).toString( )

    elif exprType == FORMAT_HEX:
        val = hex( expr.readAsNumber( ) )

    elif exprType == FORMAT_NUMBER:
        val = expr.readAsNumber( )

    elif exprType == FORMAT_NUMBER_STR:
        val = str( expr.readAsNumber( ) )

    elif exprType == FORMAT_STRING:
        val = expr.readAsNullTerminatedString( )

    elif exprType == FORMAT_STRING_PTR:
        addr = expr.readAsNumber( )
        if addr != 0:
            val = debugSession.evaluateExpression( "(char*)" + str( addr ) ).readAsNullTerminatedString( )

    elif exprType == FORMAT_TASK_STATUS:
        taskStatus = expr.readAsNumber( )
        val = getTaskStatusText( taskStatus )

    elif exprType == FORMAT_TASK_NAME:
        if expr.readAsNumber( ) > 0:
            taskMembers = expr.dereferencePointer( ).getStructureMembers( )
            if OS_TASK_NAME in taskMembers:
                val = taskMembers[ OS_TASK_NAME ].readAsNullTerminatedString( )

    elif exprType == FORMAT_ERROR_TEXT:
        err = expr.readAsNumber( )
        val = getErrorText( err )

    elif exprType == FORMAT_TIMEOUT:
        timeout = expr.readAsNumber( )
        currentTime = globCreateRef( [ OS_GLOBAL, OS_GLOBALS_TIME ] )
        if currentTime:
            timeout = timeout - debugSession.evaluateExpression( currentTime ).readAsNumber( )
            if timeout < 0:
                timeout = 0
        val = str( timeout )

    # Formatted value
    return val

# Get value of member
def getMemberValue( members, member, exprType, debugSession, defVal="N/A" ):

    # Assign default return value (used when no value can be found)
    val = defVal

    # Check if we have a valid member
    if member in members:

        # Get member expression
        expr = members[ member ]

        # Get value
        val = formatExpr( expr, exprType, debugSession )

    return val

# Is OS running
def isOSRunning( debugSession ):
    return debugSession.evaluateExpression( OS_RUNNING ).readAsNumber( ) == 1

# Determine if task has enabled floating point support
def isTaskFpEnabled( members, func, debugSession ):

    # Default is no support for NEON/FPU
    enabled = 0

    # Check if function exists that extends task context for FPU support
    if debugSession.symbolExists( func ):

        # See if task context has been extended
        osTaskPextendcontextPtr = members[ OS_TASK_PEXTENDCONTEXT ].readAsNumber( )
        if osTaskPextendcontextPtr > 0:

            # Get extended context save structure
            osExtendContext = debugSession.evaluateExpression( func )

            # Get address of structure
            osExtendContextAddr = osExtendContext.getLocationAddress( ).getLinearAddress( )

            # If extended context address equals the Neon/VFP structure then we can enable the FPU
            if osTaskPextendcontextPtr == osExtendContextAddr:
                enabled = 1;    # FPU enabled

    # Enabled flag
    return enabled

# Determine if task has an interrupt stack frame
def isIntStackFrame( members, func, debugSession ):

    # Default non interrupt stack frame
    intStackFrame = 0;

    # Make sure function exists!
    if debugSession.symbolExists( func ):

        # Get address of function used when task interrupted
        osSwitchAfterISRArmAddr = debugSession.evaluateExpression( func ).getLocationAddress( ).getLinearAddress( )

        # Get saved stack pointer from task stack
        stackPointer = members[ OS_TASK_PSTACK ].readAsNumber( )

        # Now get saved program counter (this is location where task will resume after suspension)
        programCounter = stackPointer + 36L

        # Now get actual program counter
        programCounter = debugSession.evaluateExpression( "*(unsigned long)" + str( programCounter ) ).readAsNumber( )
        #print hex( programCounter ),hex( osSwitchAfterISRArmAddr ),

        # Now check if its within function were are testing (uses a range from start of function)
        if ( programCounter > osSwitchAfterISRArmAddr ) and ( programCounter < ( osSwitchAfterISRArmAddr + 0x10 ) ):
            intStackFrame = 1;

    # Interrupt stack frame
    return intStackFrame


# Get register map name
def getRegMapName( stackPointer, members, debugSession ):

    # default text
    regMapName = REG_MAP_V7MBASIC

    # Get architecture name
    archName = debugSession.getTargetInformation( ).getArchitecture( ).getName( )

    # Determine which stack frame being used
    if archName == "ARMv7M" or archName == "ARMv7R" or archName == "ARMv6M":

        # Has task context been extended for FPU support?
        if isTaskFpEnabled( members, OS_VFP_EXTENDCONTEXT, debugSession ):

            # Yes, must be an M4 with FPU enabled
            regMapName = REG_MAP_V7MVFP

        else:

            # No, must be an M3/M4
            regMapName = REG_MAP_V7MBASIC

    # Must be ARMv7A
    else:

        # Determine if interrupt stack frame has been used
        intStackFrame = isIntStackFrame( members, OS_SWITCHAFTERISR_ARM, debugSession )

        # Has task context been extended for NEON support?
        if isTaskFpEnabled( members, OS_NEON_EXTENDCONTEXT, debugSession ):

            # Interrupt stack frame?
            if intStackFrame:

                # Yes
                regMapName = REG_MAP_V7ANEONINT

            else:

                # No
                regMapName = REG_MAP_V7ANEON

        # Has task context been extended for VFP support?
        elif isTaskFpEnabled( members, OS_VFP_EXTENDCONTEXT, debugSession ):

            # Interrupt stack frame?
            if intStackFrame:

                # Yes
                regMapName = REG_MAP_V7AFPU16INT

            else:

                # No
                regMapName = REG_MAP_V7AFPU16

        # Interrupt stack frame (No NEON or VFP)?
        elif intStackFrame:

            # Yes
            regMapName = REG_MAP_V7ABASICINT

        else:

            # No
            regMapName = REG_MAP_V7ABASIC

    # Register map name
    return regMapName

# Get FPU status text from map name
def getFPUStatusText( regMapName ):
    return FPUSUPPORT[ regMapName ]

# Get stack frame interrupt status
def getStackFrameText( regMapName ):
    return INTSTACKFRAME[ regMapName ]

# get current stack usage
def getCurrentStackUsage( members, debugSession ):
    stackUsed = 0
    stackUsedPc = 0
    stackUsedMax = 0
    stackUsedMaxPc = 0
    stackBottom = getMemberValue( members, OS_TASK_PSTACKBOT, FORMAT_NUMBER, debugSession, "" )
    if stackBottom:
        taskName = getMemberValue( members, OS_TASK_NAME, FORMAT_STRING, debugSession )
        stackPtr = getMemberValue( members, OS_TASK_PSTACK, FORMAT_NUMBER, debugSession )
        stackSize = getMemberValue( members, OS_TASK_STACKSIZE, FORMAT_NUMBER, debugSession )
        stackEnd = stackBottom + stackSize
        stackUsed = ( stackEnd - stackPtr ) + 4
        if stackSize > 0:
            stackUsedPc = ( stackUsed / float( stackSize ) ) * 100

        for addr in range( stackPtr, stackBottom, -4 ):
            val = debugSession.evaluateExpression( "*(unsigned long*)" + str( addr ) ).readAsAddress( ).getLinearAddress( )
            if val == 3452816845:
                break

        stackUsedMax = stackEnd - addr
        if stackSize > 0:
            stackUsedMaxPc = ( stackUsedMax / float( stackSize ) ) * 100

    return stackUsed, stackUsedPc, stackUsedMax, stackUsedMaxPc

def make_reg_list(offset, size, *reg_names):
    result = [("%s" % reg_names[x], long(offset + x*size)) for x in xrange(len(reg_names))]
    return result

def make_reg_range(offset, size, prefix, start, count):
    result = [("%s%d" % (prefix, start+x), long(offset + x*size)) for x in xrange(0, count)]
    return result
