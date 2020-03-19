# Copyright (C) 2013,2017 Arm Limited (or its affiliates). All rights reserved.

from utils import *
from osapi import createAddressCell, createTextCell

class BytePools(Table):
    def __init__(self):
        id = "bytepools"
        fields = [createField(id, "symbol", TEXT),
                  createField(id, "location", ADDRESS),
                  createField(id, "name", TEXT),
                  createField(id, "available", DECIMAL),
                  createField(id, "fragments", DECIMAL),
                  createField(id, "list", ADDRESS),
                  createField(id, "search", ADDRESS),
                  createField(id, "start", ADDRESS),
                  createField(id, "size", DECIMAL),
                  createField(id, "owner", TEXT),
                  createField(id, "susp_count", DECIMAL),
                  createField(id, "susp_list", TEXT)]
        Table.__init__(self, id, fields)

    def getOwnerName(self, members):
        # Get the name of the mutex owner thread
        threadptr = members['tx_byte_pool_owner']
        if threadptr.readAsNumber() == 0:
            return ""
        thread = threadptr.dereferencePointer().getStructureMembers()
        return thread['tx_thread_name'].readAsNullTerminatedString()

    def readBytePool(self, bp, sym):
        members = bp.getStructureMembers()

        cells = [createTextCell(sym),
                 createAddressCell(bp.getLocationAddress()),
                 makeTextCell(members, "tx_byte_pool_name"),
                 makeNumberCell(members, "tx_byte_pool_available"),
                 makeNumberCell(members, "tx_byte_pool_fragments"),
                 makeAddressCell(members, "tx_byte_pool_list"),
                 makeAddressCell(members, "tx_byte_pool_search"),
                 makeAddressCell(members, "tx_byte_pool_start"),
                 makeNumberCell(members, "tx_byte_pool_size"),
                 createTextCell(self.getOwnerName(members)),
                 makeNumberCell(members, "tx_byte_pool_suspended_count"),
                 createTextCell(getThreadNameList(members, 'tx_byte_pool_suspension_list'))]

        return self.createRecord(cells)

    def getRecords(self, debugSession):
        if not listSymbolsExist(debugSession, ListTypes.BYTEPOOL):
            return []
        createdptr = getListHead(debugSession, ListTypes.BYTEPOOL)
        if createdptr.readAsNumber() == 0:
            return []
        createdBytePools = createdptr.dereferencePointer()
        syms = [createdptr.resolveAddressAsString()]
        allBytePools = readListWithSymbols(createdBytePools, ListTypes.BYTEPOOL, syms)
        records = map(self.readBytePool, allBytePools, syms)
        return records