# Copyright (C) 2017 Arm Limited (or its affiliates). All rights reserved.

# P4k_thr_state_t enum definitions. This differs for 4.1 and 4.2.
P41_PS_READY         =  0
P41_PS_HELP_IPC_TX   =  1
P41_PS_HELP_IPC_RX   =  2
P41_PS_HELP_FINISH   =  3
P41_PS_HELP_EXCHANGE =  4
P41_PS_HELP_PUSH     =  5
P41_PS_HELP_PSP      =  6
P41_PS_WAIT_RX       =  7
P41_PS_WAIT_RX_EV    =  8
P41_PS_WAIT_TX       =  9
P41_PS_WAIT_INT      = 10
P41_PS_WAIT_EVENT    = 11
P41_PS_WAIT_PSP      = 12
P41_PS_WAIT_ULOCK    = 13
P41_PS_WAIT_START    = 14
P41_PS_SLEEPING      = 15
P41_PS_STOPPED       = 16

P42_PS_CURRENT       =  0
P42_PS_READY         =  1
P42_PS_HELP_IPC      =  2
P42_PS_HELP_FINISH   =  3
P42_PS_HELP_UNREF    =  4
P42_PS_HELP_EXCHANGE =  5
P42_PS_HELP_PUSH     =  6
P42_PS_HELP_MUTEX    =  7
P42_PS_HELP_GLOCK    =  8
P42_PS_WAIT_RX       =  9
P42_PS_WAIT_RX_EV    = 10
P42_PS_WAIT_TX       = 11
P42_PS_WAIT_INT      = 12
P42_PS_WAIT_EVENT    = 13
P42_PS_WAIT_GLOCK    = 14
P42_PS_WAIT_PSP      = 15
P42_PS_WAIT_ULOCK    = 16
P42_PS_WAIT_WAITQ    = 17
P42_PS_WAIT_START    = 18
P42_PS_WAIT_HM       = 19
P42_PS_SLEEPING      = 20
P42_PS_STOPPED       = 21


# The 4.1 kernel uses 17 discrete thread states, and the 4.2 uses 22, but the
# documentation for both only describes 5. Map the kernel's internal states
# down onto those described in the docs (PikeOS User Manual 2.4.2). The
# kernel's internal states are described in somewhat more detail in PikeOS
# Kernel Manual 1.15.4.
P41_THREAD_STATES = {
    P41_PS_READY:          'READY',
    P41_PS_HELP_IPC_TX:    'WAITING',
    P41_PS_HELP_IPC_RX:    'WAITING',
    P41_PS_HELP_FINISH:    'WAITING',
    P41_PS_HELP_EXCHANGE:  'WAITING',
    P41_PS_HELP_PUSH:      'WAITING',
    P41_PS_HELP_PSP:       'WAITING',
    P41_PS_WAIT_RX:        'WAITING',
    P41_PS_WAIT_RX_EV:     'WAITING',
    P41_PS_WAIT_TX:        'WAITING',
    P41_PS_WAIT_INT:       'WAITING',
    P41_PS_WAIT_EVENT:     'WAITING',
    P41_PS_WAIT_PSP:       'WAITING',
    P41_PS_WAIT_ULOCK:     'WAITING',
    P41_PS_WAIT_START:     'WAITING',
    P41_PS_SLEEPING:       'INACTIVE',
    P41_PS_STOPPED:        'STOPPED',
}
P42_THREAD_STATES = {
    P42_PS_CURRENT:         'CURRENT',
    P42_PS_READY:           'READY',
    P42_PS_HELP_IPC:        'WAITING',
    P42_PS_HELP_FINISH:     'WAITING',
    P42_PS_HELP_UNREF:      'WAITING',
    P42_PS_HELP_EXCHANGE:   'WAITING',
    P42_PS_HELP_PUSH:       'WAITING',
    P42_PS_HELP_MUTEX:      'WAITING',
    P42_PS_HELP_GLOCK:      'WAITING',
    P42_PS_WAIT_RX:         'WAITING',
    P42_PS_WAIT_RX_EV:      'WAITING',
    P42_PS_WAIT_TX:         'WAITING',
    P42_PS_WAIT_INT:        'WAITING',
    P42_PS_WAIT_EVENT:      'WAITING',
    P42_PS_WAIT_GLOCK:      'WAITING',
    P42_PS_WAIT_PSP:        'WAITING',
    P42_PS_WAIT_ULOCK:      'WAITING',
    P42_PS_WAIT_WAITQ:      'WAITING',
    P42_PS_WAIT_START:      'WAITING',
    P42_PS_WAIT_HM:         'WAITING',
    P42_PS_SLEEPING:        'INACTIVE',
    P42_PS_STOPPED:         'STOPPED',
}


