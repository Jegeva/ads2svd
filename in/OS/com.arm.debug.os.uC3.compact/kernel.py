# Copyright (C) 2015,2017 Arm Limited (or its affiliates). All rights reserved.

TTS_UNKNOWN = 0x0
# Task states from kernel.h
TTS_RUN = 0x01
TTS_RDY = 0x02
TTS_WAI = 0x04
TTS_DMT = 0x10
# Task states from uC3def.h
TTS_HBT = 0x08
TTS_STK = 0x20
TTS_SLP = 0x40
TTS_TMR = 0x80
# Mapping to printable strings
TASK_STATES = {
    TTS_UNKNOWN: 'task.state.unknown',
    TTS_RUN: 'task.state.run',
    TTS_RDY: 'task.state.ready',
    TTS_WAI: 'task.state.wait',
    TTS_DMT: 'task.state.dormant',
}

# Task wait states from kernel.h
TTW_SLP  = 0x0001
TTW_DLY  = 0x0002
TTW_SEM  = 0x0004
TTW_FLG  = 0x0008
TTW_SDTQ = 0x0010
TTW_RDTQ = 0x0020
TTW_MBX  = 0x0040
TTW_MTX  = 0x0080
TTW_SMBF = 0x0100
TTW_RMBF = 0x0200
TTW_CAL  = 0x0400
TTW_ACP  = 0x0800
TTW_RDV  = 0x1000
TTW_MPF  = 0x2000
TTW_MPL  = 0x4000
TTW_STK  = 0x8000
# Mapping to printable strings
WAIT_STATES = {
    TTW_SLP:  'TTW_SLP',
    TTW_DLY:  'TTW_DLY',
    TTW_SEM:  'TTW_SEM',
    TTW_FLG:  'TTW_FLG',
    TTW_SDTQ: 'TTW_SDTQ',
    TTW_RDTQ: 'TTW_RDTQ',
    TTW_MBX:  'TTW_MBX',
    TTW_MTX:  'TTW_MTX',
    TTW_SMBF: 'TTW_SMBF',
    TTW_RMBF: 'TTW_RMBF',
    TTW_CAL:  'TTW_CAL',
    TTW_ACP:  'TTW_ACP',
    TTW_RDV:  'TTW_RDV',
    TTW_MPF:  'TTW_MPF',
    TTW_MPL:  'TTW_MPL',
    TTW_STK:  'TTW_STK',
}

# Object types from kernel.h
TS_TMR  = 0x00
TS_RDY  = 0x10
TS_STK  = 0x20
TS_CYC  = 0x30
TS_TSK  = 0x40
TS_SEM  = 0x50
TS_FLG  = 0x60
TS_DTQ  = 0x70
TS_DTQ1 = 0x80
TS_MBX  = 0x90
TS_MPF  = 0xA0
# Mapping to printable strings
OBJECT_TYPES = {
    TS_TMR:  'system.items.tmrres',
    TS_RDY:  'system.items.rdyres',
    TS_STK:  'system.items.stkres',
    TS_CYC:  'system.items.cycres',
    TS_TSK:  'system.items.tskres',
    TS_SEM:  'system.items.semres',
    TS_FLG:  'system.items.flgres',
    TS_DTQ:  'system.items.dtqres',
    TS_DTQ1: 'system.items.dtqres',
    TS_MBX:  'system.items.mbxres',
    TS_MPF:  'system.items.mpfres',
}

