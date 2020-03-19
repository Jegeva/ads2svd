# Copyright (C) 2015,2017 Arm Limited (or its affiliates). All rights reserved.

from kernel import *
from osapi import *

"""
Data table for eForce uC3 Fixed-Size Memory Pool structures
"""

class MemoryPoolsFixed( Table ):

    def __init__(self):

        cid = 'memory_pools_fixed'

        fields = [createPrimaryField(cid, 'id', DECIMAL)]

        fields.append(createField(cid, 'name', TEXT))
        fields.append(createField(cid, 'blocks_free', DECIMAL))
        fields.append(createField(cid, 'block_size', DECIMAL))
        fields.append(createField(cid, 'total_size', DECIMAL))
        fields.append(createField(cid, 'start_addr', ADDRESS))
        fields.append(createField(cid, 'attributes', TEXT))
        fields.append(createField(cid, 'waiting_queue', TEXT))

        Table.__init__(self, cid, fields)

    def getRecords(self, debugger):

        records = []

        systbl = debugger.evaluateExpression("_kernel_systbl").getStructureMembers()
        cnstbl = debugger.evaluateExpression("_kernel_cnstbl").getStructureMembers()
        max_id = cnstbl['id_max'].readAsNumber()
        min_id = cnstbl['tskpri_max'].readAsNumber()+1

        atrtbl_elements = cnstbl['atrtbl'].getArrayElements(max_id+1)
        ctrtbl_elements = cnstbl['ctrtbl'].getArrayElements(max_id+1)
        inftbl_elements = cnstbl['inftbl'].getArrayElements(max_id+1)
        namtbl_elements = cnstbl['objname'].getArrayElements(max_id+1)
        waique_elements = cnstbl['waique'].getArrayElements(max_id+1)

        for id in range(min_id, max_id+1):
            id_atr = atrtbl_elements[id].readAsNumber()
            if (id_atr & 0xF0L) == TS_MPF:
                mpf_addr = ctrtbl_elements[id]
                inf_addr = inftbl_elements[id]
                if mpf_addr.readAsNumber() == 0 or inf_addr.readAsNumber() == 0:
                    continue
                mpf_members = mpf_addr.dereferencePointer("T_MPF*").getStructureMembers()
                inf_members = inf_addr.dereferencePointer("T_CMPF*").getStructureMembers()
                wqu_members = waique_elements[id].getStructureMembers()
                id_name = readPotentiallyNullString(namtbl_elements[id])
                records.append(self.createMpfRecord(debugger, systbl, cnstbl, id, id_atr, mpf_members, inf_members, wqu_members, id_name))

        return records

    def createMpfRecord(self, debugger, systbl, cnstbl, id, atr, mpf, inf, wqu, name):
        cells = []

        # Get the memory pool information.
        mpf_atr = self.readMpfAttributes(atr)
        mpf_block_size = inf['blksz'].readAsNumber()
        mpf_total_blocks = inf['blkcnt'].readAsNumber()
        mpf_total_size = mpf_total_blocks * mpf_block_size
        mpf_blocks_free = mpf['blkcnt'].readAsNumber()
        mpf_start_addr = inf['mpf'].readAsAddress()

        # Get the wait queue information.
        wqElements = getFIFOWaitingQueue(cnstbl, id)

        # Build the cells.
        cells.append(createNumberCell(id))
        cells.append(createTextCell(name))
        cells.append(createNumberCell(mpf_blocks_free))
        cells.append(createNumberCell(mpf_block_size))
        cells.append(createNumberCell(mpf_total_size))
        cells.append(createAddressCell(mpf_start_addr))
        cells.append(createTextCell(mpf_atr))
        cells.append(createTextCell(wqElements))

        return self.createRecord(cells)

    def readMpfAttributes(self, atr):
        if (atr & TA_TPRI):
            return ATTRIBUTES_WQU[TA_TPRI]
        return ATTRIBUTES_WQU[TA_TFIFO]
