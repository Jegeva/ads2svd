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
        fields.append(createField(cid, 'max_priority', DECIMAL))
        fields.append(createField(cid, 'first_addr', ADDRESS))
        fields.append(createField(cid, 'message_count', TEXT))
        fields.append(createField(cid, 'attributes', TEXT))
        fields.append(createField(cid, 'waiting_queue', TEXT))

        Table.__init__(self, cid, fields)

    def getRecords(self, debugger):

        records = []

        systbl = debugger.evaluateExpression('_kernel_systbl').getStructureMembers()
        qmbx = systbl['qmbx'].getStructureMembers()

        if qmbx['inf'].readAsNumber() == 0:
            return records

        info = qmbx['inf'].dereferencePointer().getStructureMembers()
        limit = info['limit'].readAsNumber()
        mailboxes = qmbx['mbx'].getArrayElements(limit+1)

        for index in range(1, limit+1):
            mailbox = mailboxes[index]
            if mailbox.readAsNumber() != 0:
                records.append(self.createMbxRecord(debugger, systbl, index, mailbox.dereferencePointer()))

        return records

    def createMbxRecord(self, debugger, systbl, id, mailbox_obj):
        cells = []
        mailbox = mailbox_obj.getStructureMembers()

        # Get the mailbox information.
        mbx_name = readPotentiallyNullString(mailbox['name'])
        mbx_attributes = mailbox['mbxatr'].readAsNumber()
        attributes = self.readMbxAttributes(mbx_attributes)

        # Get the message queue information.
        mqIsFIFO = getMessageQueueIsFIFO(debugger, mbx_attributes)
        if mqIsFIFO:
            mqMaxPri, mqStart, mqSize = getFIFOMessageQueue(systbl, mailbox['mprihd'])
        else:
            mqMaxPri, mqStart, mqSize = getPriorityMessageQueue(systbl, mailbox['mprihd'])
        # Get the wait queue information.
        wqIsFIFO = getWaitingQueueIsFIFO(debugger, mbx_attributes)
        if wqIsFIFO:
            wqElements = getFIFOWaitingQueue(systbl, mailbox['que'])
        else:
            wqElements = getPriorityWaitingQueue(systbl, mailbox['que'])

        # Build the cells.
        cells.append(createNumberCell(id))
        cells.append(createTextCell(mbx_name))
        cells.append(createNumberCell(mqMaxPri))
        cells.append(createAddressCell(mqStart))
        cells.append(createTextCell(mqSize))
        cells.append(createTextCell(attributes))
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
