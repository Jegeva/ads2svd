# Copyright (C) 2013,2015,2017,2018 Arm Limited (or its affiliates). All rights reserved.

from utils import *

#Timeout value.
OS_WAIT_FOREVER = 0xFFFFFFFFL    #///< Wait forever timeout value.

class Tasks(RtxTable):

    def __init__(self):
        id = "tasks"

        fields = [createPrimaryField(id, "id",    TEXT),
                  createField(id, "name",         TEXT),
                  createField(id, "priority",     DECIMAL),
                  createField(id, "state",        TEXT),
                  createField(id, "delay",        DECIMAL),
                  createField(id, "thread_flags", HEXADECIMAL),
                  createField(id, "flags",        HEXADECIMAL),
                  createField(id, "waiting",      TEXT)]
        RtxTable.__init__(self, id, fields)

    def createRecordFromControlBlock(self, tcbPtr, debugger):
        members = dereferenceThreadPointer(tcbPtr).getStructureMembers()

        cells = [makeTaskIdCell(tcbPtr, members),
                 makeNameCell(members,   "thread_addr"),
                 makeNumberCell(members, "priority"),
                 makeStateCell(members),
                 self.makeDelayCell(tcbPtr, members),
                 makeNumberCell(members, "thread_flags"),
                 makeNumberCell(members, "wait_flags"),
                 self.makeWaitedResourceCell(members, "thread_prev", debugger)]

        return self.createRecord(cells)

    def makeDelayCell(self, tcbPtr, members):
         # RTX stores delayed tasks in an doubly linked list ordered by ascending expiry
         # time, starting with the task pointed to by the global os_dly variable. Each task
         # in the list has its delay member set to the number of milliseconds until the
         # *next* task in the list is due to expire. To calculate the delay for a given task
         # it is required to sum the delta_time members of all previous tasks in the delay list.
        delay = 0
        if (getMember(members,"delay").readAsNumber() != OS_WAIT_FOREVER):
            for tcbPtr in pointerToIter(tcbPtr, getMemberName("delay_prev"), getCType("Thread")):
                delay += getMember(dereferenceThreadPointer(tcbPtr).getStructureMembers(), "delay").readAsNumber()

        return createNumberCell(delay if (delay > 0) else None)

    def makeWaitedResourceCell(self, members, name, debugger):
        cbPtr = getMember(members,name)

        while (nonNullPtr(cbPtr) and isThreadControlBlock(cbPtr)):
             cbPtr = nextPtr(cbPtr, name)

        if (isNullPtr(cbPtr)): return createTextCell("")

        #In RTX5 the head thread of the ready list has its member "thread_prev" pointing to the global variable osRtxInfo.thread.ready,
        #which is not a thread but the container for threads in ready state, so its control block identifier is invalid (0)
        #When cbPtr points to that address ==> This means that there is no resource that is being waited for
        if (isVersion5() and \
            (cbPtr.readAsAddress().compareTo(debugger.evaluateExpression("&osRtxInfo.thread.ready").readAsAddress()) == 0)):
            return createTextCell("")

        cbId = getControlBlockIdentifierFromPointer(cbPtr)

        return createTextCell(cbId.upper() + "@" + str(cbPtr.readAsAddress()) if cbId else "")

