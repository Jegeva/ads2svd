# Copyright (C) 2015,2017 Arm Limited (or its affiliates). All rights reserved.

from kernel import *
from osapi import *

"""
Data table for eForce uC3 Compact shared stack structures
"""

class SharedStacks( Table ):

    def __init__(self):

        cid = 'shared_stacks'

        fields = [createPrimaryField(cid, 'id', DECIMAL)]

        fields.append(createField(cid, 'name', TEXT))
        fields.append(createField(cid, 'tasks', TEXT))
        fields.append(createField(cid, 'address', ADDRESS))
        fields.append(createField(cid, 'size', DECIMAL))

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

        for id in range(min_id, max_id+1):
            id_atr = atrtbl_elements[id].readAsNumber()
            if (id_atr & 0xF0L) == TS_STK:
                stk_addr = ctrtbl_elements[id]
                if stk_addr.readAsNumber() == 0:
                    continue
                id_name = readPotentiallyNullString(namtbl_elements[id])
                records.append(self.createStkRecord(id, id_name, min_id, max_id, atrtbl_elements, inftbl_elements))

        return records

    def createStkRecord(self, stk_id, stk_name, min_id, max_id, atrtbl_elements, inftbl_elements):
        cells = []

        # The shared stack does not hold any information of its own. Instead we
        # must go through all tasks and determine whether or not they are using
        # this stack.
        stack_tasks_info = []
        for tsk_id in range(min_id, max_id+1):
            tsk_atr = atrtbl_elements[tsk_id].readAsNumber()
            if (tsk_atr & 0xF0L) == TS_TSK:
                tsk_inf = inftbl_elements[tsk_id].dereferencePointer("T_CTSK*").getStructureMembers()
                if tsk_inf['stkno'].readAsNumber() == stk_id:
                    tsk_stk_addr = tsk_inf['stk'].readAsAddress()
                    tsk_stk_size = tsk_inf['stksz'].readAsNumber()
                    stack_tasks_info.append((tsk_id, tsk_stk_addr, tsk_stk_size))

        # Collate the stack information we have collected. We must deal with the
        # possibility that each task could theoretically have different information
        # about the stack (e.g. two tasks could share a stack but one could only
        # only have access to half). In the case they differ, the true information
        # is probably the lowest stack_addr and the highest stack_size, but err on
        # the side of caution and blank the columns out if they don't agree.
        if len(stack_tasks_info) > 0:
            stack_tasks = [str(stack_tasks_info[0][0])]
            stack_addr  =      stack_tasks_info[0][1]
            stack_size  =      stack_tasks_info[0][2]
            for i in range(1, len(stack_tasks_info)):
                stack_tasks.append(str(stack_tasks_info[i][0]))
                task_stack_addr =      stack_tasks_info[i][1]
                task_stack_size =      stack_tasks_info[i][2]
                if stack_addr != task_stack_addr:
                    stack_addr = None
                if stack_size != task_stack_size:
                    stack_size = None
        else:
            stack_tasks = []
            stack_addr = None
            stack_size = None

        # Build the cells.
        cells.append(createNumberCell(stk_id))
        cells.append(createTextCell(stk_name))
        cells.append(createTextCell(', '.join(stack_tasks)))
        cells.append(createAddressCell(stack_addr))
        cells.append(createNumberCell(stack_size))

        return self.createRecord(cells)
