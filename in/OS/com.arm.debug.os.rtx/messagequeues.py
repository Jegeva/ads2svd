# Copyright (C) 2013,2017,2018 Arm Limited (or its affiliates). All rights reserved.

from utils import *



class MessageQueues(RtxInterTaskCommTable):

    def __init__(self):
        id = "message_queues"

        fields = [createField(id, "addr",     ADDRESS),
                  createField(id, "tasks",    TEXT),
                  createField(id, "state",    TEXT),
                  createField(id, "size",     DECIMAL),
                  createField(id, "count",    DECIMAL),
                  createField(id, "msg_size", DECIMAL),
                  createField(id, "first",    ADDRESS),
                  createField(id, "last",     ADDRESS)]

        functions = [lambda members, prlnk: createAddressCell(prlnk.readAsAddress()),
                     lambda members, prlnk: makeTaskWaitersCell(members, "thread_list"),
                     lambda members, prlnk: self.makeStateCell(members),
                     lambda members, prlnk: createNumberCell(members["mp_info"].getStructureMembers().get("max_blocks").readAsNumber()),
                     lambda members, prlnk: makeNumberCell(members,  "msg_count"),
                     lambda members, prlnk: makeNumberCell(members,  "msg_size"),
                     lambda members, prlnk: makeAddressCell(members, "msg_first"),
                     lambda members, prlnk: makeAddressCell(members, "msg_last")]

        RtxInterTaskCommTable.__init__(self, id, fields, functions, "MessageQueue")

    def getControlBlocks(self, dbg):
        if isVersion4(): return []

        return super(RtxInterTaskCommTable, self).getControlBlocks(dbg)

    def makeStateCell(self, members):
        waitingTasksPtr = members["thread_list"]

        if(isNullPtr(waitingTasksPtr)):
            return createTextCell("NOT_WAITING")
        else:
            return makeStateCell(waitingTasksPtr.dereferencePointer().getStructureMembers())
    