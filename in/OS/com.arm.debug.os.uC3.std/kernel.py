# Copyright (C) 2015,2017 Arm Limited (or its affiliates). All rights reserved.

TTS_UNKNOWN = 0x0
# Task states from kernel.h
TTS_RUN = 0x01
TTS_RDY = 0x02
TTS_WAI = 0x04
TTS_SUS = 0x08
TTS_WAS = 0x0C
TTS_DMT = 0x10
# Task states from uC3def.h
TTS_FIFO = 0x20
TTS_TMR =  0x80
# Mapping to printable strings
TASK_STATES = {
    TTS_RUN: 'task.state.run',
    TTS_RDY: 'task.state.ready',
    TTS_WAI: 'task.state.wait',
    TTS_SUS: 'task.state.suspend',
    TTS_WAS: 'task.state.waitsus',
    TTS_DMT: 'task.state.dormant',
    TTS_FIFO:'task.state.fifo',
    TTS_TMR: 'task.state.timer',
    TTS_UNKNOWN: 'task.state.unknown'
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
}

# Object attributes from kernel.h
# Wait queue attributes
TA_TFIFO  = 0x00
TA_TPRI   = 0x01
# Task attributes
TA_HLNG   = 0x00
TA_ASM    = 0x01
TA_ACT    = 0x02
TA_RSTR   = 0x04
TA_AUX    = 0x10
TA_DSP    = 0x20
TA_FPU    = 0x40
TA_VPU    = 0x80
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
    TA_ASM:  'TA_ASM',
    TA_ACT:  'TA_ACT',
    TA_RSTR: 'TA_RSTR',
    TA_AUX:  'TA_AUX',
    TA_DSP:  'TA_DSP',
    TA_FPU:  'TA_FPU',
    TA_VPU:  'TA_VPU',
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


def getTaskState(systbl, tcb_addr, tcb_status):
    """
    @brief Queries the state a task
    @param systbl      The members of the systbl structure
    @param tcb_addr    The address of the task P_TCB structure
    @param tcb_status  The members of the 'stat' structure in the task's T_TCB
                       structure
    @return A tuple containing the code of the task's state and the key
            to a localised message representing the state
    """
    # If we are the current task, return the run state.
    if systbl['ctcb'].readAsNumber() == tcb_addr:
        return TTS_RUN, TASK_STATES[TTS_RUN]

    msts = tcb_status['msts'].readAsNumber()

    # Otherwise derive the state from the 'msts' flag.
    state_code = msts & (TTS_DMT|TTS_WAS|TTS_SUS|TTS_WAI|TTS_RDY|TTS_RUN)
    if state_code in TASK_STATES:
        return state_code, TASK_STATES[state_code]
    else:
        return TTS_UNKNOWN, TASK_STATES[TTS_UNKNOWN]


# TSKWAIT structure only used for determining task wait states. This echoes the
# implementation of ttw_table in uC3reftsk.c
TSKWAIT = [
    TTW_SLP,
    TTW_DLY,
    TTW_RDV,
    TTW_SEM,
    TTW_FLG,
    TTW_SDTQ,
    TTW_RDTQ,
    TTW_MBX,
    TTW_MTX,
    TTW_SMBF,
    TTW_RMBF,
    TTW_CAL,
    TTW_ACP,
    TTW_MPF,
    TTW_MPL,
]
def getTaskWaitState(tcb, tcb_status, task_state):
    """
    @brief Queries the wait state of a task. This implementation echoes that in
           uC3reftsk.c.
    @param tcb         The task T_TCB object to retrieve data for.
    @param tcb_status  The members of the 'stat' structure in the task's T_TCB
                       structure.
    @param task_state  The task's state code (as returned by getTaskState(...)).
    @return Returns three values:
            first - The wobjid attribute.
            second - The task's waiting state code - a TTW_xxx number.
            third - The key to a localised message representing the wait state.
    """
    # Ensure we are in the wait state
    if task_state != TTS_WAI:
        return None, None, None

    wsts = tcb_status['wsts'].readAsNumber()
    wait_code = TSKWAIT[wsts - 1]
    wobjid = tcb['wobjid'].readAsNumber()

    return wobjid, wait_code, WAIT_STATES[wait_code]


