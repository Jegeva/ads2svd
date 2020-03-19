# Copyright (C) 2015,2017 Arm Limited (or its affiliates). All rights reserved.

from kernel import *
from osapi import *

"""
Data table for eForce uC3 Interrupt Service Routine structures
"""

class InterruptServiceRoutines( Table ):

    def __init__(self):
        cid = 'interrupt_service_routines'

        fields = [createPrimaryField(cid, 'id', DECIMAL)]

        fields.append(createField(cid, 'address', ADDRESS))
        fields.append(createField(cid, 'function', TEXT))
        fields.append(createField(cid, 'interrupt', DECIMAL))
        fields.append(createField(cid, 'attributes', TEXT))

        Table.__init__(self, cid, fields)

    def getRecords(self, debugger):
        records = []

        systbl = debugger.evaluateExpression('_kernel_systbl').getStructureMembers()
        qisr = systbl['qisr'].getStructureMembers()

        if qisr['inf'].readAsNumber() == 0:
            return records

        info = qisr['inf'].dereferencePointer().getStructureMembers()
        limit = info['limit'].readAsNumber()
        handlers = qisr['isr'].getArrayElements(limit+1)

        for index in range(1, limit+1):
            handler = handlers[index]
            if handler.readAsNumber() != 0:
                records.append(self.createIsrRecord(debugger, systbl, index, handler.dereferencePointer()))

        return records

    def createIsrRecord(self, debugger, systbl, id, handler_obj):
        cells = []
        handler = handler_obj.getStructureMembers()

        # Get the ISR's information.
        handler_addr = handler['isr'].readAsAddress()
        handler_func = handler['isr'].resolveAddressAsString()
        isr_atr = handler['isratr'].readAsNumber()
        interrupt_number = handler['intno'].readAsNumber()
        attributes = self.readIsrAttributes(isr_atr)

        # Build the cells.
        cells.append(createNumberCell(id))
        cells.append(createAddressCell(handler_addr))
        cells.append(createTextCell(handler_func))
        cells.append(createNumberCell(interrupt_number))
        cells.append(createTextCell(attributes))

        return self.createRecord(cells)


    def readIsrAttributes(self, atr):
        if (atr & TA_ASM):
            return ATTRIBUTES_TSK[TA_ASM]
        return ATTRIBUTES_TSK[TA_HLNG]
