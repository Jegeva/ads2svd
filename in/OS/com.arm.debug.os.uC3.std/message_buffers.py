# Copyright (C) 2015,2017 Arm Limited (or its affiliates). All rights reserved.

from kernel import *
from osapi import *

"""
Data table for eForce uC3 mailbox structures
"""

class MessageBuffers( Table ):

    def __init__(self):

        cid = 'message_buffers'

        fields = [createPrimaryField(cid, 'id', DECIMAL)]

        fields.append(createField(cid, 'name', TEXT))
        fields.append(createField(cid, 'message_count', DECIMAL))
        fields.append(createField(cid, 'total_buffer_size', DECIMAL))
        fields.append(createField(cid, 'free_buffer_size', DECIMAL))
        fields.append(createField(cid, 'max_msg_size', DECIMAL))
        fields.append(createField(cid, 'start_addr', ADDRESS))
        fields.append(createField(cid, 'attributes', TEXT))
        fields.append(createField(cid, 'snd_waiting_queue', TEXT))
        fields.append(createField(cid, 'rcv_waiting_queue', TEXT))

        Table.__init__(self, cid, fields)

    def getRecords(self, debugger):

        records = []

        systbl = debugger.evaluateExpression('_kernel_systbl').getStructureMembers()
        qmbf = systbl['qmbf'].getStructureMembers()

        if qmbf['inf'].readAsNumber() == 0:
            return records

        info = qmbf['inf'].dereferencePointer().getStructureMembers()
        limit = info['limit'].readAsNumber()
        message_buffers = qmbf['mbf'].getArrayElements(limit+1)

        for index in range(1, limit+1):
            message_buffer = message_buffers[index]
            if message_buffer.readAsNumber() != 0:
                records.append(self.createMbfRecord(debugger, systbl, index, message_buffer.dereferencePointer()))

        return records

    def createMbfRecord(self, debugger, systbl, id, message_buffer_obj):
        cells = []
        message_buffer = message_buffer_obj.getStructureMembers()

        # Get the message buffer information.
        mbf_name = readPotentiallyNullString(message_buffer['name'])
        mbf_attributes = message_buffer['mbfatr'].readAsNumber()
        attributes = self.readMbfAttributes(mbf_attributes)

        mbf_message_count     = message_buffer['cnt'].readAsNumber()
        mbf_total_buffer_size = message_buffer['mbfsz'].readAsNumber()
        mbf_free_buffer_size  = message_buffer['frsz'].readAsNumber()
        mbf_max_msg_size      = message_buffer['maxmsz'].readAsNumber()
        mbf_start_addr        = message_buffer['mbf'].readAsAddress()

        # Get the send wait queue information.
        snd_wqIsFIFO = getWaitingQueueIsFIFO(debugger, mbf_attributes)
        if snd_wqIsFIFO:
            snd_wqElements = getFIFOWaitingQueue(systbl, message_buffer['sque'])
        else:
            snd_wqElements = getPriorityWaitingQueue(systbl, message_buffer['sque'])

        # Get the receive wait queue information.
        rcv_wqElements = ', '.join(getInternalWaitingQueue(message_buffer['wque']))

        # Build the cells.
        cells.append(createNumberCell(id))
        cells.append(createTextCell(mbf_name))
        cells.append(createNumberCell(mbf_message_count))
        cells.append(createNumberCell(mbf_total_buffer_size))
        cells.append(createNumberCell(mbf_free_buffer_size))
        cells.append(createNumberCell(mbf_max_msg_size))
        cells.append(createAddressCell(mbf_start_addr))
        cells.append(createTextCell(attributes))
        cells.append(createTextCell(snd_wqElements))
        cells.append(createTextCell(rcv_wqElements))

        return self.createRecord(cells)

    def readMbfAttributes(self, atr):
        if (atr & TA_TPRI):
            return ATTRIBUTES_WQU[TA_TPRI]
        return ATTRIBUTES_WQU[TA_TFIFO]
