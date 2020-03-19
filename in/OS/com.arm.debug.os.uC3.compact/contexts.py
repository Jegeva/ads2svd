# Copyright (C) 2015,2017 Arm Limited (or its affiliates). All rights reserved.

from kernel import *
from osapi import *

# VFP_STATE = 0 => OS compiled without VFP support
# VFP_STATE = 1 => OS compiled with VFP support
# Due to the way the FPU-enabled flag is saved and re-checked, VFP_STATE=1
# actually works for both states - so just use that.
VFP_STATE = 1

# The part of the register map that doesn't change
# R4-R11, R12, LR...
REG_MAP_BASE = {
    "R4"  :   0L,
    "R5"  :   4L,
    "R6"  :   8L,
    "R7"  :  12L,
    "R8"  :  16L,
    "R9"  :  20L,
    "R10" :  24L,
    "R11" :  28L,
# "CONTROL":  32L,  # This is R12 which saves _kernel_systbl.cpudep.control on M4 only
#    "LR"  :  36L,   # This is the 0xFFFFFFFD special LR value to invoke an exception return
}

# Compiled without VFP support, or VFP not enabled
# R0-R3, ??, ??, (LR), XPSR  - where ?? is unused
REG_MAP_NO_VFP = {
    "R0"  :  40L,
    "R1"  :  44L,
    "R2"  :  48L,
    "R3"  :  52L,
    "PC"  :  64L,   # This is the LR when banked - i.e. the ret addr
    "XPSR":  68L, "xPSR":  68L,   # This is the hard coded 0x01000000 value
    "SP"  :  72L,   # Offset past the entire banked stack
}

# Compiled with VFP support
# S16-S31, R0-R3, ??, ??, (LR), XPSR, ??*16, FPSCR
REG_MAP_VFP_ON = {
    "D8" :  40L,
    "D9" :  48L,
    "D10" :  56L,
    "D11" :  64L,
    "D12" :  72L,
    "D13" :  80L,
    "D14" :  88L,
    "D15" :  96L,
    "S16" :  40L,
    "S17" :  44L,
    "S18" :  48L,
    "S19" :  52L,
    "S20" :  56L,
    "S21" :  60L,
    "S22" :  64L,
    "S23" :  68L,
    "S24" :  72L,
    "S25" :  76L,
    "S26" :  80L,
    "S27" :  84L,
    "S28" :  88L,
    "S29" :  92L,
    "S30" :  96L,
    "S31" : 100L,
    "R0"  : 104L,
    "R1"  : 108L,
    "R2"  : 112L,
    "R3"  : 116L,
    "PC"  : 128L,   # This is the LR when banked - i.e. the ret addr
    "XPSR": 132L, "xPSR": 132L,   # This is the hard coded 0x01000000 value
    "FPSCR":200L,
    "SP"  : 208L,   # Offset past the entire banked stack
}

