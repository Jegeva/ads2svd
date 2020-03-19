# Copyright (C) 2015,2017 Arm Limited (or its affiliates). All rights reserved.

from kernel import *
from osapi import *

"""
Data table for eForce uC3 mutex structures
"""

class Mutexes( Table ):

    def __init__(self):
        cid = 'mutexes'

        fields = [createPrimaryField(cid, 'id', DECIMAL)]

        fields.append(createField(cid, 'name', TEXT))
        fields.append(createField(cid, 'locked', TEXT))
        fields.append(createField(cid, 'priority', DECIMAL))
        fields.append(createField(cid, 'attributes', TEXT))
        fields.append(createField(cid, 'waiting_queue', TEXT))

        Table.__init__(self, cid, fields)

    def getRecords(self, debugger):
        records = []

        systbl = debugger.evaluateExpression('_kernel_systbl').getStructureMembers()
        qmtx = systbl['qmtx'].getStructureMembers()

        if qmtx['inf'].readAsNumber() == 0:
            return records

        info = qmtx['inf'].dereferencePointer().getStructureMembers()
        limit = info['limit'].readAsNumber()
        mutexes = qmtx['mtx'].getArrayElements(limit+1)

        for index in range(1, limit+1):
            mutex = mutexes[index]
            if mutex.readAsNumber() != 0:
                records.append(self.createMtxRecord(debugger, systbl, index, mutex.dereferencePointer()))

        return records

    def createMtxRecord(self, debugger, systbl, id, mutex_obj):
        cells = []
        mutex = mutex_obj.getStructureMembers()

        # Get the mutex information.
        mtx_name = readPotentiallyNullString(mutex['name'])
        mtx_locker = mutex['tskid'].readAsNumber()
        mtx_attributes = mutex['mtxatr'].readAsNumber()
        attributes, wqIsFIFO = self.readMtxAttributes(mtx_attributes)

        # Get the wait queue information.
        if wqIsFIFO:
            mtx_priority = None
            wqElements = getFIFOWaitingQueue(systbl, mutex['que'])
        else:
            mtx_priority = mutex['pri'].readAsNumber()
            wqElements = getPriorityWaitingQueue(systbl, mutex['que'])

        # Build the cells.
        cells.append(createNumberCell(id))
        cells.append(createTextCell(mtx_name))
        if mtx_locker > 0:
            cells.append(createLocalisedTextCell('misc.yes_count', mtx_locker))
        else:
            cells.append(createLocalisedTextCell('misc.no'))
        cells.append(createNumberCell(mtx_priority))
        cells.append(createTextCell(attributes))
        cells.append(createTextCell(wqElements))

        return self.createRecord(cells)

    def readMtxAttributes(self, atr):
        """
        The Mutex's Waiting Queue has two additional possible states - TA_INHERIT
        and TA_CEILING - both of which are variants on the TA_TPRI state. These
        are all mutually exclusive (and use a 2-bit field) so must be handled
        together slightly differently to normal.
        As a result of this detecting whether or not the wait queue is in FIFO
        order is slightly different to normal so we return that too.
        """
        attributes = []
        wqIsFIFO = False
        # TA_TFIFO   = 0x00, TA_TPRI    = 0x01
        # TA_INHERIT = 0x02, TA_CEILING = 0x03
        wait_queue_atr = atr & 0x03
        if wait_queue_atr == TA_TFIFO:
            attributes.append(ATTRIBUTES_WQU[TA_TFIFO])
            wqIsFIFO = True
        elif wait_queue_atr == TA_TPRI:
            attributes.append(ATTRIBUTES_WQU[TA_TPRI])
        elif wait_queue_atr == TA_INHERIT:
            attributes.append(ATTRIBUTES_MTX[TA_INHERIT])
        else: # wait_queue_atr == TA_CEILING
            attributes.append(ATTRIBUTES_MTX[TA_CEILING])

        return ' | '.join(attributes), wqIsFIFO
