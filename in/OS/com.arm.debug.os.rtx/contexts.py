# Copyright (C) 2013-2015,2017,2018 Arm Limited (or its affiliates). All rights reserved.

from osapi import *
from utils import getTaskId
from utils import getDisplayableTaskId
from utils import getTaskState
from utils import getActiveTasks
from utils import getCurrentTask
from utils import dereferenceThreadPointer
from utils import getMember
from utils import getSimpleName
from utils import isNullPtr
from utils import nonNullPtr

BASIC_REGISTERS_MAP = {"R4" : 0L,
                       "R5" : 4L,
                       "R6" : 8L,
                       "R7" : 12L,
                       "R8" : 16L,
                       "R9" : 20L,
                       "R10" : 24L,
                       "R11" : 28L,
                       "R0" : 32L,
                       "R1" : 36L,
                       "R2" : 40L,
                       "R3" : 44L,
                       "R12" : 48L,
                       "LR" : 52L,
                       "PC" : 56L,
                       "CPSR" : 60L,
                       "XPSR" : 60L,
                       "SP" : 64L}



EXTENDED_REGISTERS_MAP = {"R4": 0L,
                          "R5": 4L,
                          "R6": 8L,
                          "R7": 12L,
                          "R8": 16L,
                          "R9": 20L,
                          "R10": 24L,
                          "R11": 28L,
                          "S16": 32L,
                          "S17": 36L,
                          "S18": 40L,
                          "S19": 44L,
                          "S20": 48L,
                          "S21": 52L,
                          "S22": 56L,
                          "S23": 60L,
                          "S24": 64L,
                          "S25": 68L,
                          "S26": 72L,
                          "S27": 76L,
                          "S28": 80L,
                          "S29": 84L,
                          "S30": 88L,
                          "S31": 92L,
                          "R0": 96L,
                          "R1": 100L,
                          "R2": 104L,
                          "R3": 108L,
                          "R12": 112L,
                          "LR": 116L,
                          "PC": 120L,
                          "CPSR": 124L,
                          "XPSR": 124L,
                          "S0": 128L,
                          "S1": 132L,
                          "S2": 136L,
                          "S3": 140L,
                          "S4": 144L,
                          "S5": 148L,
                          "S6": 152L,
                          "S7": 156L,
                          "S8": 160L,
                          "S9": 164L,
                          "S10": 168L,
                          "S11": 172L,
                          "S12": 176L,
                          "S13": 180L,
                          "S14": 184L,
                          "S15": 188L,
                          "FPSCR": 192L,
                          # No register @196
                          "SP": 200L,
                          "D0": 128L,
                          "D1": 136L,
                          "D2": 144L,
                          "D3": 152L,
                          "D4": 160L,
                          "D5": 168L,
                          "D6": 176L,
                          "D7": 184L,
                          "D8": 32L,
                          "D9": 40L,
                          "D10": 48L,
                          "D11": 56L,
                          "D12": 64L,
                          "D13": 72L,
                          "D14": 80L,
                          "D15": 88L}


V8M_BASIC_REGISTERS_MAP = {"R4" : 0L,
                       "R5" : 4L,
                       "R6" : 8L,
                       "R7" : 12L,
                       "R8" : 16L,
                       "R9" : 20L,
                       "R10" : 24L,
                       "R11" : 28L,
                       "R0" : 32L,
                       "R1" : 36L,
                       "R2" : 40L,
                       "R3" : 44L,
                       "R12" : 48L,
                       "LR" : 52L,
                       "PC" : 56L,
                       "XPSR" : 60L}


V8M_EXTENDED_REGISTERS_MAP = {
                          "S16": 0L,
                          "S17": 4L,
                          "S18": 8L,
                          "S19": 12L,
                          "S20": 16L,
                          "S21": 20L,
                          "S22": 24L,
                          "S23": 28L,
                          "S24": 32L,
                          "S25": 36L,
                          "S26": 40L,
                          "S27": 44L,
                          "S28": 48L,
                          "S29": 52L,
                          "S30": 56L,
                          "S31": 60L,
                          "R4" : 64L,
                          "R5" : 68L,
                          "R6" : 72L,
                          "R7" : 76L,
                          "R8" : 80L,
                          "R9" : 84L,
                          "R10" : 88L,
                          "R11" : 92L,
                          "R0": 96L,
                          "R1": 100L,
                          "R2": 104L,
                          "R3": 108L,
                          "R12" : 112L,
                          "LR" : 116L,
                          "PC" : 120L,
                          "XPSR" : 124L,
                          "S0": 128L,
                          "S1": 132L,
                          "S2": 136L,
                          "S3": 140L,
                          "S4": 144L,
                          "S5": 148L,
                          "S6": 152L,
                          "S7": 156L,
                          "S8": 160L,
                          "S9": 164L,
                          "S10": 168L,
                          "S11": 172L,
                          "S12": 176L,
                          "S13": 180L,
                          "S14": 184L,
                          "S15": 188L,
                          "FPSCR": 192L,
                          }