def getStructureElementOffset(debugger, structure_type, structure_element):
    """Calculates the byte offset of an element within a structure.

    Parameters:
        debugger:           IDebugSession object.
        structure_type:     string type of the structure being listed (e.g. P4k_thrinfo_t).
        structure_element:  string name of the element to access in the structure.
    Returns:
        int offset of structure_element within structure_type. Will be >= 0.
    """
    struct = debugger.constructPointer(structure_type, 0).dereferencePointer().getStructureMembers()
    return struct[structure_element].getLocationAddress().getLinearAddress()

def getThreadState(state_code, is_current_thread, is_pikeos_42):
    """Returns a string representation of a state code.

    Parameters:
        state_code:        int state code (P4k_thr_state_t).
        is_current_thread: boolean, true if this thread is the 'current' one. This cannot be
                           calculated from the state code.
        is_pikeos_42:      boolean, true if the PikeOS image is a v4.2 image.
    Returns:
        string identifier for the localised state code message.
    """
    if is_current_thread:
        return 'CURRENT'
    if is_pikeos_42:
        return P42_THREAD_STATES[state_code]
    else:
        return P41_THREAD_STATES[state_code]

def decodeUID(uid):
    """Extracts the Thread ID, Task ID, Resource Partition ID and Time Partition ID from a UID.

    Parameters:
        uid:    int representation of a thread's UID.
    Returns:
        4 return values (in order): Thread ID, Task ID,  Resource Partition ID, Time Partition ID.
    """
    # This is derived from PikeOS User Manual Appendix A
    # Maximum of 511 (0x1ff) threads stored in bottom 9 bits
    threadno = uid & 0x1ff
    # Maximum of 2047 (0x7ff) tasks stored in next 11 bits
    taskno = (uid >> 9) & 0x7ff
    # Maximum of 63 (0x3f) resource partitions stored in next 6 bits
    respart = (uid >> 20) & 0x3f
    # Maximum of 63 (0x3f) time partitions stored in final 6 bits
    timepart = (uid >> 26) & 0x3f
    return threadno, taskno, respart, timepart

def readOffsetList(debugger, list, list_offset, listed_type):
    """Reads a list of structures embedded within the structure.

    PikeOS uses an offset element within its structures to represent lists of the structure (e.g.
    tasks and threads). This function facilitates the reading of such a structure.

    Parameters:
        list:           IExpressionResult of the list in question (i.e. containing adt_list_str*).
        list_offset:    int byte offset from the list pointer to the top of the structure being
                        listed. For all practical use cases this should be a negative number (i.e.
                        the list is within the structure).
        listed_type     type of the structure being listed (e.g. P4k_thrinfo_t). This should
                        be a structure type.
    Returns:
        List of IExpressionResults representing the child structures.
    """
    # Get head of child queue.
    list_mem = list.getStructureMembers()
    list_loc = list.getLocationAddress()
    head = list_mem['next']
    elements = []
    # Read all the elements from the queue until we find a pointer back to the front.
    while head.readAsAddress() != list_loc:
        # Add the offset of the "next" element to get the containing structure
        base_addr = head.readAsAddress().addOffset(list_offset)
        element = debugger.constructPointer(listed_type, base_addr).dereferencePointer()
        elements.append(element)

        # Advance to next list element
        list_node = head.dereferencePointer()
        head = list_node.getStructureMembers()['next']
    return elements

def getTask(debugger, taskno):
    """Retrieves the task structure with the given task number.

    Parameters:
        debugger:   IDebugSession object.
        taskno:     int task number of the task structure to read.
    Returns:
        Map of elements of the fetched task structure (P4k_taskinfo_t).
    """
    taskdir = debugger.evaluateExpression('"src/task.c"::taskdir').getArrayElement(taskno).getStructureMembers()
    return taskdir['td'].dereferencePointer()

def getChildTasks(debugger, task_struct):
    """Reads all the child tasks from a task.

    Parameters:
        debugger:   IDebugSession object, used to initialise the structure offset if not already.
        task:       Map of elements of a task structure (P4k_taskinfo_t) to read the children of.
    Returns:
        List of IExpressionResults representing the child task structures (P4k_taskinfo_t).
    """
    taskInfoType = debugger.resolveType('P4k_taskinfo_t')
    list_offset = getStructureElementOffset(debugger, taskInfoType, 'childql')
    return readOffsetList(debugger, task_struct.getStructureMembers()['childqh'],  -list_offset, taskInfoType)

def getChildThreads(debugger, task_struct):
    """Reads all the child threads from a task.

    Parameters:
        debugger:   IDebugSession object, used to initialise the structure offset if not already.
        task:       Map of elements of a task structure (P4k_taskinfo_t) to read the children of.
    Returns:
        List of IExpressionResults representing the child thread structures (P4k_thrinfo_t).
    """
    thrInfoType = debugger.resolveType('P4k_thrinfo_t')
    list_offset = getStructureElementOffset(debugger, thrInfoType, 'task_threadql')
    return readOffsetList(debugger, task_struct.getStructureMembers()['threadqh'], -list_offset, thrInfoType)
