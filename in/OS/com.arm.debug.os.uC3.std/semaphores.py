# Copyright (C) 2015,2017 Arm Limited (or its affiliates). All rights reserved.

from kernel import *
from osapi import *

"""
Data table for eForce uC3 semaphore structures
"""

class Semaphores( Table ):

    def __init__(self):

        cid = 'semaphores'

        fields = [createPrimaryField(cid, 'id', DECIMAL)]

        fields.append(createField(cid, 'name', TEXT))
        fields.append(createField(cid, 'sem_cnt', DECIMAL))
        fields.append(createField(cid, 'sem_max', DECIMAL))
        fields.append(createField(cid, 'attributes', TEXT))
        fields.append(createField(cid, 'waiting_queue', TEXT))

        Table.__init__(self, cid, fields)


    def getRecords(self, debugger):

        records = []

        systbl = debugger.evaluateExpression('_kernel_systbl').getStructureMembers()
        qsem = systbl['qsem'].getStructureMembers()

        if qsem['inf'].readAsNumber() == 0:
            return records

        info = qsem['inf'].dereferencePointer().getStructureMembers()
        limit = info['limit'].readAsNumber()
        semaphores = qsem['sem'].getArrayElements(limit+1)

        for index in range(1, limit+1):
            semaphore = semaphores[index]
            if semaphore.readAsNumber() != 0:
                records.append(self.createSemRecord(debugger, systbl, index, semaphore.dereferencePointer()))

        return records

    def createSemRecord(self, debugger, systbl, id, semaphore):
        cells = []
        sem_members = semaphore.getStructureMembers()

        # Get the semaphore information.
        sem_name = readPotentiallyNullString(sem_members['name'])
        sem_max  = sem_members['maxsem'].readAsNumber()
        sem_used = sem_max - sem_members['semcnt'].readAsNumber()
        sem_attributes = sem_members['sematr'].readAsNumber()
        attributes = self.readSemAttributes(sem_attributes)

        # Get the wait queue information.
        wqIsFIFO = getWaitingQueueIsFIFO(debugger, sem_attributes)
        if wqIsFIFO:
            wqElements = getFIFOWaitingQueue(systbl, sem_members['que'])
        else:
            wqElements = getPriorityWaitingQueue(systbl, sem_members['que'])

        # Build the cells.
        cells.append(createNumberCell(id))
        cells.append(createTextCell(sem_name))
        cells.append(createNumberCell(sem_used))
        cells.append(createNumberCell(sem_max))
        cells.append(createTextCell(attributes))
        cells.append(createTextCell(wqElements))

        return self.createRecord(cells)

    def readSemAttributes(self, atr):
        if (atr & TA_TPRI):
            return ATTRIBUTES_WQU[TA_TPRI]
        return ATTRIBUTES_WQU[TA_TFIFO]
