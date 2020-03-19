# Copyright (C) 2015,2017 Arm Limited (or its affiliates). All rights reserved.

from kernel import *
from osapi import *

"""
Data table for eForce uC3 Alarm Handler structures
"""

class AlarmHandlers( Table ):

    def __init__(self):
        cid = 'alarm_handlers'

        fields = [createPrimaryField(cid, 'id', DECIMAL)]

        fields.append(createField(cid, 'name', TEXT))
        fields.append(createField(cid, 'address', ADDRESS))
        fields.append(createField(cid, 'function', TEXT))
        fields.append(createField(cid, 'remaining', DECIMAL))
        fields.append(createField(cid, 'running', TEXT))
        fields.append(createField(cid, 'pending', TEXT))
        fields.append(createField(cid, 'attributes', TEXT))

        Table.__init__(self, cid, fields)

    def getRecords(self, debugger):
        records = []

        systbl = debugger.evaluateExpression('_kernel_systbl').getStructureMembers()
        qalm = systbl['qalm'].getStructureMembers()

        if qalm['inf'].readAsNumber() == 0:
            return records

        info = qalm['inf'].dereferencePointer().getStructureMembers()
        limit = info['limit'].readAsNumber()
        handlers = qalm['alm'].getArrayElements(limit+1)

        for index in range(1, limit+1):
            handler = handlers[index]
            if handler.readAsNumber() != 0:
                records.append(self.createAlmRecord(debugger, systbl, index, handler.dereferencePointer()))

        return records

    def createAlmRecord(self, debugger, systbl, id, handler_obj):
        cells = []
        TALM_STP = 0x00
        TALM_STA = 0x01
        TALM_RST = 0x02
        TALM_PND = 0x10

        handler = handler_obj.getStructureMembers()

        # Get the alarm handler's information.
        status = handler['stat'].getStructureMembers()
        msts = status['msts'].readAsNumber()
        alm_attr = status['oatr'].readAsNumber()

        name = readPotentiallyNullString(handler['name'])
        handler_addr = handler['almhdr'].readAsAddress()
        handler_func = handler['almhdr'].resolveAddressAsString()
        remaining_time = getAlarmHandlerRemainingWaitTime(TALM_STA, TALM_RST, systbl, handler, msts)
        attributes = self.readAlmAttributes(alm_attr)

        running_mode = 'misc.no' if ((msts & TALM_STA) == 0) else 'misc.yes'
        pending_mode = 'misc.no' if ((msts & TALM_PND) == 0) else 'misc.yes'

        # Build the cells.
        cells.append(createNumberCell(id))
        cells.append(createTextCell(name))
        cells.append(createAddressCell(handler_addr))
        cells.append(createTextCell(handler_func))
        cells.append(createNumberCell(remaining_time))
        cells.append(createLocalisedTextCell(running_mode))
        cells.append(createLocalisedTextCell(pending_mode))
        cells.append(createTextCell(attributes))

        return self.createRecord(cells)

    def readAlmAttributes(self, atr):
        if (atr & TA_ASM):
            return ATTRIBUTES_TSK[TA_ASM]
        return ATTRIBUTES_TSK[TA_HLNG]
