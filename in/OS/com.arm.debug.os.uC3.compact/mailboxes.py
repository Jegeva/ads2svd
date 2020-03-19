# Copyright (C) 2015,2017 Arm Limited (or its affiliates). All rights reserved.

from kernel import *
from osapi import *

"""
Data table for eForce uC3 mailbox structures
"""

class Mailboxes( Table ):

    def __init__(self):

        cid = 'mailboxes'

        fields = [createPrimaryField(cid, 'id', DECIMAL)]

        fields.append(createField(cid, 'name', TEXT))
        fields.append(createField(cid, 'first_addr', ADDRESS))
        fields.append(createField(cid, 'message_count', DECIMAL))
        fields.append(createField(cid, 'attributes', TEXT))
        fields.append(createField(cid, 'waiting_queue', TEXT))

        Table.__init__(self, cid, fields)

    def getRecords(self, debugger):

        records = []

        systbl = debugger.evaluateExpression("_kernel_systbl").getStructureMembers()
        cnstbl = debugger.evaluateExpression("_kernel_cnstbl").getStructureMembers()
        max_id = cnstbl['id_max'].readAsNumber()
        min_id = cnstbl['tskpri_max'].readAsNumber()+1

        # NB: There is no inftbl entry for mailboxes.
        atrtbl_elements = cnstbl['atrtbl'].getArrayElements(max_id+1)
        ctrtbl_elements = cnstbl['ctrtbl'].getArrayElements(max_id+1)
        namtbl_elements = cnstbl['objname'].getArrayElements(max_id+1)
        waique_elements = cnstbl['waique'].getArrayElements(max_id+1)

        for id in range(min_id, max_id+1):
            id_atr = atrtbl_elements[id].readAsNumber()
            if (id_atr & 0xF0L) == TS_MBX:
                mbx_addr = ctrtbl_elements[id]
                if mbx_addr.readAsNumber() == 0:
                    continue
                mbx_members = mbx_addr.dereferencePointer("T_MBX*").getStructureMembers()
                wqu_members = waique_elements[id].getStructureMembers()
                id_name = readPotentiallyNullString(namtbl_elements[id])
                records.append(self.createMbxRecord(debugger, systbl, cnstbl, id, id_atr, mbx_members, wqu_members, id_name))

        return records

    def createMbxRecord(self, debugger, systbl, cnstbl, id, atr, mbx, wqu, name):
        cells = []

        # Get the mailbox information.
        mbx_atr = self.readMbxAttributes(atr)

        # Get the message queue information.
        mqStart, mqSize = getFIFOMessageQueue(mbx)

        # Get the wait queue information.
        wqElements = getFIFOWaitingQueue(cnstbl, id)

        # Build the cells.
        cells.append(createNumberCell(id))
        cells.append(createTextCell(name))
        cells.append(createAddressCell(mqStart))
        cells.append(createNumberCell(mqSize))
        cells.append(createTextCell(mbx_atr))
        cells.append(createTextCell(wqElements))

        return self.createRecord(cells)

    def readMbxAttributes(self, atr):
        attributes = []
        if (atr & TA_TPRI):
            attributes.append(ATTRIBUTES_WQU[TA_TPRI])
        else:
            attributes.append(ATTRIBUTES_WQU[TA_TFIFO])

        if (atr & TA_MPRI):
            attributes.append(ATTRIBUTES_MBX[TA_MPRI])
        else:
            attributes.append(ATTRIBUTES_MBX[TA_MFIFO])

        return ' | '.join(attributes)
