# ###############################################################################
#
# Copyright (C) 2014,2017 Arm Limited (or its affiliates). All rights reserved.
#
# FreeRTOS - V7.6.0 / V8.0.0RC ARM Cortex M / A
#
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

from osapi import *
from globs import *

# Object format codes
FORMAT_NONE            = 0
FORMAT_ADDRESS         = 1
FORMAT_ADDRESS_LIN     = 2
FORMAT_ADDRESS_STR     = 3
FORMAT_HEX             = 4
FORMAT_NUMBER          = 5
FORMAT_NUMBER_STR      = 6
FORMAT_STRING          = 7
FORMAT_STRING_PTR      = 8
FORMAT_ARRAY           = 9
FORMAT_LOCATION        = 10
FORMAT_TASK_LIST       = 11
FORMAT_TASK_LISTS      = 12
FORMAT_QUEUE_TYPE      = 13
FORMAT_TASK_NAME       = 14
FORMAT_YES_NO          = 15

# Task states
STATENAMES = \
{
    PX_READY_TASKS_LISTS          : "READY",
    PX_DELAYED_TASKLIST           : "DELAYED",
    PX_OVERFLOW_DELAYED_TASK_LIST : "DELAYED (OVER)",
    X_PENDING_READY_LIST          : "PENDING",
    X_TASKS_WAITING_TERMINATION   : "TERMINATED",
    X_SUSPENDED_TASK_LIST         : "SUSPENDED"
}

# Register map names / FPU status
REGMAPNAMES = \
{
    REG_MAP_V7AVFP    : "Enabled",
    REG_MAP_V7ABASIC  : "Disabled",
    REG_MAP_V7MVFP    : "Enabled",
    REG_MAP_V7MEXT    : "Disabled",
    REG_MAP_V7MBASIC  : "Not Present"
}

# Queue types
QUEUE_TYPES = \
[
    "QUEUE",
    "MUTEX",
    "SEMA4 C",
    "SEMA4 B",
    "MUTEX R"
]

# Format expression
def formatExpr( expr, exprType, debugSession, defVal="N/A" ):

    # Assign default return value (used when no value can be found)
    val = defVal

    if exprType == FORMAT_NONE:
        val = expr

    elif exprType == FORMAT_ADDRESS:
        val = expr.readAsAddress( )

    elif exprType == FORMAT_ADDRESS_LIN:
        val = expr.readAsAddress( ).getLinearAddress( )

    elif exprType == FORMAT_ADDRESS_STR:
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

    elif exprType == FORMAT_ARRAY:
            val = debugSession.evaluateExpression( expr ).getArrayElements( )

    elif exprType == FORMAT_LOCATION:
        val = hex( expr.getLocationAddress( ).getLinearAddress( ) )

    elif exprType == FORMAT_TASK_LIST:

        val = getItemNamesFromList( expr, TCB_T, TCB_PC_TASK_NAME, debugSession )

    elif exprType == FORMAT_TASK_LISTS:

        val = getTaskNamesFromLists( expr, debugSession )

    elif exprType == FORMAT_QUEUE_TYPE:

        val = getQueueTypeName( expr.readAsNumber( ) )

    elif exprType == FORMAT_TASK_NAME:

        if expr.readAsNumber( ) > 0:
            val = expr.dereferencePointer( TCB_T + "*" ).getStructureMembers( )[ TCB_PC_TASK_NAME ].readAsNullTerminatedString( )

    elif exprType == FORMAT_YES_NO:

        if expr.readAsNumber( ) == 0:
            val = "No"
        else:
            val = "Yes"

    else:
        pass

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

    # Member value
    return val

# Get member name from list of members
def getMemberName( member, members ):

    # Default value
    name = ""

    # Found value?
    if member in members:
        name = member

    # Member name
    return name

# Get queue type name
def getQueueTypeName( queueType ):
    # Lookup name
    return QUEUE_TYPES[ queueType ]

# Get task state name
def getStateNameFromList( listName ):
    # Lookup name
    return STATENAMES[ listName ]

