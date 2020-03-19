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

        systbl = debugger.evaluateExpression('_kernel_systbl').getStructureMembers()
        qmpf = systbl['qmpf'].getStructureMembers()

        if qmpf['inf'].readAsNumber() == 0:
            return records

        info = qmpf['inf'].dereferencePointer().getStructureMembers()
        limit = info['limit'].readAsNumber()
        memorypools = qmpf['mpf'].getArrayElements(limit+1)

        for index in range(1, limit+1):
            memorypool = memorypools[index]
            if memorypool.readAsNumber() != 0:
                records.append(self.createMpfRecord(debugger, systbl, index, memorypool.dereferencePointer()))

        return records

    def createMpfRecord(self, debugger, systbl, id, memorypool_obj):
        cells = []
        memorypool = memorypool_obj.getStructureMembers()

        # Get the memory pool information.
        mpf_name = readPotentiallyNullString(memorypool['name'])
        mpf_attributes = memorypool['mpfatr'].readAsNumber()
        mpf_total_size = memorypool['allsz'].readAsNumber()
        mpf_block_size = memorypool['blksz'].readAsNumber()
        mpf_blocks_free = memorypool['blkcnt'].readAsNumber()
        mpf_start_addr = memorypool['allad'].readAsAddress()
        attributes = self.readMpfAttributes(mpf_attributes)

        # Get the wait queue information.
        wqIsFIFO = getWaitingQueueIsFIFO(debugger, mpf_attributes)
        if wqIsFIFO:
            wqElements = getFIFOWaitingQueue(systbl, memorypool['que'])
        else:
            wqElements = getPriorityWaitingQueue(systbl, memorypool['que'])

        # Build the cells.
        cells.append(createNumberCell(id))
        cells.append(createTextCell(mpf_name))
        cells.append(createNumberCell(mpf_blocks_free))
        cells.append(createNumberCell(mpf_block_size))
        cells.append(createNumberCell(mpf_total_size))
        cells.append(createAddressCell(mpf_start_addr))
        cells.append(createTextCell(attributes))
        cells.append(createTextCell(wqElements))

        return self.createRecord(cells)

    def readMpfAttributes(self, atr):
        if (atr & TA_TPRI):
            return ATTRIBUTES_WQU[TA_TPRI]
        return ATTRIBUTES_WQU[TA_TFIFO]
