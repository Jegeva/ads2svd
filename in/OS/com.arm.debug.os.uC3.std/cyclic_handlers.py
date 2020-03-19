# Copyright (C) 2015,2017 Arm Limited (or its affiliates). All rights reserved.

from kernel import *
from osapi import *

"""
Data table for eForce uC3 Cyclic Handler structures
"""

class CyclicHandlers( Table ):

    def __init__(self):
        cid = 'cyclic_handlers'

        fields = [createPrimaryField(cid, 'id', DECIMAL)]

        fields.append(createField(cid, 'name', TEXT))
        fields.append(createField(cid, 'address', ADDRESS))
        fields.append(createField(cid, 'function', TEXT))
        fields.append(createField(cid, 'cycle', DECIMAL))
        fields.append(createField(cid, 'remaining', DECIMAL))
        fields.append(createField(cid, 'running', TEXT))
        fields.append(createField(cid, 'pending', TEXT))
        fields.append(createField(cid, 'attributes', TEXT))

        Table.__init__(self, cid, fields)

    def getRecords(self, debugger):
        records = []

        systbl = debugger.evaluateExpression('_kernel_systbl').getStructureMembers()
        qcyc = systbl['qcyc'].getStructureMembers()

        if qcyc['inf'].readAsNumber() == 0:
            return records

        info = qcyc['inf'].dereferencePointer().getStructureMembers()
        limit = info['limit'].readAsNumber()
        handlers = qcyc['cyc'].getArrayElements(limit+1)

        for index in range(1, limit+1):
            handler = handlers[index]
            if handler.readAsNumber() != 0:
                records.append(self.createCycRecord(debugger, systbl, index, handler.dereferencePointer()))

        return records

    def createCycRecord(self, debugger, systbl, id, handler_obj):
        cells = []
        TCYC_STP = 0x00
        TCYC_STA = 0x01
        TCYC_PND = 0x10

        handler = handler_obj.getStructureMembers()

        # Get the cyclic handler's information.
        status = handler['stat'].getStructureMembers()
        msts = status['msts'].readAsNumber()
        cyc_attr = status['oatr'].readAsNumber()

        name = readPotentiallyNullString(handler['name'])
        handler_addr = handler['cychdr'].readAsAddress()
        handler_func = handler['cychdr'].resolveAddressAsString()
        cycle_interval = handler['cyctim'].readAsNumber()
        time_remaining = getCyclicHandlerRemainingWaitTime(TCYC_STA, systbl, handler, msts)
        attributes = self.readCycAttributes(cyc_attr)

        running_mode = 'misc.no' if ((msts & TCYC_STA) == 0) else 'misc.yes'
        pending_mode = 'misc.no' if ((msts & TCYC_PND) == 0) else 'misc.yes'

        # Build the cells.
        cells.append(createNumberCell(id))
        cells.append(createTextCell(name))
        cells.append(createAddressCell(handler_addr))
        cells.append(createTextCell(handler_func))
        cells.append(createNumberCell(cycle_interval))
        cells.append(createNumberCell(time_remaining))
        cells.append(createLocalisedTextCell(running_mode))
        cells.append(createLocalisedTextCell(pending_mode))
        cells.append(createTextCell(attributes))

        return self.createRecord(cells)

    def readCycAttributes(self, atr):
        attributes = []

        if (atr & TA_ASM):
            attributes.append(ATTRIBUTES_TSK[TA_ASM])
        else:
            attributes.append(ATTRIBUTES_TSK[TA_HLNG])

        if (atr & TA_STA):
            attributes.append(ATTRIBUTES_CYC[TA_STA])

        if (atr & TA_PHS):
            attributes.append(ATTRIBUTES_CYC[TA_PHS])

        return ' | '.join(attributes)
