# Copyright (C) 2013,2017 Arm Limited (or its affiliates). All rights reserved.

from utils import *
from osapi import createAddressCell, createTextCell

class Semaphores(Table):
    def __init__(self):
        id = "semaphores"
        fields = [createField(id, "symbol", TEXT),
                  createField(id, "location", ADDRESS),
                  createField(id, "name", TEXT),
                  createField(id, "count", DECIMAL),
                  createField(id, "susp_count", DECIMAL),
                  createField(id, "susp_list", TEXT)]
        Table.__init__(self, id, fields)

    def readSemaphore(self, semaphore, sym):
        members = semaphore.getStructureMembers()

        cells = [createTextCell(sym),
                 createAddressCell(semaphore.getLocationAddress()),
                 makeTextCell(members, "tx_semaphore_name"),
                 makeNumberCell(members, "tx_semaphore_count"),
                 makeNumberCell(members, "tx_semaphore_suspended_count"),
                 createTextCell(getThreadNameList(members, 'tx_semaphore_suspension_list'))]
        return self.createRecord(cells)

    def getRecords(self, debugSession):
        if not listSymbolsExist(debugSession, ListTypes.SEMAPHORE):
            return []
        createdptr = getListHead(debugSession, ListTypes.SEMAPHORE)
        if createdptr.readAsNumber() == 0:
            return []
        createdSemaphores = createdptr.dereferencePointer()
        syms = [createdptr.resolveAddressAsString()]
        allSemaphoresList = readListWithSymbols(createdSemaphores, ListTypes.SEMAPHORE, syms)
        records = map(self.readSemaphore, allSemaphoresList, syms)
        return records