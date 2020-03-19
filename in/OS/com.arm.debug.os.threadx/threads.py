# Copyright (C) 2013,2017 Arm Limited (or its affiliates). All rights reserved.

from utils import *
from osapi import createAddressCell

class Threads(Table):
    def __init__(self):
        id = "threads"
        fields = [createField(id, "symbol", TEXT),
                  createField(id, "location", ADDRESS),
                  createField(id, "name", TEXT),
                  createField(id, "runcount", DECIMAL),
                  createField(id, "priority", DECIMAL),
                  createField(id, "state", TEXT),
                  createField(id, "stackstart", ADDRESS),
                  createField(id, "stackend", ADDRESS),
                  createField(id, "stackptr", ADDRESS)]
        Table.__init__(self, id, fields)

    def readTask(self, taskControlBlock, sym):
        members = taskControlBlock.getStructureMembers()

        cells = [createTextCell(sym),
                 createAddressCell(taskControlBlock.getLocationAddress()),
                 makeTextCell(members, "tx_thread_name"),
                 makeNumberCell(members, "tx_thread_run_count"),
                 makeNumberCell(members, "tx_thread_priority"),
                 makeStateCell(members),
                 makeAddressCell(members, "tx_thread_stack_start"),
                 makeAddressCell(members, "tx_thread_stack_end"),
                 makeAddressCell(members, "tx_thread_stack_ptr")]

        return self.createRecord(cells)

    def getRecords(self, debugSession):
        createdptr = getListHead(debugSession, ListTypes.THREAD)
        if createdptr.readAsNumber() == 0:
            return []
        syms = [createdptr.resolveAddressAsString()]
        createdTCBs = createdptr.dereferencePointer()
        allTCBList = readListWithSymbols(createdTCBs, ListTypes.THREAD, syms)
        records = map(self.readTask, allTCBList, syms)
        return records