FP_REGISTERS_MAP = {"S0": 0L,
                    "S1": 4L,
                    "S2": 8L,
                    "S3": 12L,
                    "S4": 16L,
                    "S5": 20L,
                    "S6": 24L,
                    "S7": 28L,
                    "S8": 32L,
                    "S9": 36L,
                    "S10": 40L,
                    "S11": 44L,
                    "S12": 48L,
                    "S13": 52L,
                    "S14": 56L,
                    "S15": 60L,
                    "S16": 64L,
                    "S17": 68L,
                    "S18": 72L,
                    "S19": 76L,
                    "S20": 80L,
                    "S21": 84L,
                    "S22": 88L,
                    "S23": 92L,
                    "S24": 96L,
                    "S25": 100L,
                    "S26": 104L,
                    "S27": 108L,
                    "S28": 112L,
                    "S29": 116L,
                    "S30": 120L,
                    "S31": 124L,
                    "FPSCR": 128L,
                    # No register @132
                    "R4": 136L,
                    "R5": 140L,
                    "R6": 144L,
                    "R7": 148L,
                    "R8": 152L,
                    "R9": 156L,
                    "R10": 160L,
                    "R11": 164L,
                    "R0": 168L,
                    "R1": 172L,
                    "R2": 176L,
                    "R3": 180L,
                    "R12": 184L,
                    "LR": 188L,
                    "PC": 192L,
                    "CPSR": 196L,
                    "XPSR": 196L,
                    "SP": 200L,
                    "D0": 0L,
                    "D1": 8L,
                    "D2": 16L,
                    "D3": 24L,
                    "D4": 32L,
                    "D5": 40L,
                    "D6": 48L,
                    "D7": 56L,
                    "D8": 64L,
                    "D9": 72L,
                    "D10": 80L,
                    "D11": 88L,
                    "D12": 96L,
                    "D13": 104L,
                    "D14": 112L,
                    "D15": 120L,
                    "Q0": 0L,
                    "Q1": 16L,
                    "Q2": 32L,
                    "Q3": 48L,
                    "Q4": 64L,
                    "Q5": 80L,
                    "Q6": 96L,
                    "Q7": 112L}

NEON_REGISTERS_MAP = {"S0": 128L,
                      "S1": 132L,
                      "S2": 136L,
                      "S3": 140L,
                      "S4": 144L,
                      "S5": 148L,
                      "S6": 152L,
                      "S7": 156L,
                      "S8": 160L,
                      "S9": 164L,
                      "S10": 168L,
                      "S11": 172L,
                      "S12": 176L,
                      "S13": 180L,
                      "S14": 184L,
                      "S15": 188L,
                      "S16": 192L,
                      "S17": 196L,
                      "S18": 200L,
                      "S19": 204L,
                      "S20": 208L,
                      "S21": 212L,
                      "S22": 216L,
                      "S23": 220L,
                      "S24": 224L,
                      "S25": 228L,
                      "S26": 232L,
                      "S27": 236L,
                      "S28": 240L,
                      "S29": 244L,
                      "S30": 248L,
                      "S31": 252L,
                      "FPSCR": 256L,
                      # No register @260
                      "R4": 264L,
                      "R5": 268L,
                      "R6": 272L,
                      "R7": 276L,
                      "R8": 280L,
                      "R9": 284L,
                      "R10": 288L,
                      "R11": 292L,
                      "R0": 296L,
                      "R1": 300L,
                      "R2": 304L,
                      "R3": 308L,
                      "R12": 312L,
                      "LR": 316L,
                      "PC": 320L,
                      "CPSR": 324L,
                      "XPSR": 328L,
                      "SP": 328L,
                      "D0": 128L,
                      "D1": 136L,
                      "D2": 144L,
                      "D3": 152L,
                      "D4": 160L,
                      "D5": 168L,
                      "D6": 176L,
                      "D7": 184L,
                      "D8": 192L,
                      "D9": 200L,
                      "D10": 208L,
                      "D11": 216L,
                      "D12": 224L,
                      "D13": 232L,
                      "D14": 240L,
                      "D15": 248L,
                      "D16": 0L,
                      "D17": 8L,
                      "D18": 16L,
                      "D19": 24L,
                      "D20": 32L,
                      "D21": 40L,
                      "D22": 48L,
                      "D23": 56L,
                      "D24": 64L,
                      "D25": 72L,
                      "D26": 80L,
                      "D27": 88L,
                      "D28": 96L,
                      "D29": 104L,
                      "D30": 112L,
                      "D31": 120L,
                      "Q0": 128L,
                      "Q1": 144L,
                      "Q2": 160L,
                      "Q3": 176L,
                      "Q4": 192L,
                      "Q5": 208L,
                      "Q6": 224L,
                      "Q7": 240L,
                      "Q8": 0L,
                      "Q9": 16L,
                      "Q10": 32L,
                      "Q11": 48L,
                      "Q12": 64L,
                      "Q13": 80L,
                      "Q14": 96L,
                      "Q15": 112L}

