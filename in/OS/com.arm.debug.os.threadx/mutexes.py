# Copyright (C) 2013,2017 Arm Limited (or its affiliates). All rights reserved.

from utils import *
from osapi import createAddressCell, createTextCell

class Mutexes(Table):
    def __init__(self):
        id = "mutexes"
        fields = [createField(id, "symbol", TEXT),
                  createField(id, "location", ADDRESS),
                  createField(id, "name", TEXT),
                  createField(id, "owner_count", DECIMAL),
                  createField(id, "owner", TEXT),
                  createField(id, "inherit_flag", DECIMAL),
                  createField(id, "orig_priority", DECIMAL),
                  createField(id, "susp_count", DECIMAL),
                  createField(id, "susp_list", TEXT)]
        Table.__init__(self, id, fields)

    def getOwnerName(self, members):
        # Get the name of the mutex owner thread
        thread = members['tx_mutex_owner']
        if thread.readAsNumber() == 0:
            return ""
        thread = thread.dereferencePointer().getStructureMembers()
        return thread['tx_thread_name'].readAsNullTerminatedString()

    def readMutex(self, mutex, sym):
        members = mutex.getStructureMembers()

        cells = [createTextCell(sym),
                 createAddressCell(mutex.getLocationAddress()),
                 makeTextCell(members, "tx_mutex_name"),
                 makeNumberCell(members, "tx_mutex_ownership_count"),
                 createTextCell(self.getOwnerName(members)),
                 makeNumberCell(members, "tx_mutex_inherit"),
                 makeNumberCell(members, "tx_mutex_original_priority"),
                 makeNumberCell(members, "tx_mutex_suspended_count"),
                 createTextCell(getThreadNameList(members, 'tx_mutex_suspension_list'))]

        return self.createRecord(cells)

    def getRecords(self, debugSession):
        if not listSymbolsExist(debugSession, ListTypes.MUTEX):
            return []
        createdptr = getListHead(debugSession, ListTypes.MUTEX)
        if createdptr.readAsNumber() == 0:
            return []
        createdMutexes = createdptr.dereferencePointer()
        syms = [createdptr.resolveAddressAsString()]
        allMutexesList = readListWithSymbols(createdMutexes, ListTypes.MUTEX, syms)
        records = map(self.readMutex, allMutexesList, syms)
        return records