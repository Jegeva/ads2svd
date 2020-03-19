# Copyright (C) 2015,2017 Arm Limited (or its affiliates). All rights reserved.

from kernel import *
from osapi import *

"""
Data table for eForce uC3 Compact Cyclic Handler structures
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

        systbl = debugger.evaluateExpression("_kernel_systbl").getStructureMembers()
        cnstbl = debugger.evaluateExpression("_kernel_cnstbl").getStructureMembers()
        max_id = cnstbl['id_max'].readAsNumber()
        min_id = cnstbl['tskpri_max'].readAsNumber()+1

        atrtbl_elements = cnstbl['atrtbl'].getArrayElements(max_id+1)
        ctrtbl_elements = cnstbl['ctrtbl'].getArrayElements(max_id+1)
        inftbl_elements = cnstbl['inftbl'].getArrayElements(max_id+1)
        namtbl_elements = cnstbl['objname'].getArrayElements(max_id+1)
        waique_elements = cnstbl['waique'].getArrayElements(max_id+1)

        for id in range(min_id, max_id+1):
            id_atr = atrtbl_elements[id].readAsNumber()
            if (id_atr & 0xF0L) == TS_CYC:
                cyc_addr = ctrtbl_elements[id]
                inf_addr = inftbl_elements[id]
                if cyc_addr.readAsNumber() == 0 or inf_addr.readAsNumber() == 0:
                    continue
                cyc_members = cyc_addr.dereferencePointer("T_CYC*").getStructureMembers()
                inf_members = inf_addr.dereferencePointer("T_CCYC*").getStructureMembers()
                wqu_members = waique_elements[id].getStructureMembers()
                id_name = readPotentiallyNullString(namtbl_elements[id])
                records.append(self.createCycRecord(debugger, systbl, cnstbl, id, id_atr, cyc_members, inf_members, wqu_members, id_name))
        return records

    def createCycRecord(self, debugger, systbl, cnstbl, id, atr, cyc, inf, wqu, name):
        cells = []
        TCYC_STP = 0x00
        TCYC_STA = 0x01
        TCYC_PND = 0x10

        # Get the cyclic handler's information.
        cyc_atr = self.readCycAttributes(atr)
        msts = cyc['msts'].readAsNumber()
        cycle_interval = inf['cyctim'].readAsNumber()
        address = inf['cychdr'].readAsAddress()
        function = inf['cychdr'].resolveAddressAsString()
        time_remaining = getCyclicHandlerRemainingWaitTime(TCYC_STA, systbl, cnstbl, cyc)

        running_mode = 'misc.no' if ((msts & TCYC_STA) == 0) else 'misc.yes'
        pending_mode = 'misc.no' if ((msts & TCYC_PND) == 0) else 'misc.yes'

        # Build the cells.
        cells.append(createNumberCell(id))
        cells.append(createTextCell(name))
        cells.append(createAddressCell(address))
        cells.append(createTextCell(function))
        cells.append(createNumberCell(cycle_interval))
        cells.append(createNumberCell(time_remaining))
        cells.append(createLocalisedTextCell(running_mode))
        cells.append(createLocalisedTextCell(pending_mode))
        cells.append(createTextCell(cyc_atr))

        return self.createRecord(cells)

    def readCycAttributes(self, atr):
        attributes = []
        # TA_HLNG is always specified in the Compact profile.
        attributes.append(ATTRIBUTES_TSK[TA_HLNG])

        if (atr & TA_STA):
            attributes.append(ATTRIBUTES_CYC[TA_STA])

        if (atr & TA_PHS):
            attributes.append(ATTRIBUTES_CYC[TA_PHS])

        return ' | '.join(attributes)
