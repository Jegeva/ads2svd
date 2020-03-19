# Copyright (C) 2015,2017 Arm Limited (or its affiliates). All rights reserved.

from kernel import *
from osapi import *

"""
Data table for eForce uC3 Compact task structures
"""

class Tasks( Table ):

    def __init__(self):

        cid = 'tasks'

        fields = []
        fields.append(createPrimaryField(cid, 'id', DECIMAL))
        fields.append(createField(cid, 'name', TEXT))
        fields.append(createField(cid, 'addr', ADDRESS))
        fields.append(createField(cid, 'func', TEXT))
        fields.append(createField(cid, 'state', TEXT))
        fields.append(createField(cid, 'priority', DECIMAL))
        fields.append(createField(cid, 'waitstatus', TEXT))
        fields.append(createField(cid, 'timeremain', TEXT))
        fields.append(createField(cid, 'actcnt', DECIMAL))
        fields.append(createField(cid, 'wupcnt', DECIMAL))
        fields.append(createField(cid, 'suscnt', DECIMAL))
        fields.append(createField(cid, 'attributes', TEXT))
        fields.append(createField(cid, 'stkalloc', TEXT))
        fields.append(createField(cid, 'stksize', DECIMAL))
        fields.append(createField(cid, 'stkptr', ADDRESS))
        fields.append(createField(cid, 'stkload', TEXT))

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
            if (id_atr & 0xF0L) == TS_TSK:
                tcb_addr = ctrtbl_elements[id]
                inf_addr = inftbl_elements[id]
                if tcb_addr.readAsNumber() == 0 or inf_addr.readAsNumber() == 0:
                    continue
                tcb_members = tcb_addr.dereferencePointer("T_TCB*").getStructureMembers()
                inf_members = inf_addr.dereferencePointer("T_CTSK*").getStructureMembers()
                wqu_members = waique_elements[id].getStructureMembers()
                id_name = readPotentiallyNullString(namtbl_elements[id])
                records.append(self.createTaskRecord(debugger, systbl, cnstbl, id, id_atr, tcb_members, inf_members, wqu_members, id_name))

        return records

    def createTaskRecord(self, debugger, systbl, cnstbl, id, atr, tcb, inf, wqu, name):

        # Get system information
        current_task_id = systbl['run'].readAsNumber()
        # Get task information
        task_addr = inf['task'].readAsAddress()
        task_func = inf['task'].resolveAddressAsString()
        state_code, state_label = getTaskState(systbl, tcb, id)
        curr_pri = tcb['cpri'].readAsNumber()
        # Get wait information
        wobjid, wait_code, wait_label = getTaskWaitState(cnstbl, tcb, state_code)
        wait_time = getTaskRemainingWaitTime(systbl, cnstbl, tcb)
        # Get event counts
        act_cnt = tcb['act'].readAsNumber()
        wup_cnt = tcb['wup'].readAsNumber()
        sus_cnt = 0 # Suspend count (part of the specification) is always 0 in compact.
        # Get attributes
        attributes = self.readTskAttributes(atr)
        # Calculate stack usage
        stack_bottom = inf['stk'].readAsAddress()
        stack_size = inf['stksz'].readAsNumber()
        stack_top = stack_bottom.addOffset(stack_size)
        stack_ptr  = tcb['ctx'].getStructureMembers()['sp'].readAsAddress()
        # The current task's stack pointer will be in $SP.
        if id == current_task_id:
            stack_ptr = debugger.evaluateExpression('$SP').readAsAddress()
        # Unrun tasks will have a 0 stack pointer.
        if stack_ptr.getLinearAddress() == 0:
            stack_ptr = None
            stack_load = None
        else:
            stack_load = ((stack_top.getLinearAddress() - stack_ptr.getLinearAddress()) * 100.0) / stack_size

        cells = []
        # Task information
        cells.append(createNumberCell(id))
        cells.append(createTextCell(name))
        cells.append(createAddressCell(task_addr))
        cells.append(createTextCell(task_func))
        cells.append(createLocalisedTextCell(state_label))
        cells.append(createNumberCell(curr_pri))
        # Wait information
        if wait_code != None:
            if wobjid != None and wobjid != 0:
                cells.append(createTextCell("%s ID:%d" % (wait_label, wobjid)))
            else:
                cells.append(createTextCell(wait_label))
            if wait_time != None:
                cells.append(createTextCell(str(wait_time)))
            else:
                cells.append(createTextCell('TMO_FEVR'))
        else:
            cells.append(createTextCell(None))
            cells.append(createTextCell(None))
        # Event counts
        cells.append(createNumberCell(act_cnt))
        cells.append(createNumberCell(wup_cnt))
        cells.append(createNumberCell(sus_cnt))
        # Attributes
        cells.append(createTextCell(attributes))
        # Stack information
        cells.append(createTextCell(' - '.join([str(stack_bottom), str(stack_top)])))
        cells.append(createNumberCell(stack_size))
        if stack_ptr != None:
            cells.append(createAddressCell(stack_ptr))
            if stack_load < 0.0 or stack_load > 100.0:
                cells.append(createTextCell(""))
            else:
                cells.append(createTextCell("%.0f%%" % (stack_load)))
        else:
            cells.append(createTextCell(None))
            cells.append(createTextCell(None))

        return self.createRecord(cells)

    def readTskAttributes(self, atr):
        attributes = []
        # TA_HLNG is always specified in the Compact profile.
        attributes.append(ATTRIBUTES_TSK[TA_HLNG])

        if (atr & TA_ACT):
            attributes.append(ATTRIBUTES_TSK[TA_ACT])

        if (atr & TA_RSTR):
            attributes.append(ATTRIBUTES_TSK[TA_RSTR])

        if (atr & TA_FPU):
            attributes.append(ATTRIBUTES_TSK[TA_FPU])

        return ' | '.join(attributes)
