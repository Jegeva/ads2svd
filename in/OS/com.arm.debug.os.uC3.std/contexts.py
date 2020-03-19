# Copyright (C) 2015,2017 Arm Limited (or its affiliates). All rights reserved.

from itertools import *
from kernel import *
from osapi import *
from utils import *

# The part of the register map that doesn't change
# R4-R11, ...
REG_MAP_BASE = {
    "R0"  : None,
    "R1"  : None,
    "R2"  : None,
    "R3"  : None,
    "R4"  :   0L,
    "R5"  :   4L,
    "R6"  :   8L,
    "R7"  :  12L,
    "R8"  :  16L,
    "R9"  :  20L,
    "R10" :  24L,
    "R11" :  28L,
    "R12" : None,
}

# Compiled without VFP support
# R4-R11, CPSR, LR
REG_MAP_NO_VFP = {
    "CPSR":  32L, "XPSR":  32L,
    #"LR"  :  36L,
    "PC"  :  36L,
    "SP"  :  40L,    # Offset past the entire banked stack
}

# Compiled with half/full VFP support but in a non-VFP function
# R4-R11, FPEXC, CPSR, CPSR, LR
REG_MAP_VFP_OFF = {
    "FPEXC": 32L,
    "CPSR":  40L, "XPSR":  40L,
    #"LR"  :  44L,
    "PC"  :  44L,
    "SP"  :  48L,   # Offset past the entire banked stack
}

# Compiled with half VFP support in a VFP function
# R4-R11, FPEXC, FPSCR, D8-D15, CPSR, LR
REG_MAP_VFP_HALF = dict(chain(
    make_reg_list(32, 4, "FPEXC", "FPSCR"),
    make_reg_range(40, 8, "D", 8, 8),
    make_reg_range(40, 4, "S", 16, 16),
    # SP is offset past the entire banked stack
    make_reg_list(104, 4, "CPSR", "PC", "SP"),
    ))

# Compiled with full VFP support in a VFP function
# R4-R11, FPEXC, FPSCR, D8-D15, D16-D31, CPSR, LR
REG_MAP_VFP_FULL = dict(chain(
    make_reg_list(32, 4, "FPEXC", "FPSCR"),
    make_reg_range(40, 8, "D", 8, 24),
    make_reg_range(40, 4, "S", 16, 16),
    # SP is offset past the entire banked stack
    make_reg_list(232, 4, "CPSR", "PC", "SP"),
    ))