class ContextsProvider(ExecutionContextsProvider):

    def getCurrentOSContext(self, debugger):
        tcbPtr = getCurrentTask(debugger)

        # Synthesises a "NULL" task in this case
        if isNullPtr(tcbPtr):
            return ExecutionContext(-1, "NULL", getTaskState(2))
        else:
            return self.createContextFromTaskControlBlock(debugger, tcbPtr)

    def getAllOSContexts(self, debugger):
        return map(lambda ptr: self.createContextFromTaskControlBlock(debugger, ptr), getActiveTasks(debugger))

    def getOSContextSavedRegister(self, debugger, context, name):
        arch = debugger.getTargetInformation().getArchitecture().getName()
        base = context.getAdditionalData()["tsk_stack"]

        if name == "PSPLIM_S":
            stack_lim = context.getAdditionalData()["tsk_stack_lim"]
            return debugger.evaluateExpression("(long)" + str(stack_lim))
        elif name == "SP" or name == "PSP_S":
            return debugger.evaluateExpression("(long)" + str(base))

        offset = context.getAdditionalData()["register_map"].get(name, None)
        if offset == None:
            return None

        base = base.addOffset(offset)
        return debugger.evaluateExpression("(long*)" + str(base))


    def createContextFromTaskControlBlock(self, debugger, tcbPtr):
        arch = debugger.getTargetInformation().getArchitecture().getName()

        members = dereferenceThreadPointer(tcbPtr).getStructureMembers()

        id      = getTaskId(tcbPtr, members)
        name    = getSimpleName(members,"thread_addr")
        state   = getTaskState(getMember(members,"state").readAsNumber())

        context = ExecutionContext(id, name, state, getDisplayableTaskId(tcbPtr, members))

        stackPointer = getMember(members,"sp").readAsAddress()
        stack_lim    = getMember(members, "stack_mem").readAsAddress()
        stack_frame  = getMember(members, "stack_frame").readAsNumber()

        context.getAdditionalData()["tsk_stack"] = stackPointer
        context.getAdditionalData()["tsk_stack_lim"]   = stack_lim
        context.getAdditionalData()["tsk_stack_frame"] = stack_frame

        if arch=="ARMv8M":
            context.getAdditionalData()["register_map"] = self.getV8MRegisterMap(stack_frame)
        else:
            context.getAdditionalData()["register_map"] = self.getRegisterMap(stack_frame)

        return context

    def getRegisterMap(self, value):
        if value == 1:
            return EXTENDED_REGISTERS_MAP
        elif value == 2:
            return FP_REGISTERS_MAP
        elif value == 4:
            return NEON_REGISTERS_MAP
        else:
            return BASIC_REGISTERS_MAP

    def getV8MRegisterMap(self, value):
        if (not (value & 0x10) ):
            return V8M_EXTENDED_REGISTERS_MAP
        else:
            return V8M_BASIC_REGISTERS_MAP

    def getNonGlobalRegisterNames(self):
        result = set()
        result.update(BASIC_REGISTERS_MAP.keys())
        result.update(EXTENDED_REGISTERS_MAP.keys())
        result.update(FP_REGISTERS_MAP.keys())
        result.update(NEON_REGISTERS_MAP.keys())
        result.update(V8M_BASIC_REGISTERS_MAP.keys())
        result.update(V8M_EXTENDED_REGISTERS_MAP.keys())
        return result