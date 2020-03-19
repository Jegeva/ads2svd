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
            if (id_atr & 0xF0L) == TS_DTQ:
                dtq_addr = ctrtbl_elements[id]
                inf_addr = inftbl_elements[id]
                if dtq_addr.readAsNumber() == 0 or inf_addr.readAsNumber() == 0:
                    continue
                dtq_members = dtq_addr.dereferencePointer("T_DTQ*").getStructureMembers()
                inf_members = inf_addr.dereferencePointer("T_CDTQ*").getStructureMembers()
                wqu_members = waique_elements[id].getStructureMembers()
                id_name = readPotentiallyNullString(namtbl_elements[id])
                records.append(self.createDtqRecord(debugger, systbl, cnstbl, id, id_atr, dtq_members, inf_members, wqu_members, id_name))

        return records

    def createDtqRecord(self, debugger, systbl, cnstbl, id, atr, dtq, inf, wqu, name):
        cells = []

        # Get the dataqueue information.
        dtq_atr = self.readDtqAttributes(atr)

        dtq_count = dtq['cnt'].readAsNumber()
        dtq_capacity = inf['dtqcnt'].readAsNumber()
        dtq_addr = inf['dtq'].readAsAddress()

        # Dataqueues actually register two separate object ID's, giving them two
        # separate wait queue structures:
        # - The first of these is used for the Receive Wait Queue.
        # - The second of these is used for the Send Wait Queue.
        rcv_wqElements = getFIFOWaitingQueue(cnstbl, id+0)
        snd_wqElements = getFIFOWaitingQueue(cnstbl, id+1)

        cells = []

        cells.append(createNumberCell(id))
        cells.append(createTextCell(name))
        cells.append(createNumberCell(dtq_count))
        cells.append(createNumberCell(dtq_capacity))
        cells.append(createAddressCell(dtq_addr))
        cells.append(createTextCell(dtq_atr))
        cells.append(createTextCell(snd_wqElements))
        cells.append(createTextCell(rcv_wqElements))

        return self.createRecord(cells)

    def readDtqAttributes(self, atr):
        if (atr & TA_TPRI):
            return ATTRIBUTES_WQU[TA_TPRI]
        return ATTRIBUTES_WQU[TA_TFIFO]