class ContextsProvider(ExecutionContextsProvider):

    def getCurrentOSContext(self, debugger):
        """
        Member 'ctcb' of the kernel data structure contains a pointer to the current task
        """
        systbl = debugger.evaluateExpression("_kernel_systbl").getStructureMembers()
        current_task = systbl["ctcb"]
        if(current_task.readAsNumber() > 0):
            return self.createContext(systbl, current_task)
        else:
            return self.createKernelContext(debugger)

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
        qtcb = systbl["qtcb"].getStructureMembers()
        info = qtcb["inf"].dereferencePointer().getStructureMembers()
        limit = info["limit"].readAsNumber()
        usedc = info["usedc"].readAsNumber()
        tasks = qtcb["tcb"].getArrayElements(limit+1)

        for index in range(1, limit+1):
            task = tasks[index]
            if task.readAsNumber() != 0:
                contexts.append(self.createContext(systbl, task))

        return contexts

    # Returns a dictionary with the non-base component register map,
    # based on the VFP state
    def extractRegMap(self, debugger, sp):
        # The task can be in a number of states:
        # 0. Indeterminate
        # 1. Compiled without VFP Support
        # 2. Compiled with half VFP support in a non-VFP function
        # 3. Compiled with full VFP support in a non-VFP function
        # 4. Compiled with half VFP support in a VFP function
        # 5. Compiled with full VFP support in a VFP function
        # The first 8 words (R4-R11) do not change. The first variable word is
        # at offset 32.
        vfp_flag = debugger.getConnectionSetting('os vfp-flag')

        # Detect case 1
        # Offset 32,36 is either FPEXC | FPSCR/CPSR if compiled with VFP
        #                     or CPSR  | LR         otherwise
        # We can't easily detect this, since FPEXC is mostly SubArch defined
        # and the LR can in theory hold anything (and even if it's an address
        # there's nothing to stop it looking like a CPSR).
        if vfp_flag == 'disabled':
            return REG_MAP_NO_VFP

        # Detect cases 2 + 3
        # Read FPEXC.EN
        fpexc = debugger.evaluateExpression("*((unsigned long*)" + str(sp.addOffset(32L)) + ")").readAsNumber()
        fpexc_en = fpexc & 0x40000000L
        if not fpexc_en:
            return REG_MAP_VFP_OFF

        # Detect case 4
        # We need to detect if D16 onwards are disabled/not implemented.
        if vfp_flag == 'vfpv3_16':
            return REG_MAP_VFP_HALF

        # Detect case 5
        # We need to detect if D16 onwards are enabled.
        if vfp_flag == 'vfpv3_32':
            return REG_MAP_VFP_FULL

        # Case 0
        return {}

    def getOSContextSavedRegister(self, debugger, context, name):
        # There are a number of stages in a task's life cycle:
        #   1. Task is created.
        #          T_TCB is populated, stk is allocated.
        #   2. Task is activated.
        #          Small amount of startup-state pushed to stack. T_TCB->sp is set.
        #   3. Task runs.
        #          T_TCB->pc is set
        #   4. Task may enter idle state (at which point it returns to #2)
        #   5. Task is deleted.
        # NB: sp in this case contains the stack pointer to the banked registers. This is
        # NOT the stack pointer which will be re-instated from a context switch (as the
        # task will have the banked registers removed from its stack once it starts again).
        sp = context.getAdditionalData()["task_sp"]
        pc = context.getAdditionalData()["task_pc"]
        # Saved SP will be 0 if this is the current task (should never happen), or if the
        # task has not been activated. In the latter case we can derive the SP from the stack
        # base and PC from task ptr, but there won't be any banked registers.
        if sp.getLinearAddress() == 0L:
            if name == "SP":
                sp_base = context.getAdditionalData()["task_stkbase"]
                sp_size = context.getAdditionalData()["task_stksize"]
                sp_addr = sp_base.addOffset(sp_size).getLinearAddress()
                return debugger.evaluateExpression("(long)" + str(sp_addr))
            elif name == "PC":
                pc_addr = context.getAdditionalData()["task_taskptr"].getLinearAddress()
                return debugger.evaluateExpression("(long)" + str(pc_addr))
            else:
                return None
        elif pc.getLinearAddress() == 0L:
            # We know the saved SP is non-zero, so there is some data stored on the stack,
            # however if the saved PC is zero the task has never been run, so we don't
            # have any banked state stored on the stack.
            if name == "SP":
                sp_addr = sp.getLinearAddress()
                return debugger.evaluateExpression("(long)"  + str(sp_addr))
            elif name == "PC":
                pc_addr = context.getAdditionalData()["task_taskptr"].getLinearAddress()
                return debugger.evaluateExpression("(long)" + str(pc_addr))
            else:
                return None
        else:
            # Otherwise we're looking at the stack for banked registers.
            # Check if the stack is big enough to contain banked registers (we have
            # at least 10 words in banked registers, whereas only 4 or 6 are pushed
            # on at task creation.
            # Registers wouldn't be banked if the task has never been run.
            stk_base = context.getAdditionalData()["task_stkbase"]
            stk_size = context.getAdditionalData()["task_stksize"]
            if sp.getLinearAddress() > stk_base.addOffset(stk_size - 40L).getLinearAddress():
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

    def createContext(self, systbl, task):
        task = task.dereferencePointer()
        members = task.getStructureMembers()
        id = members["tskid"].readAsNumber()
        name = readPotentiallyNullString(members["name"])
        stateCode, stateStr = getTaskState(systbl, task.readAsNumber(), members['stat'].getStructureMembers())

        # Create context
        context = ExecutionContext(id, name, stateStr)

        # Store additional information in the execution context
        context.getAdditionalData()["task_pc"]      = members["pc"].readAsAddress()
        context.getAdditionalData()["task_sp"]      = members["sp"].readAsAddress()
        context.getAdditionalData()["task_taskptr"] = members["task"].readAsAddress()
        context.getAdditionalData()["task_stkbase"] = members["stk"].readAsAddress()
        context.getAdditionalData()["task_stksize"] = members["stksz"].readAsNumber()

        return context

    def createKernelContext(self, debugger):
        return ExecutionContext(0, "kernel", "RUNNING")

    def getNonGlobalRegisterNames(self):
        result = set()
        result.update(REG_MAP_BASE.keys())
        result.update(REG_MAP_NO_VFP.keys())
        result.update(REG_MAP_VFP_OFF.keys())
        result.update(REG_MAP_VFP_HALF.keys())
        result.update(REG_MAP_VFP_FULL.keys())
        # These aren't in the register maps
        result.update("D%d" % x for x in xrange(0,8))
        result.update("S%d" % x for x in xrange(0,16))
        return result
