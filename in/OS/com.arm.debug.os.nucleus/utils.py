################################################################################
#
# Copyright (C) 2014,2017 Arm Limited (or its affiliates). All rights reserved.
#
#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

from osapi import *

NO      = 0
YES     = 1

NOYES_TEXT = \
{
    NO:  "NO",
    YES: "YES"
}

NU_READY                    = 0
NU_PURE_SUSPEND             = 1
NU_SLEEP_SUSPEND            = 2
NU_MAILBOX_SUSPEND          = 3
NU_QUEUE_SUSPEND            = 4
NU_PIPE_SUSPEND             = 5
NU_SEMAPHORE_SUSPEND        = 6
NU_EVENT_SUSPEND            = 7
NU_PARTITION_SUSPEND        = 8
NU_MEMORY_SUSPEND           = 9
NU_SCHEDULED                = 10
NU_FINISHED                 = 11
NU_TERMINATED               = 12
NU_DEBUG_SUSPEND            = 13
NU_ERROR_SUSPEND            = 14

TASK_STATES = \
{
    NU_READY                    : "READY",
    NU_PURE_SUSPEND             : "PURE SUSPEND",
    NU_SLEEP_SUSPEND            : "SLEEP SUSPEND",
    NU_MAILBOX_SUSPEND          : "MAILBOX SUSPEND",
    NU_QUEUE_SUSPEND            : "QUEUE SUSPEND",
    NU_PIPE_SUSPEND             : "PIPE SUSPEND",
    NU_SEMAPHORE_SUSPEND        : "SEMA SUSPEND",
    NU_EVENT_SUSPEND            : "EVENT SUSPEND",
    NU_PARTITION_SUSPEND        : "PART SUSPEND",
    NU_MEMORY_SUSPEND           : "MEMORY SUSPEND",
    NU_SCHEDULED                : "SCHEDULED",
    NU_FINISHED                 : "FINSIHED",
    NU_TERMINATED               : "TERMINATED",
    NU_DEBUG_SUSPEND            : "DEBUG SUSPEND",
    NU_ERROR_SUSPEND            : "ERROR SUSPEND"
}

TM_TASK_TIMER = 0
TM_APPL_TIMER = 1

TIMER_TYPE_TEXT = \
{
    TM_TASK_TIMER   : "TASK",
    TM_APPL_TIMER   : "APPL"
}

EV_CONSUME  = 1
EV_AND      = 2

EV_OPER_TEST = \
{
    EV_CONSUME  : "CONSUME",
    EV_AND      : "AND"
}

NU_AND                 = 2
NU_AND_CONSUME         = 3
NU_DISABLE_TIMER       = 4
NU_ENABLE_TIMER        = 5
NU_FIFO                = 6
NU_FIXED_SIZE          = 7
NU_NO_PREEMPT          = 8
NU_NO_START            = 9
NU_NO_SUSPEND          = 0
NU_OR                  = 0
NU_OR_CONSUME          = 1
NU_PREEMPT             = 10
NU_PRIORITY            = 11
NU_START               = 12
NU_SUSPEND             = 0xFFFFFFFFL
NU_VARIABLE_SIZE       = 13
NU_PRIORITY_INHERIT    = 14

NU_SERVICE_TEXT = \
{
    NU_AND                 : "AND",
    NU_AND_CONSUME         : "AND CONSUME",
    NU_DISABLE_TIMER       : "DISABLE TIMER",
    NU_ENABLE_TIMER        : "ENABLE TIMER",
    NU_FIFO                : "FIFO",
    NU_FIXED_SIZE          : "FIXED SIZE",
    NU_NO_PREEMPT          : "NO PREEMPT",
    NU_NO_START            : "NO START",
    NU_NO_SUSPEND          : "NO SUSPEND",
    NU_OR                  : "OR",
    NU_OR_CONSUME          : "OR CONSUME",
    NU_PREEMPT             : "PREEMPT",
    NU_PRIORITY            : "PRIORITY",
    NU_START               : "START",
    NU_SUSPEND             : "SUSPEND",
    NU_VARIABLE_SIZE       : "VARIABLE SIZE",
    NU_PRIORITY_INHERIT    : "PRIORITY INHERIT"
}

PROC_CREATED_STATE          = 0
PROC_LOADING_STATE          = 1
PROC_STARTING_STATE         = 2
PROC_DEINITIALIZING_STATE   = 3
PROC_STOPPING_STATE         = 4
PROC_UNLOADING_STATE        = 5
PROC_KILLING_STATE          = 6
PROC_STOPPED_STATE          = 7
PROC_STARTED_STATE          = 8
PROC_FAILED_STATE           = 9