class ContextsProvider(ExecutionContextsProvider):

    def getCurrentOSContext(self, debugger):
        """
        Current task ID is stored in _kernel_systbl.run, which indexes into _kernel_cnstbl.ctrtbl
        """
        systbl = debugger.evaluateExpression("_kernel_systbl").getStructureMembers()
        cnstbl = debugger.evaluateExpression("_kernel_cnstbl").getStructureMembers()
        cur_id = systbl['run'].readAsNumber()
        max_id = cnstbl['id_max'].readAsNumber()
        min_id = cnstbl['tskpri_max'].readAsNumber()+1
        # The ctrtbl contains more than just task elements so we need to validate cur_id
        # before reading blindly with it.
        if cur_id < min_id or cur_id > max_id:
            return self.createKernelContext(debugger)

        # Read the relevant task structures
        atrtbl_element = cnstbl['atrtbl'].getArrayElement(cur_id)
        if (atrtbl_element.readAsNumber() & 0xF0L) != TS_TSK:
            return self.createKernelContext(debugger)
        ctrtbl_element = cnstbl['ctrtbl'].getArrayElement(cur_id)
        inftbl_element = cnstbl['inftbl'].getArrayElement(cur_id)
        namtbl_element = cnstbl['objname'].getArrayElement(cur_id)

        if ctrtbl_element.readAsNumber() == 0 or inftbl_element.readAsNumber() == 0:
            return self.createKernelContext(debugger)
        tcb_members = ctrtbl_element.dereferencePointer("T_TCB*").getStructureMembers()
        inf_members = inftbl_element.dereferencePointer("T_CTSK*").getStructureMembers()
        id_name = readPotentiallyNullString(namtbl_element)
        id_atr = atrtbl_element.readAsNumber()

        return self.createContext(systbl, cur_id, id_atr, tcb_members, inf_members, id_name)

    def getAllOSContexts(self, debugger):
        """
        List of tasks is 'qtcb' in _kernel_systbl.
        - 'inf->limit' - overall size of the structure, exc. the first element in
                         the list which is the info structure (qtcb is a union).
        - 'inf->usedc' - number of spaces used (exc. the info struct). The list
                         fills from the end first.
        """
        contexts = []

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
            if (id_atr & 0xF0L) == TS_TSK:
                tcb_addr = ctrtbl_elements[id]
                inf_addr = inftbl_elements[id]
                if tcb_addr.readAsNumber() == 0 or inf_addr.readAsNumber() == 0:
                    continue
                tcb_members = tcb_addr.dereferencePointer("T_TCB*").getStructureMembers()
                inf_members = inf_addr.dereferencePointer("T_CTSK*").getStructureMembers()
                id_name = readPotentiallyNullString(namtbl_elements[id])
                contexts.append(self.createContext(systbl, id, id_atr, tcb_members, inf_members, id_name))

        return contexts

    # Returns a dictionary with the non-base component register map,
    # based on the VFP state
    def extractRegMap(self, debugger, sp):
        # The task can be in a number of states (although far fewer than the
        # standard profile):
        # 0. Indeterminate
        # 1. Compiled without VFP Support
        # 2. Compiled with VFP support in a non-VFP function
        # 3. Compiled with VFP support in a VFP function
        # The first 10 words (R4-R11, R12, LR) do not change. The first variable word is
        # at offset 40.

        # Detect case 1
        # We cannot reliably detect the compile-time options so rely on being
        # explicitly told we were compiled without VFP.
        if VFP_STATE == 0:
            return REG_MAP_NO_VFP

        # Distinguish cases 2 and 3
        # The CONTROL register (at offset 32) has its FP enablement bit cleared before
        # being banked so instead we read the banked LR (at offset 36) and infer from that.
        banked_lr = debugger.evaluateExpression("*((unsigned long*)" + str(sp.addOffset(36L)) + ")").readAsNumber()
        fpu_enabled = ((banked_lr & 0x10L) == 0L)
        if not fpu_enabled:
            return REG_MAP_NO_VFP
        return REG_MAP_VFP_ON

    def getOSContextSavedRegister(self, debugger, context, name):
        # NB: sp in this case contains the stack pointer to the banked registers. This is
        # NOT the stack pointer which will be re-instated from a context switch (as the
        # task will have the banked registers removed from its stack once it starts again).
        sp = context.getAdditionalData()["task_sp"]
        # User processes always use SP_PROCESS as their SP, so hard code this.
        if name == "SP_PROCESS":
            name = "SP"
        # Saved SP will be 0 if this is the current task (should never happen), or if the
        # task has never been run. In the latter case we can derive the SP from the stack
        # base and PC from task ptr, but there won't be any banked registers.
        if sp.getLinearAddress() == 0L:
            if name == "SP":
                sp_base = context.getAdditionalData()["task_stkbase"]
                sp_size = context.getAdditionalData()["task_stksize"]
                sp_addr = sp_base.addOffset(sp_size).getLinearAddress()
                return debugger.evaluateExpression("(long)" + str(sp_addr))
            elif name == "PC":
                pc_val = context.getAdditionalData()["task_taskptr"].getLinearAddress()
                return debugger.evaluateExpression("(long)" + str(pc_val))
            else:
                return None
        else:
            # Otherwise we're looking at the stack for banked registers.
            # Check if the stack is big enough to contain banked registers (we have at
            # least 18 words in banked registers, whereas only a few are pushed on at
            # task creation.
            stk_base = context.getAdditionalData()["task_stkbase"]
            stk_size = context.getAdditionalData()["task_stksize"]
            if sp.getLinearAddress() > stk_base.addOffset(stk_size - 72L).getLinearAddress():
                return None
            else:
                # First check the base register map (the parts that don't change)
                reg_offset = REG_MAP_BASE.get(name, None)
                if reg_offset is None:
                    # If we've been asked for one of the non-base components, work
                    # out what VFP state we are in
                    reg_map = self.extractRegMap(debugger, sp)
                    reg_offset = reg_map.get(name, None)
                    # If we were unable to work it out, return nothing
                    if reg_offset is None:
                        return None
                # Add the offset
                reg_addr = sp.addOffset(reg_offset)
        # If we were returning the SP this is actually the value of its address rather
        # than the value of the contents of the address.
        if name == "SP":
            return debugger.evaluateExpression("(long)"  + str(reg_addr))
        else:
            return debugger.evaluateExpression("(long*)" + str(reg_addr))

    def createContext(self, systbl, id, atr, tcb_members, inf_members, name):
        stateCode,stateStr = getTaskState(systbl, tcb_members, id)

        # Create context
        context = ExecutionContext(id, name, stateStr)

        # Store additional information in the execution context
        context.getAdditionalData()["task_sp"]      = tcb_members["ctx"].getStructureMembers()['sp'].readAsAddress()
        context.getAdditionalData()["task_taskptr"] = inf_members["task"].readAsAddress()
        context.getAdditionalData()["task_stkbase"] = inf_members["stk"].readAsAddress()
        context.getAdditionalData()["task_stksize"] = inf_members["stksz"].readAsNumber()

        return context

    def createKernelContext(self, debugger):
        return ExecutionContext(0, "kernel", "RUNNING")

    
    def getNonGlobalRegisterNames(self):
        result = set()
        result.update(REG_MAP_BASE.keys())
        result.update(REG_MAP_NO_VFP.keys())
        result.update(REG_MAP_VFP_ON.keys())
        # These aren't in the reg-maps but aren't global
        result.update({"SP_PROCESS", "R12", "LR"})
        result.update({"S%d" % x for x in xrange(0, 16)})
        result.update({"D%d" % x for x in xrange(0, 8)})
        return result