def getTaskRemainingWaitTime(systbl, tcb, tcb_status):
    """
    @brief Queries the remaining wait time for a task that is in a timed
           wait. This implementation is based on the calculations done in
           uC3reftsk.c:39
    @param systbl      The members of the systbl structure.
    @param tcb         The task T_TCB object to retrieve data for.
    @param tcb_status  The members of the 'stat' structure in the task's T_TCB
                       structure.
    @return The number of remaining milliseconds the given task will wait, or
            None if the task is not in a timed wait
    """
    msts = tcb_status['msts'].readAsNumber()

    # Check we are in a timed-wait state
    if msts & TTS_TMR:
        tcb_ltime = tcb['stime'].getStructureMembers()['ltime'].readAsNumber()
        sys_ltime = systbl['systim'].getStructureMembers()['ltime'].readAsNumber()
        sys_tick = systbl['tick'].readAsNumber()

        lefttmo = tcb_ltime - sys_ltime - 1
        lefttmo = lefttmo - (lefttmo % sys_tick)
        # Deviate slightly from the reference and ensure we cannot return negative values.
        return max(0, lefttmo)
    # Otherwise we are waiting forever
    return None


def getCyclicHandlerRemainingWaitTime(TCYC_STA, systbl, cyc, cyc_msts):
    """
    @brief  Queries the remaining time before a given cyclic handler is next
            activated. This implementation is based on the calculations done in
            uC3refcyc.c:32
    @param  TCYC_STA  The value of the TCYC_STA constant (this is not stored globally).
    @param  systbl    The members of the systbl structure.
    @param  cyc       The members of the T_TCYC structure.
    @param  cyc_msts  The value of cyc['stat'].getStructureMembers()['msts'].
    @return The number of remaining milliseconds before the next activation, or
            None if the cyclic handler is not active.
    """
    # Check the cyclic handler is enabled
    if (cyc_msts & TCYC_STA) != 0:
        cyc_ltime = cyc['stime'].getStructureMembers()['ltime'].readAsNumber()
        sys_ltime = systbl['systim'].getStructureMembers()['ltime'].readAsNumber()
        sys_tick = systbl['tick'].readAsNumber()

        lefttim = cyc_ltime - sys_ltime - 1
        lefttim = lefttim - (lefttim % sys_tick)
        # Deviate slightly from the reference and ensure we cannot return negative values.
        return max(0, lefttim)
    # Otherwise no remaining time to calculate
    return None


def getAlarmHandlerRemainingWaitTime(TALM_STA, TALM_RST, systbl, alm, alm_msts):
    """
    @brief  Queries the remaining time before a given alarm handler is next
            activated. This implementation is based on the calculations done in
            uC3refalm.c:32
    @param  TALM_STA  The value of the TALM_STA constant (this is not stored globally).
    @param  TALM_RST  The value of the TALM_RST constant (this is not stored globally).
    @param  systbl    The members of the systbl structure.
    @param  alm       The members of the T_TALM structure.
    @param  cyc_msts  The value of ALM['stat'].getStructureMembers()['msts'].
    @return The number of remaining milliseconds before the next activation, or
            None if the alarm handler is not active.
    """
    # Check the alarm handler is enabled
    if (alm_msts & TALM_STA) != 0:
        alm_ltime = alm['stime'].getStructureMembers()['ltime'].readAsNumber()
        sys_ltime = systbl['systim'].getStructureMembers()['ltime'].readAsNumber()
        sys_tick = systbl['tick'].readAsNumber()

        lefttim = alm_ltime - sys_ltime - 1
        lefttim = lefttim - (lefttim % sys_tick)
        # Deviate slightly from the reference and ensure we cannot return negative values.
        return max(0, lefttim)
    elif (alm_msts & TALM_RST) != 0:
        alm_ltime = alm['stime'].getStructureMembers()['ltime'].readAsNumber()
        return max(0, alm_ltime)
    # Otherwise no remaining time to calculate
    return None