PROC_STATES = \
{
    PROC_CREATED_STATE          : "CREATED",
    PROC_LOADING_STATE          : "LOADING",
    PROC_STARTING_STATE         : "STARTING",
    PROC_DEINITIALIZING_STATE   : "DEINITIALIZING",
    PROC_STOPPING_STATE         : "STOPPING",
    PROC_UNLOADING_STATE        : "UNLOADING",
    PROC_KILLING_STATE          : "KILLING",
    PROC_STOPPED_STATE          : "STOPPED",
    PROC_STARTED_STATE          : "STARTED",
    PROC_FAILED_STATE           : "FAILED"
}

def checkObjectPtr( expr, debugSession ):
    return debugSession.evaluateExpression( expr ).readAsNumber( )

def getObjectPtr( expr, struct, debugSession ):
    if not debugSession.symbolExists( expr ):
        return None
    ptr = debugSession.evaluateExpression( expr ).readAsNumber( )
    if ptr == 0:
        return None
    return debugSession.evaluateExpression( "(" + struct + "*)(" + hex( ptr ) + ")" )

def getNextObjectPtr( ptr, struct, member, debugSession ):
    members = ptr.dereferencePointer( ).getStructureMembers( )
    tcCreated = members[ member ]
    nextPtr = tcCreated.getStructureMembers( )[ "cs_next" ].readAsNumber( )
    return debugSession.evaluateExpression( "(" + struct + "*)(" + hex( nextPtr ) + ")" )

def getCurrentTask( debugSession ):
    return getObjectPtr( "TCD_Execute_Task", "TC_TCB", debugSession )

def getFirstTask( debugSession ):
    return getObjectPtr( "TCD_Created_Tasks_List", "TC_TCB", debugSession )

def getNextTask( ptr, debugSession ):
    return getNextObjectPtr( ptr, "TC_TCB", "tc_created", debugSession )

def getFirstProcess( debugSession ):
    return getObjectPtr( "PROC_Created_List", "PROC_CB", debugSession )

def getNextProcess( ptr, debugSession ):
    return getNextObjectPtr( ptr, "PROC_CB", "created", debugSession )

def getFirstHisr( debugSession ):
    return getObjectPtr( "TCD_Created_HISRs_List", "TC_HCB", debugSession )

def getNextHisr( ptr, debugSession ):
    return getNextObjectPtr( ptr, "TC_HCB", "tc_created", debugSession )

def getFirstTimer( debugSession ):
    return getObjectPtr( "TMD_Created_Timers_List", "TM_APP_TCB", debugSession )

def getNextTimer( ptr, debugSession ):
    return getNextObjectPtr( ptr, "TM_APP_TCB", "tm_created", debugSession )

def getFirstDynamic( debugSession ):
    return getObjectPtr( "DMD_Created_Pools_List", "DM_PCB", debugSession )

def getNextDynamic( ptr, debugSession ):
    return getNextObjectPtr( ptr, "DM_PCB", "dm_created", debugSession )

def getNextDynsus( ptr, debugSession ):
    return getNextObjectPtr( ptr, "DM_SUSPEND", "dm_suspend_link", debugSession )

def checkMailbox( debugSession ):
    objListName = "MBD_Created_Mailboxes_List"
    return debugSession.symbolExists( objListName ) and checkObjectPtr( objListName, debugSession )

def getFirstMailbox( debugSession ):
    return getObjectPtr( "MBD_Created_Mailboxes_List", "MB_MCB", debugSession )

def getNextMailbox( ptr, debugSession ):
    return getNextObjectPtr( ptr, "MB_MCB", "mb_created", debugSession )

def getNextMailboxsus( ptr, debugSession ):
    return getNextObjectPtr( ptr, "MB_SUSPEND", "mb_suspend_link", debugSession )

def getFirstPipe( debugSession ):
    return getObjectPtr( "PID_Created_Pipes_List", "PI_PCB", debugSession )

def getNextPipe( ptr, debugSession ):
    return getNextObjectPtr( ptr, "PI_PCB", "pi_created", debugSession )

def getNextPipesus( ptr, debugSession ):
    return getNextObjectPtr( ptr, "PI_SUSPEND", "pi_suspend_link", debugSession )

def getFirstPartition( debugSession ):
    return getObjectPtr( "PMD_Created_Pools_List", "PM_PCB", debugSession )

def getNextPartition( ptr, debugSession ):
    return getNextObjectPtr( ptr, "PM_PCB", "pm_created", debugSession )

def getNextPartitionSus( ptr, debugSession ):
    return getNextObjectPtr( ptr, "PM_SUSPEND", "pm_suspend_link", debugSession )

