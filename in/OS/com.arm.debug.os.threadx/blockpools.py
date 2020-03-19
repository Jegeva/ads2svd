# Copyright (C) 2013,2017 Arm Limited (or its affiliates). All rights reserved.

from utils import *
from osapi import createAddressCell, createTextCell

class BlockPools(Table):
    def __init__(self):
        id = "blockpools"
        fields = [createField(id, "symbol", TEXT),
                  createField(id, "location", ADDRESS),
                  createField(id, "name", TEXT),
                  createField(id, "available", DECIMAL),
                  createField(id, "total", DECIMAL),
                  createField(id, "available_list", ADDRESS),
                  createField(id, "start", ADDRESS),
                  createField(id, "size", DECIMAL),
                  createField(id, "block_size", DECIMAL),
                  createField(id, "susp_count", DECIMAL),
                  createField(id, "susp_list", TEXT)]
        Table.__init__(self, id, fields)

    def readBlockPool(self, bp, sym):
        members = bp.getStructureMembers()

        cells = [createTextCell(sym),
                 createAddressCell(bp.getLocationAddress()),
                 makeTextCell(members, "tx_block_pool_name"),
                 makeNumberCell(members, "tx_block_pool_available"),
                 makeNumberCell(members, "tx_block_pool_total"),
                 makeAddressCell(members, "tx_block_pool_available_list"),
                 makeAddressCell(members, "tx_block_pool_start"),
                 makeNumberCell(members, "tx_block_pool_size"),
                 makeNumberCell(members, "tx_block_pool_block_size"),
                 makeNumberCell(members, "tx_block_pool_suspended_count"),
                 createTextCell(getThreadNameList(members, 'tx_block_pool_suspension_list'))]

        return self.createRecord(cells)

    def getRecords(self, debugSession):
        if not listSymbolsExist(debugSession, ListTypes.BLOCKPOOL):
            return []
        createdptr = getListHead(debugSession, ListTypes.BLOCKPOOL)
        if createdptr.readAsNumber() == 0:
            return []
        createdBlockPools = createdptr.dereferencePointer()
        syms = [createdptr.resolveAddressAsString()]
        allBlockPools = readListWithSymbols(createdBlockPools, ListTypes.BLOCKPOOL, syms)
        records = map(self.readBlockPool, allBlockPools, syms)
        return records