def getWaitingQueueIsFIFO(debugger, queue_attribute):
    """
    @brief  Queries whether or not the queue with the specified attribute is
            FIFO-ordered or not (in which case it will be Priority-ordered).
    @param  queue_attribute  The attribute flag for the queue to check.
    @return True if the queue is FIFO, False otherwise.
    """
    return (queue_attribute & TA_TPRI) == 0


def getPriorityWaitingQueue(systbl, queue_obj):
    """
    @brief  Converts a Priority-ordered waiting queue into a string.
            A queue can be either FIFO-ordered or Priority-ordered. Its type
            can be derived using the getWaitingQueueIsFIFO(...) function. This
            function will NOT check it is the right type.
    @param  systbl      The _kernel_systbl structure.
    @param  queue_obj   A T_TPRI type queue object.
    @return The string representation of the queue.
    """
    priority_strings = []
    queue = queue_obj.getStructureMembers()
    priority_max = systbl['qrdq'].getStructureMembers()['inf'].dereferencePointer().getStructureMembers()['limit'].readAsNumber()
    wtcbs = queue['mwait'].getArrayElements(priority_max+1)
    for index in range(1, priority_max+1):
        wtcb = wtcbs[index]
        queue_result = getInternalWaitingQueue(wtcb)
        if len(queue_result) > 0:
            priority_strings.append(', '.join(queue_result))
    return ', '.join(priority_strings)


def getFIFOWaitingQueue(systbl, queue_obj):
    """
    @brief  Converts a FIFO-ordered waiting queue into a string.
            A queue can be either FIFO-ordered or Priority-ordered. Its type
            can be derived using the getWaitingQueueIsFIFO(...) function. This
            function will NOT check it is the right type.
    @param  systbl      The _kernel_systbl structure.
    @param  queue_obj   A T_TPRI type queue object.
    @return The string representation of the queue.
    """
    wtcb = queue_obj.getStructureMembers()['wait']
    return ', '.join(getInternalWaitingQueue(wtcb))


def getInternalWaitingQueue(wtcb_obj):
    """
    @brief  Converts an internal T_WTCB type task waiting queue (which is in
            FIFO order) into a list of the waiting-tasks' IDs.
    @param  wtcb_obj    A T_WTCB type waiting task object.
    @return A list of numbers representing each of the waiting-tasks' IDs. This
            will be in FIFO order, with the next ID to be selected as the first
            element.
    """
    queuedObjs = []
    wtcb = wtcb_obj.getStructureMembers()
    wtcb_addr = wtcb_obj.getLocationAddress().getLinearAddress()
    # Read through all elements in the queue until we find an element which
    # points back to the start. The way the queues are structured there is
    # always a 'stop' element at the end pointing to the start, but all other
    # elements are valid. This means the list will always have n+1 elements
    # for n-waiting tasks.
    # Because the first item of every T_TCB is a T_WTCB, we can cast from a
    # T_WTCB* straight to a T_TCB* to get the associated task structure.
    while (wtcb['next'].readAsAddress().getLinearAddress() != wtcb_addr):
        tcb = wtcb['next'].dereferencePointer("T_TCB*").getStructureMembers()
        queuedObjs.append(str(tcb['tskid'].readAsNumber()))
        wtcb = wtcb['next'].dereferencePointer().getStructureMembers()
    return queuedObjs


def getMessageQueueIsFIFO(debugger, attributes):
    return (attributes & TA_MPRI) == 0