def getFirstEventGroup( debugSession ):
    return getObjectPtr( "EVD_Created_Event_Groups_List", "EV_GCB", debugSession )

def getNextEventGroup( ptr, debugSession ):
    return getNextObjectPtr( ptr, "EV_GCB", "ev_created", debugSession )

def getNextEvgrpsus( ptr, debugSession ):
    return getNextObjectPtr( ptr, "EV_SUSPEND", "ev_suspend_link", debugSession )

def getFirstQueue( debugSession ):
    return getObjectPtr( "QUD_Created_Queues_List", "QU_QCB", debugSession )

def getNextQueue( ptr, debugSession ):
    return getNextObjectPtr( ptr, "QU_QCB", "qu_created", debugSession )

def getNextQuesus( ptr, struct, member, debugSession ):
    return getNextObjectPtr( ptr, struct, member, debugSession )

def getFirstSemaphore( debugSession ):
    return getObjectPtr( "SMD_Created_Semaphores_List", "SM_SCB", debugSession )

def getNextSemaphore( ptr, debugSession ):
    return getNextObjectPtr( ptr, "SM_SCB", "sm_created", debugSession )

def getNextSemasus( ptr, debugSession ):
    return getNextObjectPtr( ptr, "SM_SUSPEND", "sm_suspend_link", debugSession )

def getFirstSpinlock(debugSession):
    return getObjectPtr("SLD_Created_Spinlocks_List", "SL_SCB", debugSession)

def getNextSpinlock(ptr, debugSession):
    return getNextObjectPtr(ptr, "SL_SCB", "sl_created", debugSession)

def longToHex( number ):
    return '0x%08X' % number

def getTaskStatusText( status ):
    return TASK_STATES[ status ]

def getProcStatusText( status ):
    return PROC_STATES[ status ]

def getNoYesText( status ):
    return NOYES_TEXT[ status ]

def getTimerTypeText( type ):
    return TIMER_TYPE_TEXT[ type ]

def getEvOperText( oper ):
    return EV_OPER_TEST[ oper ]

def getServiceText( service ):
    return NU_SERVICE_TEXT[ service ]

def addressExprsToLong( expr ):
    addr = expr.getLocationAddress( )
    return addr.getLinearAddress( )

def isTaskInterruptFrame( tcbMembers, debugSession ):
    stackPtr = tcbMembers[ "tc_stack_pointer" ].readAsNumber( )
    return debugSession.evaluateExpression( "*(unsigned long*)" + hex( stackPtr ) ).readAsNumber( ) == 1

def getStructureName( cbPtr, itemName, defName="" ):
    name = defName
    if cbPtr.readAsNumber( ):
        cbMembers = cbPtr.dereferencePointer( ).getStructureMembers( )
        if itemName in cbMembers:
            name = cbMembers[ itemName ].readAsNullTerminatedString( )
    return name

def strFun(val, default="N/A") :
    if val == None:
        return createTextCell(default)
    else:
        return createTextCell(val.readAsNullTerminatedString())

def intFun(val, default=-1) :
    if val == None:
        return createNumberCell(default)
    else:
        return createNumberCell(val.readAsNumber())

def addrFun(val, default=None) :
    if val == None:
        return createAddressCell(default)
    else:
        return createAddressCell(val.readAsAddress())

def addrOfFun(val, default=None) :
    if val == None:
        return createAddressCell(default)
    else:
        return createAddressCell(val.getLocationAddress())

def enumFun(enumVals, val):
    index = -1
    if val != None:
        index = val.readAsNumber()
    result = None
    if index in enumVals:
        result = enumVals[index]
    else:
       result = str(index)
    return createTextCell(result)

def addIfPresent(cells, cbMembers, name, resultBuilder):
    if name in cbMembers:
        cells.append(resultBuilder(cbMembers[name]))
    else:
        cells.append(resultBuilder(None))

def listIter(debugSession, firstFunc, nextFunc):
    firstPtr = firstFunc(debugSession)
    if firstPtr == None or firstPtr.readAsNumber() == 0:
        return
    else:
        yield firstPtr
    harePtr = nextFunc(firstPtr, debugSession)
    tortoisePtr = firstPtr
    advanceTortoise = False
    while harePtr.readAsNumber() != firstPtr.readAsNumber() and\
          harePtr.readAsNumber() != tortoisePtr.readAsNumber() and\
          harePtr.readAsNumber() != 0 :
        yield harePtr
        harePtr = nextFunc(harePtr, debugSession)
        if(advanceTortoise):
            tortoisePtr = nextFunc(tortoisePtr, debugSession)
        advanceTortoise = not advanceTortoise

