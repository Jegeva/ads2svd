# Copyright (C) 2015,2017 Arm Limited (or its affiliates). All rights reserved.

from kernel import *
from osapi import *

"""
Data table for eForce uC3 eventflag structures
"""

class Eventflags( Table ):

    def __init__(self):

        cid = 'eventflags'

        fields = [createPrimaryField(cid, 'id', DECIMAL)]

        fields.append(createField(cid, 'name', TEXT))
        fields.append(createField(cid, 'pattern', TEXT))
        fields.append(createField(cid, 'attributes', TEXT))
        fields.append(createField(cid, 'waiting_queue', TEXT))

        Table.__init__(self, cid, fields)


    def getRecords(self, debugger):

        records = []

        systbl = debugger.evaluateExpression('_kernel_systbl').getStructureMembers()
        qflg = systbl['qflg'].getStructureMembers()

        if qflg['inf'].readAsNumber() == 0:
            return records

        info = qflg['inf'].dereferencePointer().getStructureMembers()
        limit = info['limit'].readAsNumber()
        eventflags = qflg['flg'].getArrayElements(limit+1)

        for index in range(1, limit+1):
            eventflag = eventflags[index]
            if eventflag.readAsNumber() != 0:
                records.append(self.createFlgRecord(debugger, systbl, index, eventflag.dereferencePointer()))

        return records

    def createFlgRecord(self, debugger, systbl, id, eventflag_obj):
        cells = []
        eventflag = eventflag_obj.getStructureMembers()

        # Get the eventflag information.
        flg_name = readPotentiallyNullString(eventflag['name'])
        flg_pattern  = eventflag['flgptn'].readAsNumber()
        flg_attributes = eventflag['flgatr'].readAsNumber()
        attributes = self.readFlgAttributes(flg_attributes)

        # Get the wait queue information.
        wqIsFIFO = getWaitingQueueIsFIFO(debugger, flg_attributes)
        if wqIsFIFO:
            wqElements = getFIFOWaitingQueue(systbl, eventflag['que'])
        else:
            wqElements = getPriorityWaitingQueue(systbl, eventflag['que'])

        # Build the cells.
        cells.append(createNumberCell(id))
        cells.append(createTextCell(flg_name))
        cells.append(createTextCell("0x%08X" % (flg_pattern)))
        cells.append(createTextCell(attributes))
        cells.append(createTextCell(wqElements))

        return self.createRecord(cells)

    def readFlgAttributes(self, atr):
        attributes = []
        if (atr & TA_TPRI):
            attributes.append(ATTRIBUTES_WQU[TA_TPRI])
        else:
            attributes.append(ATTRIBUTES_WQU[TA_TFIFO])

        if (atr & TA_WMUL):
            attributes.append(ATTRIBUTES_FLG[TA_WMUL])
        else:
            attributes.append(ATTRIBUTES_FLG[TA_WSGL])

        if (atr & TA_CLR):
            attributes.append(ATTRIBUTES_FLG[TA_CLR])

        return ' | '.join(attributes)