# Object attributes from kernel.h
# Wait queue attributes
TA_TFIFO  = 0x00
TA_TPRI   = 0x01
# Task attributes
TA_HLNG   = 0x00
TA_USR    = 0x01
TA_ACT    = 0x02
TA_RSTR   = 0x04
TA_FPU    = 0x08
# Mailbox attributes
TA_MFIFO  = 0x00
TA_MPRI   = 0x02
# Eventflag attributes
TA_WSGL   = 0x00
TA_WMUL   = 0x02
TA_CLR    = 0x04
# Mutex attributes
TA_INHERIT= 0x02
TA_CEILING= 0x03
# Cyclic handler attributes
TA_STA    = 0x02
TA_PHS    = 0x04
# Mapping to printable strings
ATTRIBUTES_WQU = {
    TA_TFIFO: 'TA_TFIFO',
    TA_TPRI:  'TA_TPRI',
}
ATTRIBUTES_TSK = {
    TA_HLNG: 'TA_HLNG',
    TA_USR:  'TA_USR',
    TA_ACT:  'TA_ACT',
    TA_RSTR: 'TA_RSTR',
    TA_FPU:  'TA_FPU',
}
ATTRIBUTES_MBX = {
    TA_MFIFO: 'TA_MFIFO',
    TA_MPRI:  'TA_MPRI',
}
ATTRIBUTES_FLG = {
    TA_WSGL: 'TA_WSGL',
    TA_WMUL: 'TA_WMUL',
    TA_CLR:  'TA_CLR',
}
ATTRIBUTES_MTX = {
    TA_INHERIT: 'TA_INHERIT',
    TA_CEILING: 'TA_CEILING',
}
ATTRIBUTES_CYC = {
    TA_STA: 'TA_STA',
    TA_PHS: 'TA_PHS',
}

def readPotentiallyNullString(result):
    """
    @brief  uC3 can sometimes represents empty strings by the NULL pointer, so
            it is necessary to catch this and deal with it safetly.
    @param  result  The ExpressionResult to read as a string.
    @return The string representation of the ExpressionResult given.
    """
    if result.readAsNumber() == 0:
        return ""
    return result.readAsNullTerminatedString()

def getTaskState(systbl, tcb, task_id):
    """
    @brief Queries the state of a task. This implementation echoes that in
           uC3reftsk.c
    @param systbl      The members of the _kernel_systbl structure
    @param tcb         The members of the tasks T_TCB structure
    @param task_id     The id of the task
    @return Returns two values:
            first - The task's state code - a TTS_xxx number.
            second - The key to a localised message representing the state.
    """
    # If we are the current task, return the run state.
    if systbl['run'].readAsNumber() == task_id:
        return TTS_RUN, TASK_STATES[TTS_RUN]

    msts = tcb['msts'].readAsNumber()

    # Shared stacks are always in the wait state.
    if (msts & TTS_STK) != 0:
        return TTS_WAI, TASK_STATES[TTS_WAI]

    # Otherwise derive the state from the 'msts' flag.
    state_code = msts & (TTS_RDY|TTS_WAI|TTS_DMT)
    if state_code in TASK_STATES:
        return state_code, TASK_STATES[state_code]
    else:
        return TTS_UNKNOWN, TASK_STATES[TTS_UNKNOWN]


# TSKWAIT structure only used for determining task wait states. This echoes the
# implementation in uC3reftsk.c
TSKWAIT = [
    TTW_STK,
    0,
    0,
    TTW_SEM,
    TTW_FLG,
    TTW_RDTQ,
    TTW_SDTQ,
    TTW_MBX,
    TTW_MPF,
]
def getTaskWaitState(cnstbl, tcb, task_state):
    """
    @brief Queries the wait state of a task. This implementation echoes that in
           uC3reftsk.c
    @param cnstbl      The members of the _kernel_cnstbl structure
    @param tcb         The task T_TCB object to retrieve data for.
    @param task_state  The task's state code (as returned by getTaskState(...)).
    @return Returns three values:
            first - The corrected wobjid attribute.
            second - The task's waiting state code - a TTW_xxx number.
            third - The key to a localised message representing the wait state.
    """
    # Ensure we are in the wait state
    if task_state != TTS_WAI:
        return None, None, None

    wobjid = tcb['wobjid'].readAsNumber()
    if wobjid != 0:
        # If there is a wait object, get its type and use as an index
        wait_code = TSKWAIT[(cnstbl['atrtbl'].getArrayElement(wobjid).readAsNumber() >> 4) - 2]
        if wait_code == TTW_SDTQ:
            wobjid -= 1
    elif (tcb['msts'].readAsNumber() & TTS_SLP) != 0:
        # If not, check if we are in the sleep state
        wait_code = TTW_SLP
    else:
        # Otherwise we must be in the delay state
        wait_code = TTW_DLY
    return wobjid, wait_code, WAIT_STATES[wait_code]


