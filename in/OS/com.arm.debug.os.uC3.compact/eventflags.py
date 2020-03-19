# Copyright (C) 2015,2017 Arm Limited (or its affiliates). All rights reserved.

from kernel import *
from osapi import *

"""
Data table for eForce uC3 Compact eventflag structures
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
            if (id_atr & 0xF0L) == TS_FLG:
                flg_addr = ctrtbl_elements[id]
                inf_addr = inftbl_elements[id]
                if flg_addr.readAsNumber() == 0 or inf_addr.readAsNumber() == 0:
                    continue
                flg_members = flg_addr.dereferencePointer("T_FLG*").getStructureMembers()
                inf_members = inf_addr.dereferencePointer("T_CFLG*").getStructureMembers()
                wqu_members = waique_elements[id].getStructureMembers()
                id_name = readPotentiallyNullString(namtbl_elements[id])
                records.append(self.createFlgRecord(debugger, systbl, cnstbl, id, id_atr, flg_members, inf_members, wqu_members, id_name))

        return records

    def createFlgRecord(self, debugger, systbl, cnstbl, id, atr, flg, inf, wqu, name):
        cells = []

        # Get the eventflag information.
        flg_pattern  = flg['flgptn'].readAsNumber()
        flg_atr = self.readFlgAttributes(atr)

        # Get the wait queue information.
        wqElements = getFIFOWaitingQueue(cnstbl, id)

        # Build the cells.
        cells.append(createNumberCell(id))
        cells.append(createTextCell(name))
        cells.append(createTextCell("0x%08X" % (flg_pattern)))
        cells.append(createTextCell(flg_atr))
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
