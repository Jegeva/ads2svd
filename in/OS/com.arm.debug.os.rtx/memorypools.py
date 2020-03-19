# Copyright (C) 2018 Arm Limited (or its affiliates). All rights reserved.

from utils import *



class MemoryPools(RtxTable):

    MP_CONRTOL_BLOCK_NAMES = [
            "stack",
            "thread",
            "timer",
            "event_flags",
            "mutex",
            "semaphore",
            "memory_pool",
            "message_queue"]

    def __init__(self):
        id = "memory_pools"

        fields = [createField(id, "name",        TEXT),
                  createField(id, "size",        DECIMAL),
                  createField(id, "max_blocks",  DECIMAL),
                  createField(id, "used_blocks", DECIMAL),
                  createField(id, "block_size",  DECIMAL),
                  createField(id, "block_base",  ADDRESS),
                  createField(id, "block_lim",   ADDRESS),
                  createField(id, "block_free",  ADDRESS)]

        RtxTable.__init__(self, id, fields)

    def getRecords(self, dbg):
        if isVersion4(): return []

        mpi_members = dbg.evaluateExpression("osRtxInfo.mpi").getStructureMembers()

        records = []
        for name in MemoryPools.MP_CONRTOL_BLOCK_NAMES:
            mp_info_ptr = mpi_members.get(name)
            if (nonNullPtr(mp_info_ptr)):
                records.append(self.createRecordFromControlBlock(mp_info_ptr, name))

        return records

    def createRecordFromControlBlock(self, mp_info_ptr, name):
        members = mp_info_ptr.dereferencePointer().getStructureMembers()
        max_blocks = getMember(members,"max_blocks").readAsNumber()
        block_size = getMember(members,"block_size").readAsNumber()
        total_size = max_blocks*block_size

        cells = [createTextCell(name),
                 createNumberCell(total_size),
                 createNumberCell(max_blocks),
                 makeNumberCell(members,  "used_blocks"),
                 createNumberCell(block_size),
                 makeAddressCell(members, "block_base"),
                 makeAddressCell(members, "block_lim"),
                 makeAddressCell(members, "block_free")]

        return self.createRecord(cells)

