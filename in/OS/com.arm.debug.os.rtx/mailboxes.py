# Copyright (C) 2013,2017,2018 Arm Limited (or its affiliates). All rights reserved.

from utils import *

MAILBOX_STATE_NAMES = ["NOT_WAITING",       # 0
                       "WAITING_GET",       # 1
                       "WAITING_SEND",      # 2
                       "WAITING_ALLOCATE"]  # 3


class Mailboxes(RtxInterTaskCommTable):

    def __init__(self):
        id = "mailboxes"

        fields = [createField(id, "addr", ADDRESS),
                  createField(id, "tasks", TEXT),
                  createField(id, "state", TEXT),
                  createField(id, "first", DECIMAL),
                  createField(id, "last", DECIMAL),
                  createField(id, "count", DECIMAL),
                  createField(id, "size", DECIMAL),
                  createField(id, "messages", ADDRESS)]

        functions = [lambda members, prlnk: createAddressCell(prlnk.readAsAddress()),
                     lambda members, prlnk: makeTaskWaitersCell(members, "thread_list"),
                     lambda members, prlnk: self.makeStateCell(members, "state"),
                     lambda members, prlnk: makeNumberCell(members, "msg_first"),
                     lambda members, prlnk: makeNumberCell(members, "msg_last"),
                     lambda members, prlnk: makeNumberCell(members, "msg_count"),
                     lambda members, prlnk: makeNumberCell(members, "size"),
                     lambda members, prlnk: makeAddressOfCell(members, "msg")]

        RtxInterTaskCommTable.__init__(self, id, fields, functions, "Mailbox")

    def getControlBlocks(self, dbg):
        if not isVersion4(): return []

        return super(RtxInterTaskCommTable, self).getControlBlocks(dbg)

    def makeStateCell(self, members, name):
        stateId = getMember(members, name).readAsNumber()
        if stateId < 0 or stateId > (len(MAILBOX_STATE_NAMES) -1):
            return createTextCell(str(stateId))
        else:
            return createTextCell(MAILBOX_STATE_NAMES[int(stateId)])
    