def getTaskRemainingWaitTime(systbl, cnstbl, tcb):
    """
    @brief Queries the remaining wait time for a task that is in a timed
           wait. This implementation is based on the calculations done in
           uC3reftsk.c:61
    @param systbl  The members of the _kernel_systbl structure
    @param cnstbl  The members of the _kernel_cnstbl structure
    @param tcb     The members of the relevant task's T_TCB structure.
    @return The number of remaining milliseconds the given task will wait, or
            None if the task is not in a timed wait.
    """
    msts = tcb['msts'].readAsNumber()

    # Check we are in a timed-wait state
    if (msts & TTS_TMR) != 0:
        tcb_rtime = tcb['rtime'].readAsNumber()
        sys_ltime = systbl['systim'].getStructureMembers()['ltime'].readAsNumber()
        krnl_tick = cnstbl['tick'].readAsNumber()
        time1 = tcb_rtime - sys_ltime
        time2 = (time1 // krnl_tick) * krnl_tick
        # Deviate slightly from the reference and ensure we cannot return negative values.
        if time1 == time2:
            if time2 < krnl_tick:
                return 0
            else:
                return max(0, time2 - krnl_tick)
        else:
            return max(0, time2)
    # Otherwise we are waiting forever
    return None


def getCyclicHandlerRemainingWaitTime(TCYC_STA, systbl, cnstbl, cyc):
    """
    @brief  Queries the remaining time before a given cyclic handler is next
            activated. This implementation is based on the calculations done in
            uC3refcyc.c:37
    @return The number of remaining milliseconds before the next activation, or
            None if the cyclic handler is not active.
    """
    msts = cyc['msts'].readAsNumber()

    # Check the cyclic handler is enabled
    if (msts & TCYC_STA) != 0:
        cyc_rtime = cyc['rtime'].readAsNumber()
        sys_ltime = systbl['systim'].getStructureMembers()['ltime'].readAsNumber()
        krnl_tick = cnstbl['tick'].readAsNumber()
        time = cyc_rtime - sys_ltime
        time += krnl_tick - 1
        time = (time // krnl_tick) * krnl_tick
        if time != 0:
            time -= krnl_tick
        # Deviate slightly from the reference and ensure we cannot return negative values.
        return max(0, time)
    # Otherwise no remaining time to calculate
    return None


def getFIFOWaitingQueue(cnstbl, id):
    """
    @brief   Returns a string representation of the OS object given by id.
    @param cnstb   The members of the _kernel_cnstbl structure
    @param id      The id number of the object whose wait queue will be extracted.
    @return  A string of comma separated ids of objects waiting on the given id.
    """
    queue = []
    curr_id = id
    next_id = cnstbl['waique'].getArrayElement(curr_id).getStructureMembers()['nid'].readAsNumber()
    while next_id != id:
        queue.append(str(next_id))
        curr_id = next_id
        next_id = cnstbl['waique'].getArrayElement(curr_id).getStructureMembers()['nid'].readAsNumber()
    return ', '.join(queue)

def getFIFOMessageQueue(mbx):
    """
    @brief Converts a FIFO-ordered message queue into a string.
    @param mbx  The members of the T_MBX structure whose message queue is to
                be retrieved.
    @return The start address of the queue and a string representation of it.
    """
    mem_ptr = mbx['top']
    # We could print the entire queue, but that will get very long very quickly.
    # Instead we choose to print just the start address and number of items.
    queued_messages = getInternalMessageQueue(mem_ptr)
    first_addr = None
    if len(queued_messages) > 0:
        first_addr = queued_messages[0]
    return first_addr, len(queued_messages)

def getInternalMessageQueue(mem_ptr):
    """
    @brief  Converts an internal T_MEM type message header message queue (which
            is in FIFO order) into a list of the queued start addresses.
    @param  mem_ptr  A T_MEM* type message header object.
    @return A list of addresses representing each of the queued message's
            starting addresses. This will be in FIFO order, with the next
            address to be selected as the first element.
    """
    queuedObjs = []
    next = mem_ptr
    next_addr = next.readAsAddress()
    # Read through all elements in the queue until we find an element which
    # points back to the start. The way the queues are structured the final
    # element will have zero in the next pointer field.
    while next_addr.getLinearAddress() != 0:
        queuedObjs.append(next_addr)
        next = next.dereferencePointer().getStructureMembers()['next']
        next_addr = next.readAsAddress()
    return queuedObjs
