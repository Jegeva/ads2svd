# Copyright (C) 2015,2017 Arm Limited (or its affiliates). All rights reserved.

from kernel import *
from osapi import *

"""
Data table for eForce uC3 Compact semaphore structures
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
            if (id_atr & 0xF0L) == TS_SEM:
                sem_addr = ctrtbl_elements[id]
                inf_addr = inftbl_elements[id]
                if sem_addr.readAsNumber() == 0 or inf_addr.readAsNumber() == 0:
                    continue
                sem_members = sem_addr.dereferencePointer("T_SEM*").getStructureMembers()
                inf_members = inf_addr.dereferencePointer("T_CSEM*").getStructureMembers()
                wqu_members = waique_elements[id].getStructureMembers()
                id_name = readPotentiallyNullString(namtbl_elements[id])
                records.append(self.createSemRecord(debugger, systbl, cnstbl, id, id_atr, sem_members, inf_members, wqu_members, id_name))

        return records

    def createSemRecord(self, debugger, systbl, cnstbl, id, atr, sem, inf, wqu, name):
        cells = []

        # Get the semaphore information.
        sem_max  = inf['maxsem'].readAsNumber()
        sem_used = sem_max - sem['semcnt'].readAsNumber()
        sem_atr = self.readSemAttributes(atr)

        # Get the wait queue information.
        wqElements = getFIFOWaitingQueue(cnstbl, id)

        # Build the cells.
        cells.append(createNumberCell(id))
        cells.append(createTextCell(name))
        cells.append(createNumberCell(sem_used))
        cells.append(createNumberCell(sem_max))
        cells.append(createTextCell(sem_atr))
        cells.append(createTextCell(wqElements))

        return self.createRecord(cells)

    def readSemAttributes(self, atr):
        if (atr & TA_TPRI):
            return ATTRIBUTES_WQU[TA_TPRI]
        return ATTRIBUTES_WQU[TA_TFIFO]
