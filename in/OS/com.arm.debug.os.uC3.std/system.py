# Copyright (C) 2015,2017 Arm Limited (or its affiliates). All rights reserved.

from kernel import *
from osapi import *

"""
Data table for eForce uC3 system information
"""

class System( Table ):

    def __init__(self):

        cid = 'system'

        fields = [ createField(cid, 'item', TEXT), createField(cid, 'value', TEXT) ]

        Table.__init__(self, cid, fields)

    def getRecords(self, debugger):

        systbl = debugger.evaluateExpression('_kernel_systbl').getStructureMembers()

        records = []

        records.append(self.createMemoryRecord('system.items.sysmem', systbl, 'free_sys'))
        records.append(self.createMemoryRecord('system.items.stkmem', systbl, 'free_stk'))
        records.append(self.createMemoryRecord('system.items.mplmem', systbl, 'free_mpl'))
        records.append(self.createSeparator())
        records.append(self.createResourceRecord('system.items.taskres', systbl, 'qtcb'))
        records.append(self.createResourceRecord('system.items.semres', systbl, 'qsem'))
        records.append(self.createResourceRecord('system.items.flgres', systbl, 'qflg'))
        records.append(self.createResourceRecord('system.items.dtqres', systbl, 'qdtq'))
        records.append(self.createResourceRecord('system.items.mbxres', systbl, 'qmbx'))
        records.append(self.createResourceRecord('system.items.mtxres', systbl, 'qmtx'))
        records.append(self.createResourceRecord('system.items.mbfres', systbl, 'qmbf'))
        records.append(self.createResourceRecord('system.items.porres', systbl, 'qpor'))
        records.append(self.createResourceRecord('system.items.mpfres', systbl, 'qmpf'))
        records.append(self.createResourceRecord('system.items.mplres', systbl, 'qmpl'))
        records.append(self.createResourceRecord('system.items.almres', systbl, 'qalm'))
        records.append(self.createResourceRecord('system.items.cycres', systbl, 'qcyc'))
        records.append(self.createResourceRecord('system.items.isrres', systbl, 'qisr'))
        records.append(self.createSeparator())
        records.append(self.createOverrunHandlerRecord(systbl))
        records.append(self.createFunctionRecord('system.items.timefunc', systbl, 'ctrtim'))
        records.append(self.createFunctionRecord('system.items.idlefunc', systbl, 'sysidl'))
        records.append(self.createFunctionRecord('system.items.stkfunc', systbl, 'inistk'))

        return records

    def createMemoryRecord(self, key, systbl, pool_member):
        cells = []

        cells.append(createLocalisedTextCell(key))
        cells.append(createLocalisedTextCell('system.items.memory', getFreeMem(systbl[pool_member])))

        return self.createRecord(cells)

    def createResourceRecord(self, key, systbl, queue_member):
        cells = []

        cells.append(createLocalisedTextCell(key))
        cells.append(createLocalisedTextCell('system.items.resources', getQueueInf(systbl, queue_member)))

        return self.createRecord(cells)

    def createOverrunHandlerRecord(self, systbl):
        tovr = systbl['ovr']

        if tovr.readAsNumber() == 0:
            cells = []
            cells.append(createLocalisedTextCell('system.items.ovrhdr'))
            cells.append(createLocalisedTextCell('system.items.nofunc'))
            return self.createRecord(cells)
        else:
            return self.createFunctionRecord('system.items.ovrhdr', tovr.dereferencePointer().getStructureMembers(), 'ovrhdr')

    def createFunctionRecord(self, key, struct, func_member):
        cells = []

        cells.append(createLocalisedTextCell(key))

        func_ptr = struct[func_member]

        if func_ptr.readAsNumber() == 0:
            cells.append(createLocalisedTextCell('system.items.nofunc'))
        else:
            cells.append(createTextCell(func_ptr.resolveAddressAsString()))

        return self.createRecord(cells)

    def createSeparator(self):
        return self.createRecord([createTextCell(''),createTextCell('')])
