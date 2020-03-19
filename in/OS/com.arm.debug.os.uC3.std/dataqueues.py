# Copyright (C) 2015,2017 Arm Limited (or its affiliates). All rights reserved.

from kernel import *
from osapi import *

"""
Data table for eForce uC3 data queue structures
"""

class DataQueues( Table ):

    def __init__(self):

        cid = 'dataqueues'

        fields = [createPrimaryField(cid, 'id', DECIMAL)]

        fields.append(createField(cid, 'name', TEXT))
        fields.append(createField(cid, 'count', DECIMAL))
        fields.append(createField(cid, 'capacity', DECIMAL))
        fields.append(createField(cid, 'start_addr', ADDRESS))
        fields.append(createField(cid, 'attributes', TEXT))
        fields.append(createField(cid, 'snd_waiting_queue', TEXT))
        fields.append(createField(cid, 'rcv_waiting_queue', TEXT))

        Table.__init__(self, cid, fields)

    def getRecords(self, debugger):

        systbl = debugger.evaluateExpression('_kernel_systbl').getStructureMembers()
        qdtq = systbl['qdtq'].getStructureMembers()

        if qdtq['inf'].readAsNumber() == 0:
            return records

        info = qdtq['inf'].dereferencePointer().getStructureMembers()
        limit = info['limit'].readAsNumber()
        queues = qdtq['dtq'].getArrayElements(limit+1)

        records = []

        for index in range(1, limit+1):
            queue = queues[index]
            if queue.readAsNumber() != 0:
                records.append(self.createDtqRecord(debugger, systbl, index, queue.dereferencePointer()))

        return records

    def createDtqRecord(self, debugger, systbl, id, queue):

        dtq = queue.getStructureMembers()

        dtq_name = readPotentiallyNullString(dtq['name'])
        dtq_count = dtq['cnt'].readAsNumber()
        dtq_capacity = dtq['dtqcnt'].readAsNumber()
        dtq_addr = dtq['dtq'].readAsAddress()
        dtq_attributes = dtq['dtqatr'].readAsNumber()
        attributes = self.readDtqAttributes(dtq_attributes)

        snd_wqIsFIFO = getWaitingQueueIsFIFO(debugger, dtq_attributes)
        if snd_wqIsFIFO:
            snd_wqElements = getFIFOWaitingQueue(systbl, dtq['sque'])
        else:
            snd_wqElements = getPriorityWaitingQueue(systbl, dtq['sque'])

        rcv_wqElements = ', '.join(getInternalWaitingQueue(dtq['que']))

        cells = []

        cells.append(createNumberCell(id))
        cells.append(createTextCell(dtq_name))
        cells.append(createNumberCell(dtq_count))
        cells.append(createNumberCell(dtq_capacity))
        cells.append(createAddressCell(dtq_addr))
        cells.append(createTextCell(attributes))
        cells.append(createTextCell(snd_wqElements))
        cells.append(createTextCell(rcv_wqElements))

        return self.createRecord(cells)

    def readDtqAttributes(self, atr):
        if (atr & TA_TPRI):
            return ATTRIBUTES_WQU[TA_TPRI]
        return ATTRIBUTES_WQU[TA_TFIFO]