def addressExprsToLong( expr ):
    addr = expr.getLocationAddress()
    return addr.getLinearAddress()

def listGetNextEntry( listMembers, listEnd ):
    nextPtr = listMembers[ XLISTI_PX_NEXT ]
    # Increment the index to the next item and return the item, ensuring
    # we don't return the marker used at the end of the list
    if nextPtr.readAsNumber( ) == addressExprsToLong( listEnd ):
        listMembers = nextPtr.dereferencePointer( ).getStructureMembers( )
        nextPtr = listMembers[ XLISTI_PX_NEXT ]
    return nextPtr

# Get TCB's from a list
def readTCBItems( listStructure ):

    # Initilaise list
    TCBItems = [ ]

    # Get list structure members
    listMembers = listStructure.getStructureMembers( )

    # Get number of items in the list
    numItems = listMembers[ XLIST_UX_NUMBER_OF_ITEMS ].readAsNumber( )

    # List empty?
    if numItems > 0:

        # Get last item
        listItemEnd = listMembers[ XLIST_X_LIST_END ]

        # Get first item
        indexPtr = listMembers[ XLIST_PX_INDEX ]
        listMembers = indexPtr.dereferencePointer( ).getStructureMembers( )

        # Get owner (TCB) of first entry
        listPtr = listGetNextEntry( listMembers, listItemEnd )
        listMembers = listPtr.dereferencePointer( ).getStructureMembers( )
        TCBFirstPtr = listMembers[ XLISTI_PV_OWNER ]

        # Process list
        while True:

            # Get owner (TCB) of next entry
            listPtr = listGetNextEntry( listMembers, listItemEnd )
            listMembers = listPtr.dereferencePointer( ).getStructureMembers( )
            TCBNextPtr = listMembers[ XLISTI_PV_OWNER ]

            # Get TCB (cast as it's actually a void* )
            TCB = TCBNextPtr.dereferencePointer( TCB_T + "*" )

            # Add TCB to list
            TCBItems.append( TCB )

            # End of list?
            if TCBNextPtr.readAsNumber( ) == TCBFirstPtr.readAsNumber( ):
                break   # Yes

    # List of TCB's
    return TCBItems

# Get task names from Read Tasks Lists
def getTaskNamesFromLists( taskLists, debugSession ):

    # Default text when lists empty
    taskNames = "N/A"

    # Get lists
    readyLists = taskLists.getArrayElements( )

    # Process each list
    for readyList in readyLists :

        # Get task names
        tn = getItemNamesFromList( readyList, TCB_T, TCB_PC_TASK_NAME, debugSession )

        # List empty?
        if not tn == "N/A":

            # First task name?
            if not taskNames == "N/A":

                # No, append to list
                taskNames = taskNames + ", " + tn
            else:

                # Start list
                taskNames = tn

    # List of task names
    return taskNames

# Get items from a list
def readListItems( listStructure, itemType ):

    # Initilaise list
    listItems = [ ]

    # Get list structure members
    listMembers = listStructure.getStructureMembers( )

    # Get number of items in the list
    numItems = listMembers[ XLIST_UX_NUMBER_OF_ITEMS ].readAsNumber( )

    # List empty?
    if numItems > 0:

        # Get last item
        listItemEnd = listMembers[ XLIST_X_LIST_END ]

        # Get first item
        indexPtr = listMembers[ XLIST_PX_INDEX ]
        listMembers = indexPtr.dereferencePointer( ).getStructureMembers( )

        # Get owner of first entry
        listPtr = listGetNextEntry( listMembers, listItemEnd )
        listMembers = listPtr.dereferencePointer( ).getStructureMembers( )
        firstItemPtr = listMembers[ XLISTI_PV_OWNER ]

        # Process list
        while True:

            # Get owner of next entry
            listPtr = listGetNextEntry( listMembers, listItemEnd )
            listMembers = listPtr.dereferencePointer( ).getStructureMembers( )
            nextItemPtr = listMembers[ XLISTI_PV_OWNER ]

            # Get item (cast as it's actually a void* )
            item = nextItemPtr.dereferencePointer( itemType + "*" )

            # Add item to list
            listItems.append( item )

            # End of list?
            if nextItemPtr.readAsNumber( ) == firstItemPtr.readAsNumber( ):
                break   # Yes

    # List items
    return listItems