def getPriorityMessageQueue(systbl, queue_obj):
    """
    @brief  Converts a Priority-ordered message queue into a string.
            A message queue's type can be derived using the getWaitingQueueIsFIFO(...)
            function. This function will NOT check it is the right type.
    @param  systbl      The _kernel_systbl structure.
    @param  queue_obj   A T_MPRI type queue object.
    @return The maximum priority of the queue, the start address of the queue
            and a string representation of it.
    """
    priority_strings = []
    mmhd = queue_obj.getStructureMembers()['mult'].getStructureMembers()
    priority_max = mmhd['maxmpri'].readAsNumber()
    mhds = mmhd['mque'].getArrayElements(priority_max+1)
    first_addr = None
    for index in range(1, priority_max+1):
        mhd = mhds[index]
        queued_messages = getInternalMessageQueue(mhd)
        if first_addr == None and len(queued_messages) > 0:
            first_addr = queued_messages[0]
        priority_strings.append("%d: (%d)" % (index, len(queued_messages)))
    return priority_max, first_addr, ', '.join(priority_strings)


def getFIFOMessageQueue(systbl, queue_obj):
    """
    @brief  Converts a FIFO-ordered message queue into a string.
            A message queue's type can be derived using the getWaitingQueueIsFIFO(...)
            function. This function will NOT check it is the right type.
    @param  systbl      The _kernel_systbl structure.
    @param  queue_obj   A T_MPRI type queue object.
    @return The maximum priority of the queue (always 0 for a FIFO queue), the
            start address of the queue and a string representation of it.
    """
    mhd = queue_obj.getStructureMembers()['sngl']
    # We could print the entire queue, but that will get very long very quickly.
    # Instead we choose to print just the start address and number of items.
    queued_messages = getInternalMessageQueue(mhd)
    first_addr = None
    if len(queued_messages) > 0:
        first_addr = queued_messages[0]
    return None, first_addr, str(len(queued_messages))


def getInternalMessageQueue(mhd_obj):
    """
    @brief  Converts an internal T_MHD type message header message queue (which
            is in FIFO order) into a list of the queued start addresses.
    @param  mhd_obj     A T_MHD type message header object.
    @return A list of addresses representing each of the queued message's
            starting addresses. This will be in FIFO order, with the next
            address to be selected as the first element.
    """
    queuedObjs = []
    mhd = mhd_obj.getStructureMembers()
    next = mhd['top']
    next_addr = next.readAsAddress()
    # Read through all elements in the queue until we find an element which
    # points back to the start. The way the queues are structured the final
    # element will have zero in the next pointer field.
    while next_addr.getLinearAddress() != 0:
        queuedObjs.append(next_addr)
        next = next.dereferencePointer().getStructureMembers()['msgque']
        next_addr = next.readAsAddress()
    return queuedObjs


def getQueueInf(systbl, queue_member):
    """
    @brief  Reads a queue from the _kernel_systbl structure and returns the T_INF
            details about the limit and used count of the queue.
    @param  systbl         The _kernel_systbl structure
    @param  queue_member   The name of the queue member to read
    @return A tuple containing the used count and limit of the requested queue
    """
    queue = systbl[queue_member]
    if queue.readAsNumber() == 0:
        return (0, 0)
    t_inf = queue.getStructureMembers()['inf'].dereferencePointer().getStructureMembers()
    return (t_inf['usedc'].readAsNumber(), t_inf['limit'].readAsNumber())


def getFreeMem(memory):
    """
    @brief  Reads the amount of free memory in a memory pool.
    @param  memory   The pointer of the T_MEM structure to count free memory
    @return The count of the free memory in the given memory structure and the
            maximum contiguous block of free memory.
    """
    total_free = 0
    max_contiguous = 0
    blk = memory
    while blk.readAsNumber() != 0:
        blk_members = blk.dereferencePointer().getStructureMembers()
        free = blk_members['size'].readAsNumber()
        total_free += free
        max_contiguous = max(free, max_contiguous)
        blk = blk_members['next']
    return total_free, max_contiguous