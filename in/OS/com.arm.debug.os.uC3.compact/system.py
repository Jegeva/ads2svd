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

        systbl = debugger.evaluateExpression("_kernel_systbl").getStructureMembers()
        cnstbl = debugger.evaluateExpression("_kernel_cnstbl").getStructureMembers()
        max_id = cnstbl['id_max'].readAsNumber()
        min_id = cnstbl['tskpri_max'].readAsNumber()+1
        atrtbl_elements = cnstbl['atrtbl'].getArrayElements(max_id+1)
        resource_counts = self.getResourceCounts(atrtbl_elements, min_id, max_id)
        cpudep = systbl['cpudep'].getStructureMembers()

        records = []

        # Resources for each data structure
        records.append(self.createResourceRecord('system.items.taskres', TS_TSK, resource_counts))
        records.append(self.createResourceRecord('system.items.semres',  TS_SEM, resource_counts))
        records.append(self.createResourceRecord('system.items.flgres',  TS_FLG, resource_counts))
        records.append(self.createResourceRecord('system.items.dtqres',  TS_DTQ, resource_counts))
        records.append(self.createResourceRecord('system.items.mbxres',  TS_MBX, resource_counts))
        records.append(self.createResourceRecord('system.items.mpfres',  TS_MPF, resource_counts))
        records.append(self.createResourceRecord('system.items.cycres',  TS_CYC, resource_counts))
        records.append(self.createResourceRecord('system.items.stkres',  TS_STK, resource_counts))
        records.append(self.createSeparator())

        # Functions
        records.append(self.createFunctionRecord('system.items.timefunc', cnstbl, 'ctrtim'))
        records.append(self.createFunctionRecord('system.items.idlefunc', cnstbl, 'sysidl'))
        records.append(self.createSeparator())

        # Misc
        records.append(self.createNonZeroNumberRecord('system.items.curtask', systbl['run'].readAsNumber()))
        records.append(self.createNonZeroNumberRecord('system.items.curpri', systbl['pri'].readAsNumber()))
        records.append(self.createNonZeroNumberRecord('system.items.basepri', cpudep['basepri'].readAsNumber()))
        records.append(self.createHexstringRecord(    'system.items.primask', cpudep['primask'].readAsNumber()))

        return records

    def getResourceCounts(self, atrtbl_elements, min_id, max_id):
        attribute_counts = {
            TS_TMR: 0,
            TS_RDY: 0,
            TS_STK: 0,
            TS_CYC: 0,
            TS_TSK: 0,
            TS_SEM: 0,
            TS_FLG: 0,
            TS_DTQ: 0,
            TS_MBX: 0,
            TS_MPF: 0,
        }
        for id in range(min_id, max_id+1):
            id_atr = atrtbl_elements[id].readAsNumber() & 0xF0L
            if id_atr in attribute_counts:
                attribute_counts[id_atr] += 1
        return attribute_counts

    def createResourceRecord(self, row_key, row_value, resource_counts):
        cells = []

        cells.append(createLocalisedTextCell(row_key))
        cells.append(createLocalisedTextCell('system.items.resources', resource_counts[row_value]))

        return self.createRecord(cells)

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

    def createNonZeroNumberRecord(self, key, number):
        cells = [createLocalisedTextCell(key)]
        if number > 0:
            cells.append(createTextCell(str(number)))
        else:
            cells.append(createTextCell(None))
        return self.createRecord(cells)

    def createHexstringRecord(self, key, number):
        return self.createRecord([createLocalisedTextCell(key), createTextCell("0x%08X" % (number))])