# Get item names from a list
def getItemNamesFromList( itemList, itemType, memberName, debugSession ):

    # Default text when lists empty
    itemNames = "N/A"

    # Read list items
    listItems = readListItems( itemList, itemType )

    # Process each item
    for listItem in listItems:

        # Get the item structure members
        listItemMembers = listItem.getStructureMembers( )

        # Get item name
        itemName = listItemMembers[ memberName ].readAsNullTerminatedString( )

        # First item name?
        if not itemNames == "N/A":

            # No, append to list
            itemNames = itemNames + ", " + itemName

        else:

            # Start list
            itemNames = itemName

    # List of item names
    return itemNames

# Get register map name
def getRegMapName( stackPointer, debugSession ):

    # default text
    regMapName = REG_MAP_V7MBASIC

    # Get processor architecture
    archName = debugSession.getTargetInformation( ).getArchitecture( ).getName( )

    # Cortex-R/M
    if archName == "ARMv7M" or archName == "ARMv7R" or archName == "ARMv6M":

        # Setup FPU flag defaults
        isFPUenabled    = False     # FPU not enabled
        noFpStackFrame  = True      # No FPU stack frame

        # Has processoe an FPU?
        hasFPU = debugSession.symbolExists( "$FPSCR" ) == 1
        if hasFPU:

            # Yes, now check if it's enabled
            CPACR = debugSession.evaluateExpression( "$CPACR" ).readAsNumber( )
            if CPACR & ( 0xF << 20 ):

                # FPU is present and enabled
                isFPUenabled = True

                # Now determine if task has a FPU stack frame by examining the contents of the LR register saved on the stack
                R14addr = stackPointer.addOffset( 32 )      # Offset to LR
                R14val = debugSession.evaluateExpression( "*(long)" + str( R14addr ) ).readAsNumber( )
                noFpStackFrame = R14val & 0x10              # If bit 4 clear its a FPU stack frame

        if not hasFPU:
            # M3 or M4 with no FPU
            regMapName = REG_MAP_V7MBASIC
        elif not isFPUenabled:
            # M4 with FPU, but not enabled
            regMapName = REG_MAP_V7MBASIC
        elif noFpStackFrame:
            # M4 with FPU enabled, but task not using FPU
            regMapName = REG_MAP_V7MEXT
        else:
            # M4 with FPU enabled and task using FPU
            regMapName = REG_MAP_V7MVFP

    # Cortex-A
    else:

        # FPU stack frame indication flag is first word on the stack
        if debugSession.evaluateExpression( "*(long)" + str( stackPointer ) ).readAsNumber( ) == 1:
            # Using FPU
            regMapName = REG_MAP_V7AVFP
        else:
            # Not using FPU
            regMapName = REG_MAP_V7ABASIC

    # Register map name
    return regMapName

def make_reg_list(offset, size, *reg_names):
    result = [("%s" % reg_names[x], long(offset + x*size)) for x in xrange(len(reg_names))]
    return result

def make_reg_range(offset, size, prefix, start, count):
    result = [("%s%d" % (prefix, start+x), long(offset + x*size)) for x in xrange(0, count)]
    return result

# Get FPU status text from map name
def getFPUStatusText( regMapName ):
    return REGMAPNAMES[ regMapName ]

# Create a cell
def createCell( cells, members, itemName, itemFormat, cellType, debugSession ):

    if cellType == ADDRESS:
        cells.append( createAddressCell( getMemberValue( members, itemName, itemFormat, debugSession ) ) )
    elif cellType == DECIMAL:
        cells.append( createNumberCell( getMemberValue( members, itemName, itemFormat, debugSession ) ) )
    else:
        cells.append( createTextCell( getMemberValue( members, itemName, itemFormat, debugSession ) ) )
