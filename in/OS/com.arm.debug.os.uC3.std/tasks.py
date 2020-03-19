# Copyright (C) 2015,2017 Arm Limited (or its affiliates). All rights reserved.

from kernel import *
from osapi import *

"""
Data table for eForce uC3 task structures
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
        fields.append(createField(cid, 'curr_pri', DECIMAL))
        fields.append(createField(cid, 'base_pri', DECIMAL))
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

        systbl = debugger.evaluateExpression('_kernel_systbl').getStructureMembers()
        qtcb = systbl['qtcb'].getStructureMembers()

        if qtcb['inf'].readAsNumber() == 0:
            return records

        info = qtcb['inf'].dereferencePointer().getStructureMembers()
        limit = info['limit'].readAsNumber()
        tasks = qtcb['tcb'].getArrayElements(limit+1)

        for index in range(1, limit+1):
            tcb = tasks[index]
            tcb_addr = tcb.readAsNumber()
            if tcb_addr != 0:
                records.append(self.createTaskRecord(debugger, systbl, index, tcb.dereferencePointer(), tcb_addr))

        return records

    def createTaskRecord(self, debugger, systbl, id, tcb, tcb_addr):

        tcb_members = tcb.getStructureMembers()

        # Get task information
        tcb_name = readPotentiallyNullString(tcb_members['name'])
        task_addr = tcb_members['task'].readAsAddress()
        task_func = tcb_members['task'].resolveAddressAsString()
        tcb_status = tcb_members['stat'].getStructureMembers()
        state_code, state_label = getTaskState(systbl, tcb_addr, tcb_status)
        curr_pri = tcb_members['cpri'].readAsNumber()
        base_pri = tcb_members['bpri'].readAsNumber()
        # Get wait information
        wobjid, wait_code, wait_label = getTaskWaitState(tcb_members, tcb_status, state_code)
        wait_time = getTaskRemainingWaitTime(systbl, tcb_members, tcb_status)
        # Extract event counts
        act_count = tcb_members['act'].readAsNumber()
        wup_count = tcb_members['wup'].readAsNumber()
        sus_count = tcb_members['sus'].readAsNumber()
        # Attributes
        attributes = self.readTskAttributes(tcb_status['oatr'].readAsNumber())
        # Calculate stack usage
        stack_bottom = tcb_members['stk'].readAsAddress()
        stack_size = tcb_members['stksz'].readAsNumber()
        stack_top = stack_bottom.addOffset(stack_size)
        stack_ptr  = tcb_members['sp'].readAsAddress()
        if stack_ptr.getLinearAddress() == 0:
            stack_ptr = debugger.evaluateExpression('$SP').readAsAddress()
        stack_load = ((stack_top.getLinearAddress() - stack_ptr.getLinearAddress()) * 100.0) / stack_size

        cells = []
        # Task information
        cells.append(createNumberCell(id))
        cells.append(createTextCell(tcb_name))
        cells.append(createAddressCell(task_addr))
        cells.append(createTextCell(task_func))
        cells.append(createLocalisedTextCell(state_label))
        cells.append(createNumberCell(curr_pri))
        cells.append(createNumberCell(base_pri))
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
        cells.append(createNumberCell(act_count))
        cells.append(createNumberCell(wup_count))
        cells.append(createNumberCell(sus_count))
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

        if (atr & TA_ASM):
            attributes.append(ATTRIBUTES_TSK[TA_ASM])
        else:
            attributes.append(ATTRIBUTES_TSK[TA_HLNG])

        if (atr & TA_ACT):
            attributes.append(ATTRIBUTES_TSK[TA_ACT])

        if (atr & TA_RSTR):
            attributes.append(ATTRIBUTES_TSK[TA_RSTR])

        if (atr & TA_AUX):
            attributes.append(ATTRIBUTES_TSK[TA_AUX])

        if (atr & TA_DSP):
            attributes.append(ATTRIBUTES_TSK[TA_DSP])

        if (atr & TA_FPU):
            attributes.append(ATTRIBUTES_TSK[TA_FPU])

        if (atr & TA_VPU):
            attributes.append(ATTRIBUTES_TSK[TA_VPU])

        return ' | '.join(attributes)
