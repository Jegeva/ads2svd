# Copyright (C) 2017 Arm Limited (or its affiliates). All rights reserved.

from itertools import *
from osapi import *
import kernel
import re

class ContextsProvider(ExecutionContextsProvider):

    def __init__(self):
        self.p4k_thrinfo_t = None
        self.is_v8a = None
        self.is_pikeos42 = None

    def get_p4k_thrinfo_t(self, debugger):
        if self.p4k_thrinfo_t is None:
            self.p4k_thrinfo_t = debugger.resolveType('P4k_thrinfo_t')
        return self.p4k_thrinfo_t

    def isV8A(self, debugger):
        if self.is_v8a is None:
            arch = debugger.getTargetInformation().getArchitecture().getName()
            self.is_v8a = re.match('ARMv8.*A', arch) != None
        return self.is_v8a

    def isPikeOS42(self, debugger):
        if self.is_pikeos42 is None:
            kinfo = debugger.evaluateExpression('"kinfo.c"::kinfo_ptr').dereferencePointer().getStructureMembers()
            buildid = kinfo['kernel_id'].readAsNullTerminatedString()
            self.is_pikeos42 = '4.2' in buildid
        return self.is_pikeos42

    def cleanupState(self):
        self.p4k_thrinfo_t = None
        self.is_v8a = None

    def getCurrentOSContext(self, debugger):
        # The location of the pointer to this CPU's current thread info block is arch specific.
        cur_thread_ptr = None
        if self.isV8A(debugger):
            # On v8 it's kept in TPIDR_EL1.
            cur_thread_ptr = debugger.evaluateExpression('$TPIDR_EL1')
            if cur_thread_ptr.readAsNumber() == 0:
                return None
        else:
            # On v7 it's kept in TPIDRPRW.
            cur_thread_ptr = debugger.evaluateExpression('$TPIDRPRW')
            if cur_thread_ptr.readAsNumber() == 0:
                return None

        # Retrieve the stashed P4k_thrinfo_t type.
        p4k_thrinfo_t = self.get_p4k_thrinfo_t(debugger)
        if not p4k_thrinfo_t:
            return None

        # Cast the retrieved (non-zero) address of the thread info block to a P4k_thrinfo_t*.
        cur_threadinfo = debugger.constructPointer(p4k_thrinfo_t, cur_thread_ptr.readAsAddress())

        return self.createContext(debugger, cur_threadinfo.dereferencePointer(), True, False)

    def getAllOSContexts(self, debugger):
        # Starting at the kernel task (id 0) which is the parent of all other tasks, extract all
        # other tasks and their threads.
        tasks = [kernel.getTask(debugger, 0)]
        threads = []
        ptr = 0
        while ptr < len(tasks):
            target = tasks[ptr]
            tasks += kernel.getChildTasks(debugger, target)
            threads += kernel.getChildThreads(debugger, target)
            ptr += 1
        # Create contexts
        contexts = []
        for thread in threads:
            contexts.append(self.createContext(debugger, thread, False, False))
        return contexts

    def getOSContextHierarchy(self, debugger):
        return [self.createContextGroup(debugger, kernel.getTask(debugger, 0))]

    def createContextGroup(self, debugger, task_struct):
        # Extract data from this task
        task = task_struct.getStructureMembers()
        taskname = task['name'].readAsNullTerminatedString()
        taskno = task['taskno'].readAsNumber()
        respart = task['respart'].dereferencePointer().getStructureMembers()['id'].readAsNumber()
        taskid = "Partition %d, Task %d" % (respart, taskno)
        # Extract children
        child_tasks = kernel.getChildTasks(debugger, task_struct)
        child_threads = kernel.getChildThreads(debugger, task_struct)
        # Create elements for children
        child_task_contexts = []
        for child_task in child_tasks:
            child_task_contexts.append(self.createContextGroup(debugger, child_task))
        child_thread_contexts = []
        for child_thread in child_threads:
            child_thread_contexts.append(self.createContext(debugger, child_thread, False, True))
        # Create element for this context
        return ExecutionContextGroup(taskname, taskid, None, child_task_contexts, child_thread_contexts)

    def createContext(self, debugger, thread_struct, current, hierarchical_id):
        """Creates an ExecutionContext from the given thread.

        Parameters:
            thread_struct: IExpressionResult of the thread structure (P4k_thrinfo_t).
            current:       boolean whether or not the context should be current.
            hierarchical_id:  Whether the generated ID should be based on a hierarchical
                (true) or flat (false) ID structure.
        Returns:
            ExecutionContext representation of the thread.
        """
        thread = thread_struct.getStructureMembers()
        # Build an ID string
        uid = thread['uid'].readAsNumber()
        threadno, taskno, respart, timepart = kernel.decodeUID(uid)
        if hierarchical_id:
            prettyId = "Thread %d" % (threadno)
        else:
            prettyId = "Partition %d, Task %d, Thread %d" % (respart, taskno, threadno)
        # Extract the other parts
        name = thread['name'].readAsNullTerminatedString()
        stateStr = kernel.getThreadState(thread['state'].readAsNumber(), current, self.isPikeOS42(debugger))
        # Build the context
        context = ExecutionContext(uid, name, stateStr, prettyId)

        # Store additional information in the execution context
        thread_addr = thread_struct.getLocationAddress()
        context.getAdditionalData()["thread_ptr"] = thread_addr
        context.getAdditionalData()["task_ptr"]   = thread['task'].readAsAddress()

        # Mark the thread object itself as cacheable
        debugger.markRegionCacheable(thread_addr, self.get_p4k_thrinfo_t(debugger).getSizeInBytes())

        # Mark the register bank's memory as cacheable
        regBankPtr = self.getRegBankPtr(debugger, thread_addr)
        regBankType = regBankPtr.getType().getPointedAtType()
        debugger.markRegionCacheable(regBankPtr.readAsAddress(), regBankType.getSizeInBytes())

        return context

    def getRegBankPtr(self, debugger, thread_addr):
        p4k_thrinfo_t = self.get_p4k_thrinfo_t(debugger)
        thread_ptr = debugger.constructPointer(p4k_thrinfo_t, thread_addr)
        thread = thread_ptr.dereferencePointer().getStructureMembers()
        context = thread['context']
        regBankPtr = context.getStructureMembers()['uregs']
        return regBankPtr

    def getOSContextSavedRegister(self, debugger, context, name):
        # Retrieve the context's additional info
        thread_addr = context.getAdditionalData()["thread_ptr"] # IAddress

        # All context information is saved together in the thread object
        reg_bank_ptr = self.getRegBankPtr(debugger, thread_addr)
        reg_bank = reg_bank_ptr.dereferencePointer().getStructureMembers()

        # NB: It is vitally important when returning registers that they are the correct length
        # (especially if they contain bitfields).
        if self.isV8A(debugger):
            return self.extractV8Regs(debugger, name, reg_bank)
        else:
            return self.extractV7Regs(debugger, name, reg_bank)

    def extractV7Regs(self, debugger, name, reg_bank):
        # The GP regs are banked in a single array.
        if name[0] == 'R' and name[1:].isdigit():
            return reg_bank['regs'].getArrayElement(int(name[1:]))
        # Aliased GP regs.
        if name == 'SP':
            return reg_bank['regs'].getArrayElement(13)
        if name == 'LR':
            return reg_bank['regs'].getArrayElement(14)
        if name == 'PC':
            return reg_bank['regs'].getArrayElement(15)

        # Handle the CPSR.
        if name == 'CPSR':
            return reg_bank['cpsr']

        # Handle the FP enable register
        if name == 'FPEXC':
            return reg_bank['fpexc']
        # Bit 30 is the enable bit.
        fpu_enabled = (reg_bank['fpexc'].readAsNumber() & 0x40000000) != 0
        # If the FPU is enabled, handle the other banked FPU regs.
        if fpu_enabled:
            # The FP regs are banked in a single array.
            if name[0] == 'D' and name[1:].isdigit():
                return reg_bank['fpregs'].getArrayElement(int(name[1:]))
            # Handle the FP state & control registers.
            if name == 'FPSCR':
                return reg_bank['fpscr']
            # Interestingly the PikeOS v7 kernel banks some v6 VFP registers. As these will not be
            # requested unless a user has an RVC or similar set up with them named we are safe to
            # read when requested (deferring to the users' control).
            if name == 'FPINST':
                return reg_bank['fpinst']
            if name == 'FPINST2':
                return reg_bank['fpinst2']

        # Handle other miscellaneous banked special purpose registers.
        if name == 'TPIDRURO':
            return reg_bank['tls']

        # Otherwise the register is unbanked
        return None

    def extractV8Regs(self, debugger, name, reg_bank):
        # The GP regs are banked in a single array.
        # For X regs return the full 64 bit number. For W/R regs cast (truncate) to 32 bits.
        if name[0] == 'X' and name[1:].isdigit():
            return reg_bank['regs'].getArrayElement(int(name[1:]))
        if (name[0] == 'W' or name[0] == 'R') and name[1:].isdigit():
            val = reg_bank['regs'].getArrayElement(int(name[1:])).readAsNumber()
            return debugger.evaluateExpression('(int) %d' % (val))

        # The FP regs are also banked in a single array
        fpu_enabled = reg_bank['usedfpu'].readAsNumber() > 0
        if fpu_enabled:
            # AArch32 and AArch64 FPRegs have the same names (AArch64 just has more, and the H regs)
            # so this will handle both modes.
            # For Q/V regs, return the full 128 bit number. For everything else, mask appropriately.
            if (name[0] == 'Q' or name[0] == 'V') and name[1:].isdigit():
                return reg_bank['fpregs'].getArrayElement(int(name[1:]))
            if name[0] == 'D' and name[1:].isdigit():
                val = reg_bank['fpregs'].getArrayElement(int(name[1:])).readAsNumber()
                return debugger.evaluateExpression('(long long) %d' % (val))
            if name[0] == 'S' and name[1:].isdigit():
                val = reg_bank['fpregs'].getArrayElement(int(name[1:])).readAsNumber()
                return debugger.evaluateExpression('(int) %d' % (val))
            if name[0] == 'H' and name[1:].isdigit():
                val = reg_bank['fpregs'].getArrayElement(int(name[1:])).readAsNumber()
                return debugger.evaluateExpression('(short) %d' % (val))

        # Other core regs. Interestingly we cannot differentiate 32-bit from 64-bit accesses, here
        # so we don't get the opportunity to mask it. Assume the engine is robust to this...
        if name == 'LR':
            # LR is banked as GPR[30]
            return reg_bank['regs'].getArrayElement(30)
        if name == 'PC':
            return reg_bank['pc']
        if name == 'SP':
            return reg_bank['sp']

        # Handle the PSTATE
        # The banked CPSR is a pseudo register following the same structure as the AArch32 CPSR.
        # Thus AArch32::Core::CPSR is easy
        if name == 'CPSR':
            return debugger.evaluateExpression('(int) %d' % (reg_bank['cpsr'].readAsNumber()))
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
            return debugger.evaluateExpression('(int) (%d & 0xF0000000)' % (reg_bank['cpsr'].readAsNumber()))
        if name == 'DAIF':
            return debugger.evaluateExpression('(int) (%d & 0x3C0)'      % (reg_bank['cpsr'].readAsNumber()))
        if name == 'Mode':
            return debugger.evaluateExpression('(int) (%d & 0x1F)'       % (reg_bank['cpsr'].readAsNumber()))
        if name == 'CurrentEL':
            return debugger.evaluateExpression('(int) (%d & 0xC)'        % (reg_bank['cpsr'].readAsNumber()))
        if name == 'SPSel':
            return debugger.evaluateExpression('(int) (%d & 0x1)'        % (reg_bank['cpsr'].readAsNumber()))
        if name == 'PAN':
            return debugger.evaluateExpression('(int) (%d & 0x400000)'   % (reg_bank['cpsr'].readAsNumber()))

        # Handle the FP state & control
        if fpu_enabled:
            # Unlike the CPSR pseudo register, FPSR and FPCR are banked separately. Thus, this time it's
            # the AArch64 side which is easy (AArch64::System::Float::FPSR, AArch64::System::Float::FPCR)
            if name == 'FPSR':
                return debugger.evaluateExpression('(int) %d' % (reg_bank['fpsr'].readAsNumber()))
            if name == 'FPCR':
                return debugger.evaluateExpression('(int) %d' % (reg_bank['fpcr'].readAsNumber()))
            # For AArch32::System::Float::FPSCR, combine the two (no bitfields overlap and all overlap
            # should be RES0, so a simple | is safe).
            if name == 'FPSCR':
                return debugger.evaluateExpression('(int) (%d | %d)' % (reg_bank['fpsr'].readAsNumber(),
                                                                        reg_bank['fpcr'].readAsNumber()))

        # Handle other miscellaneous banked special purpose registers
        if name == 'TPIDR_EL0':
            return reg_bank['tpidr']
        if name == 'TPIDRRO_EL0':
            return reg_bank['tpidrro']

        # Otherwise the register is unbanked
        return None

    def getNonGlobalRegisterNames(self):
        result = set(chain(
                # V7 Non-FP registers
                ["R%d" % n for n in xrange(0,13)],
                ["SP", "LR", "PC", "CPSR", "TPIDURO"],
                # V7 FP Registers
                ["FPEXC", "FPSCR", "FPINST", "FPINST2"],
                ["S%d" % n for n in xrange(0,32)],
                ["D%d" % n for n in xrange(0,16)],

                # V8 Non-Core Registers
                ["X%d" % n for n in xrange(0,31)],
                ["W%d" % n for n in xrange(0,31)],
                ["SP", "LR", "PC", "CPSR", "NZCV", "DAIF", "Mode", "CurrentEL", "SPSel", "PAN", "TPIDR_EL0", "TPIDRR0_EL0"],
                # V8 VFP Registesr
                ["FPSR", "FPCR", "FPSCR"],
                ["H%d" % n for n in xrange(0,32)],
                ["S%d" % n for n in xrange(0,32)],
                ["D%d" % n for n in xrange(0,32)],
                ["Q%d" % n for n in xrange(0,32)],
                ["V%d" % n for n in xrange(0,32)],
            ))
        return result

