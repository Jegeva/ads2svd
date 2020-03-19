# Copyright (C) 2015,2017 Arm Limited (or its affiliates). All rights reserved.

from kernel import *
from osapi import *

"""
Data table for eForce uC3 Variable-Size Memory Pool structures
"""

class MemoryPoolsVariable( Table ):

    def __init__(self):

        cid = 'memory_pools_variable'

        fields = [createPrimaryField(cid, 'id', DECIMAL)]

        fields.append(createField(cid, 'name', TEXT))
        fields.append(createField(cid, 'largest_free', DECIMAL))
        fields.append(createField(cid, 'total_free', DECIMAL))
        fields.append(createField(cid, 'total_size', DECIMAL))
        fields.append(createField(cid, 'start_addr', ADDRESS))
        fields.append(createField(cid, 'attributes', TEXT))
        fields.append(createField(cid, 'waiting_queue', TEXT))

        Table.__init__(self, cid, fields)


    def getRecords(self, debugger):

        records = []

        systbl = debugger.evaluateExpression('_kernel_systbl').getStructureMembers()
        qmpl = systbl['qmpl'].getStructureMembers()

        if qmpl['inf'].readAsNumber() == 0:
            return records

        info = qmpl['inf'].dereferencePointer().getStructureMembers()
        limit = info['limit'].readAsNumber()
        memorypools = qmpl['mpl'].getArrayElements(limit+1)

        for index in range(1, limit+1):
            memorypool = memorypools[index]
            if memorypool.readAsNumber() != 0:
                records.append(self.createMplRecord(debugger, systbl, index, memorypool.dereferencePointer()))

        return records

    def createMplRecord(self, debugger, systbl, id, memorypool_obj):
        cells = []
        memorypool = memorypool_obj.getStructureMembers()

        # Get the memory pool information.
        mpl_name = readPotentiallyNullString(memorypool['name'])
        mpl_attributes = memorypool['mplatr'].readAsNumber()
        mpl_total_size = memorypool['mplsz'].readAsNumber()
        mpl_start_addr = memorypool['allad'].readAsAddress()
        mpl_total_free, mpl_largest_free = getFreeMem(memorypool['top'])
        attributes = self.readMplAttributes(mpl_attributes)

        # Get the wait queue information.
        wqIsFIFO = getWaitingQueueIsFIFO(debugger, mpl_attributes)
        if wqIsFIFO:
            wqElements = getFIFOWaitingQueue(systbl, memorypool['que'])
        else:
            wqElements = getPriorityWaitingQueue(systbl, memorypool['que'])

        # Build the cells.
        cells.append(createNumberCell(id))
        cells.append(createTextCell(mpl_name))
        cells.append(createNumberCell(mpl_largest_free))
        cells.append(createNumberCell(mpl_total_free))
        cells.append(createNumberCell(mpl_total_size))
        cells.append(createAddressCell(mpl_start_addr))
        cells.append(createTextCell(attributes))
        cells.append(createTextCell(wqElements))

        return self.createRecord(cells)

    def readMplAttributes(self, atr):
        if (atr & TA_TPRI):
            return ATTRIBUTES_WQU[TA_TPRI]
        return ATTRIBUTES_WQU[TA_TFIFO]
