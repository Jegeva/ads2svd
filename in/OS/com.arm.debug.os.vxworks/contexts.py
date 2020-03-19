# Copyright (C) 2015,2017 Arm Limited (or its affiliates). All rights reserved.

"""
Implementation of OS support for Wind River VxWorks RTOS
"""
from itertools import *
from osapi import *
from utils import *
import re

class ContextsProvider( ExecutionContextsProvider ):

    def __init__(self):
        self.is_v8a = None

    def isV8A(self, debugger):
        if self.is_v8a is None:
            arch = debugger.getTargetInformation().getArchitecture().getName()
            self.is_v8a = re.match('ARMv8.*A', arch) != None
        return self.is_v8a

    def isAArch64(self, debugger):
        return debugger.evaluateExpression("sizeof $PC").readAsNumber() == 8

    # Get context of current executing task
    def getCurrentOSContext( self, debugSession ) :
        # UP kernels define 'taskIdCurrent' as a pointer to the current task.
        # SMP kernels define 'vxKernelVars' as having the array of per-cpu state (including task).
        if debugSession.symbolExists("vxKernelVars"):
            # SMP
            coreId = getCoreId(debugSession, self.isV8A(debugSession))
            cpuInfo = debugSession.evaluateExpression("vxKernelVars").getArrayElement(coreId)
            cpuVar = cpuInfo.getStructureMembers()["vars"]
            currentTCBPtr = cpuVar.getStructureMembers()["cpu_taskIdCurrent"]
            if currentTCBPtr.readAsNumber():
                return self.createContextFromTaskControlBlock(debugSession, currentTCBPtr)
        elif debugSession.symbolExists("taskIdCurrent"):
            # UP
            # Get pointer to TCB of currently executing task.
            currentTCBPtr = debugSession.evaluateExpression("taskIdCurrent")
            if currentTCBPtr.readAsNumber():
                return self.createContextFromTaskControlBlock(debugSession, currentTCBPtr)
        return None

    # Get context of all tasks
    def getAllOSContexts( self, debugSession ):

        # List is empty
        contexts = [ ]

        # Get list of all task id's
        tcbPtrList = readTaskList( debugSession )

        # Create contect for each task
        for tcbPtr in tcbPtrList:
            contexts.append( self.createContextFromTaskControlBlock( debugSession, tcbPtr ) )

        # All task contexts
        return contexts

    # Get saved resgiters for a given task
    def getOSContextSavedRegister( self, debugger, context, name ):
        gp_regs = context.getAdditionalData()["gp_regs"]
        fp_regs = context.getAdditionalData()["fp_regs"]

        if self.isV8A(debugger):
            return self.extractV8Regs(debugger, name, gp_regs, fp_regs)
        else:
            return self.extractV7Regs(debugger, name, gp_regs, fp_regs)

    def extractV7Regs(self, debugger, name, gp_regs, fp_regs):
        reg_id = int(name[1:]) if name[1:].isdigit() else None

        if gp_regs:
            # The GP regs are banked in a single array.
            if name[0] == 'R' and reg_id is not None:
                return gp_regs['r'].getArrayElement(reg_id)
            # Other/aliased core regs.
            if name == 'SP':
                return gp_regs['r'].getArrayElement(13)
            if name == 'LR':
                return gp_regs['r'].getArrayElement(14)
            if name == 'PC':
                # PC is stored as a pointer. Pointers are automatically dereferenced by the OS
                # extension. To prevent it doing this cast to an integral type.
                return debugger.evaluateExpression('(int) %d' % (gp_regs['pc'].readAsNumber()))

            # Handle the CPSR.
            if name == 'CPSR':
                return gp_regs['cpsr']

            # Handle other miscellaneous banked special purpose registers.
            if name == 'TPIDRURO':
                return gp_regs['tlsbase']
            if name == 'TTBR0':
                return gp_regs['ttbase']

        if fp_regs:
            # Handle the description registers.
            if name == 'FPSID':
                return fp_regs['fpsid']
            if name == 'FPEXC':
                return fp_regs['fpexc']
            # Bit 30 is the enable bit.
            fpu_enabled = (fp_regs['fpexc'].readAsNumber() & 0x40000000) != 0
            # If the FPU is enabled, handle the other banked FPU regs.
            if fpu_enabled:
                # Handle the status/control registers.
                if name == 'FPSCR':
                    return fp_regs['fpscr']
                if name == 'FPINST':
                    return fp_regs['fpinst']
                if name == 'FPINST2':
                    return fp_regs['fpinst2']
                if reg_id is not None:
                    # The 32-bit FP regs are banked in a single array.
                    if name[0] == 'S':
                        return fp_regs['vfp_gpr'].getArrayElement(reg_id)
                    # We can infer the first 16 64-bit FP regs from the 32-bit ones.
                    if name[0] == 'D' and reg_id < 16:
                        regs_base = fp_regs['vfp_gpr'].getLocationAddress()
                        d_addr = regs_base.addOffset(reg_id * 8)
                        return debugger.evaluateExpression('*((unsigned long long*) %s)' % (d_addr.toString()))

        # Otherwise the register is unbanked
        return None

    def extractV8Regs(self, debugger, name, gp_regs, fp_regs):
        reg_id = int(name[1:]) if name[1:].isdigit() else None

        if gp_regs:
            # Handle the core registers.
            # For X regs return the full 64 bit number. For W/R regs cast (truncate) to 32 bits.
            if name[0] == 'X' and reg_id is not None:
                return gp_regs['r'].getArrayElement(reg_id)
            if (name[0] == 'W' or name[0] == 'R') and reg_id is not None:
                val = gp_regs['r'].getArrayElement(reg_id).readAsNumber()
                return debugger.evaluateExpression('(int) %d' % (val))
            # Other core regs. Interestingly we cannot differentiate 32-bit from 64-bit accesses, here
            # so we don't get the opportunity to mask it. Assume the engine is robust to this...
            if name == 'SP':
                return gp_regs['sp']
            if name == 'LR':
                return gp_regs['r'].getArrayElement(30)   # LR is banked as GPR[30]
            if name == 'PC':
                # PC is stored as a pointer. Pointers are automatically dereferenced by the OS
                # extension. To prevent it doing this cast to an integral type.
                return debugger.evaluateExpression('(long) %d' % (gp_regs['pc'].readAsNumber()))

            # Handle the PSTATE.
            # The banked pstate is a pseudo register following the same structure as the AArch32 CPSR.
            # Thus AArch32::Core::CPSR is easy
            if name == 'CPSR':
                return debugger.evaluateExpression('(int) %d' % (gp_regs['pstate'].readAsNumber()))
            # For the AArch64 PSTATE the mapping is slightly more difficult and as follows:
            # AArch32::Core::CPSR.NZCV (31-28)     => AArch64::System::PSTATE::NZCV (31-28)
            # AArch32::Core::CPSR.Q (27)           => N/A
            # AArch32::Core::CPSR.J (24)           => N/A
            # AArch32::Core::CPSR.PAN (22)         => AArch64::System::PSTATE:PAN (22) (v8.1+ only)
            # AArch32::Core::CPSR.SS (21)          =>
            # AArch32::Core::CPSR.IL (20)          =>
            # AArch32::Core::CPSR.GE (19-16)       => N/A
            # AArch32::Core::CPSR.IT (26-25,15-10) => N/A
            # AArch32::Core::CPSR.EAIF (9-6)       => AArch64::System::PSTATE::DAIF (9-6)
            # AArch32::Core::CPSR.T (5)            => N/A
            # AArch32::Core::CPSR.M (4-0)          => AArch64::System::PSTATE::Mode (4-0)
            #                     M (3-2)          => AArch64::System::PSTATE::CurrentEL (3-2)
            #                     M (0)            => AArch64::System::PSTATE::SPSel (0)
            if name == 'NZCV':
                return debugger.evaluateExpression('(int) (%d & 0xF0000000)' % (gp_regs['pstate'].readAsNumber()))
            if name == 'DAIF':
                return debugger.evaluateExpression('(int) (%d & 0x3C0)'      % (gp_regs['pstate'].readAsNumber()))
            if name == 'Mode':
                return debugger.evaluateExpression('(int) (%d & 0x1F)'       % (gp_regs['pstate'].readAsNumber()))
            if name == 'CurrentEL':
                return debugger.evaluateExpression('(int) (%d & 0xC)'        % (gp_regs['pstate'].readAsNumber()))
            if name == 'SPSel':
                return debugger.evaluateExpression('(int) (%d & 0x1)'        % (gp_regs['pstate'].readAsNumber()))
            if name == 'PAN':
                return debugger.evaluateExpression('(int) (%d & 0x400000)'   % (gp_regs['pstate'].readAsNumber()))

            # Handle other miscellaneous banked special purpose registers.
            if name == 'TPIDRRO_EL0':
                return gp_regs['tlsbase']
            if name == 'TTBR0_EL1':
                # ttbase is a pointer type so must be cast to an integral.
                return debugger.evaluateExpression('(long) %d' % (gp_regs['ttbase'].readAsNumber()))

        if fp_regs:
            # Handle the status/control registers.
            # Unlike the CPSR pseudo register, FPSR and FPCR are banked separately. Thus, this time
            # it's the AArch64 side which is easy.
            if name == 'FPSR':
                return debugger.evaluateExpression('(int) %d' % (fp_regs['fpsr'].readAsNumber()))
            if name == 'FPCR':
                return debugger.evaluateExpression('(int) %d' % (fp_regs['fpcr'].readAsNumber()))
            # For AArch32 FPSCR, combine the two (no bitfields overlap and all overlap is RES0, so
            # a simple | is safe).
            if name == 'FPSCR':
                return debugger.evaluateExpression('(int) (%d | %d)' % (fp_regs['fpsr'].readAsNumber(),
                                                                        fp_regs['fpcr'].readAsNumber()))

            # The VFP regs are banked in one giant array of 32 128-bit fields.
            if reg_id is not None:
                if name[0] == 'H':
                    s_val =fp_regs['vfp_gpr'].getArrayElement(reg_id).getStructureMembers()['u32'].getArrayElement(0)
                    return debugger.evaluateExpression('(short) %d' % (s_val.readAsNumber()))
                if name[0] == 'S':
                    return fp_regs['vfp_gpr'].getArrayElement(reg_id).getStructureMembers()['u32'].getArrayElement(0)
                if name[0] == 'D':
                    return fp_regs['vfp_gpr'].getArrayElement(reg_id).getStructureMembers()['u64'].getArrayElement(0)
                if name[0] == 'Q' or name[0] == 'V':
                    q_loc = fp_regs['vfp_gpr'].getArrayElement(reg_id).getLocationAddress()
                    return debugger.evaluateExpression('*((__int128*) %s)' % (q_loc.toString()))

        # Otherwise the register is unbanked
        return None


    # Create context from task control block
    def createContextFromTaskControlBlock( self, debugger, tcbPtr ):

        # Get structure members of TCB.
        tcbMembers = tcbPtr.dereferencePointer().getStructureMembers()

        # Get task id number (use address of TCB). Present it as 32/64-bit hex rather than decimal.
        taskId = tcbPtr.readAsNumber()
        taskIdStr = "ID %s" % (longToHex(taskId, 64 if self.isV8A(debugger) else 32))

        # Extract task name and state.
        taskName = getClassName(tcbMembers['objCore'])
        taskState = getTaskState(tcbMembers)

        # Create task context.
        context = ExecutionContext(taskId, taskName, taskState, prettyId=taskIdStr)

        # Locate the banked register array and save it to the context.
        context.getAdditionalData()["gp_regs"] = tcbMembers["regs"].getStructureMembers()
        context.getAdditionalData()["fp_regs"] = self.getFPRegs(tcbMembers["pCoprocTbl"])

        # Complete task context
        return context

    def getFPRegs(self, pCoprocTbl):
        if not pCoprocTbl.readAsNumber():
            return None

        coprocTbl = pCoprocTbl.dereferencePointer().getStructureMembers()

        if not coprocTbl['pCtx'].readAsNumber():
            return None

        ctxStruct = coprocTbl['pCtx'].dereferencePointer('VFP_CONTEXT*').getStructureMembers()
        return ctxStruct
    
    def getNonGlobalRegisterNames(self):
        result = set(chain(
                # V7 Non-FP registers
                ["R%d" % n for n in xrange(0,13)],
                ["SP", "LR", "PC", "CPSR", "TPIDRURO", "TTBR0"],
                # V7 FP Registers
                ["FPSID", "FPEXC", "FPSCR", "FPINST", "FPINST2"],
                ["S%d" % n for n in xrange(0,32)],
                ["D%d" % n for n in xrange(0,16)],

                # V8 Non-Core Registers
                ["X%d" % n for n in xrange(0,31)],
                ["W%d" % n for n in xrange(0,31)],
                ["SP", "LR", "PC", "CPSR","NZCV", "DAIF", "Mode", "CurrentEL", "SPSel", "PAN", "TPIDRRO_EL0", "TTBR0_EL1"],
                # V8 VFP Registesr
                ["FPSR", "FPCR", "FPSCR"],
                ["H%d" % n for n in xrange(0,32)],
                ["S%d" % n for n in xrange(0,32)],
                ["D%d" % n for n in xrange(0,32)],
                ["Q%d" % n for n in xrange(0,32)],
                ["V%d" % n for n in xrange(0,32)],
            ))
        return result
