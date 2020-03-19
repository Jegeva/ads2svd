# Copyright (C) 2013,2017 Arm Limited (or its affiliates). All rights reserved.

from utils import *
from osapi import createAddressCell

class Queues(Table):
    def __init__(self):
        id = "queues"
        fields = [createField(id, "symbol", TEXT),
                  createField(id, "location", ADDRESS),
                  createField(id, "name", TEXT),
                  createField(id, "messagesize", DECIMAL),
                  createField(id, "capacity", DECIMAL),
                  createField(id, "enqueued", DECIMAL),
                  createField(id, "available", DECIMAL),
                  createField(id, "susp_count", DECIMAL),
                  createField(id, "susp_list", TEXT)]
        Table.__init__(self, id, fields)

    def readQueue(self, queue, sym):
        members = queue.getStructureMembers()

        cells = [createTextCell(sym),
                 createAddressCell(queue.getLocationAddress()),
                 makeTextCell(members, "tx_queue_name"),
                 makeNumberCell(members, "tx_queue_message_size"),
                 makeNumberCell(members, "tx_queue_capacity"),
                 makeNumberCell(members, "tx_queue_enqueued"),
                 makeNumberCell(members, "tx_queue_available_storage"),
                 makeNumberCell(members, "tx_queue_suspended_count"),
                 createTextCell(getThreadNameList(members, 'tx_queue_suspension_list'))]

        return self.createRecord(cells)

    def getRecords(self, debugSession):
        if not listSymbolsExist(debugSession, ListTypes.QUEUE):
            return []
        createdptr = getListHead(debugSession, ListTypes.QUEUE)
        if createdptr.readAsNumber() == 0:
            return []
        createdQueues = createdptr.dereferencePointer()
        syms = [createdptr.resolveAddressAsString()]
        allQueuesList = readListWithSymbols(createdQueues, ListTypes.QUEUE, syms)
        records = map(self.readQueue, allQueuesList, syms)
        return records