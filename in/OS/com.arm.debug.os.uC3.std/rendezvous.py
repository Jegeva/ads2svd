# Copyright (C) 2015,2017 Arm Limited (or its affiliates). All rights reserved.

from kernel import *
from osapi import *

"""
Data table for eForce uC3 rendezvous structures
"""

class Rendezvous( Table ):

    def __init__(self):

        cid = 'rendezvous'

        fields = [createPrimaryField(cid, 'id', DECIMAL)]

        fields.append(createField(cid, 'name', TEXT))
        fields.append(createField(cid, 'max_call_size', DECIMAL))
        fields.append(createField(cid, 'max_reply_size', DECIMAL))
        fields.append(createField(cid, 'attributes', TEXT))
        fields.append(createField(cid, 'call_waiting_queue', TEXT))
        fields.append(createField(cid, 'reply_waiting_queue', TEXT))

        Table.__init__(self, cid, fields)


    def getRecords(self, debugger):

        records = []

        systbl = debugger.evaluateExpression('_kernel_systbl').getStructureMembers()
        qpor = systbl['qpor'].getStructureMembers()

        if qpor['inf'].readAsNumber() == 0:
            return records

        info = qpor['inf'].dereferencePointer().getStructureMembers()
        limit = info['limit'].readAsNumber()
        ports = qpor['por'].getArrayElements(limit+1)

        for index in range(1, limit+1):
            port = ports[index]
            if port.readAsNumber() != 0:
                records.append(self.createPorRecord(debugger, systbl, index, port.dereferencePointer()))

        return records

    def createPorRecord(self, debugger, systbl, id, port_obj):
        cells = []
        port = port_obj.getStructureMembers()

        # Get the rendezvous information.
        # The name field of the Rendezvous data structure is currently not correctly
        # populated and will read as null for now.
        por_name = readPotentiallyNullString(port['name'])
        por_attr = port['poratr'].readAsNumber()
        por_max_call_size  = port['maxcmsz'].readAsNumber()
        por_max_reply_size = port['maxrmsz'].readAsNumber()
        attributes = self.readPorAttributes(por_attr)

        # Get the call wait queue information.
        call_wqIsFIFO = getWaitingQueueIsFIFO(debugger, por_attr)
        if call_wqIsFIFO:
            call_wqElements = getFIFOWaitingQueue(systbl, port['cque'])
        else:
            call_wqElements = getPriorityWaitingQueue(systbl, port['cque'])

        # Get the reply wait queue information.
        rply_wqElements = ', '.join(getInternalWaitingQueue(port['aque']))

        # Build the cells.
        cells.append(createNumberCell(id))
        cells.append(createTextCell(por_name))
        cells.append(createNumberCell(por_max_call_size))
        cells.append(createNumberCell(por_max_reply_size))
        cells.append(createTextCell(attributes))
        cells.append(createTextCell(call_wqElements))
        cells.append(createTextCell(rply_wqElements))

        return self.createRecord(cells)

    def readPorAttributes(self, atr):
        if (atr & TA_TPRI):
            return ATTRIBUTES_WQU[TA_TPRI]
        return ATTRIBUTES_WQU[TA_TFIFO]
