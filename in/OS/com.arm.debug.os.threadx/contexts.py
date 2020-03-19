# Copyright (C) 2013-2014,2017 Arm Limited (or its affiliates). All rights reserved.

from itertools import *
from osapi import *
from utils import *
import re

ACLASS_INT_STACKFRAME = {"CPSR" : 4L,
                        "R0" : 8L,
                        "R1" : 12L,
                        "R2" : 16L,
                        "R3" : 20L,
                        "R4" : 24L,
                        "R5" : 28L,
                        "R6" : 32L,
                        "R7" : 36L,
                        "R8" : 40L,
                        "R9" : 44L,
                        "R10" : 48L,
                        "R11" : 52L,
                        "R12" : 56L,
                        "LR" : 60L,
                        "PC" : 64L,
                        "SP" : 68L}


# For non-interrupted stack frames, some of these registers aren't available as ThreadX
# uses the calling convention to optimize away some context saving. The PC here actually points
# to the LR, as the LR contains the PC of the OS thread.
ACLASS_NON_INT_STACKFRAME = {"CPSR": 4L,
                             "R4": 8L,
                             "R5": 12L,
                             "R6": 16L,
                             "R7": 20L,
                             "R8": 24L,
                             "R9": 28L,
                             "R10": 32L,
                             "R11": 36L,
                             "PC": 40L,
                             "SP": 44L}

ACLASS_VFP_INT_STACKFRAME = dict(chain(
    [("CPSR",4L)],
    make_reg_range(8, 8, "D", 0, 32),
    make_reg_range(8, 4, "S", 0, 32),
    [("FPSCR",264L)],
    make_reg_range(268, 4, "R", 0, 13),
    make_reg_list(320, 4, "LR", "PC", "SP"),
    ))

ACLASS_VFP_NON_INT_STACKFRAME = dict(chain(
    [("CPSR",4L)],
    make_reg_range(8, 8, "D", 8, 24),
    make_reg_range(8, 4, "S", 8, 24),
    make_reg_list(200, 4, "FPSCR",
                        "R4", "R5", "R6", "R7",
                        "R8", "R9", "R10", "R11",
                        "PC", "SP")
    ))

# AARCH64 stack frames
ACLASS_AARCH64_INT_STACKFRAME = {
                            "SPSR": 0x0, "ELR": 0x8, "X28": 0x10, "reserved": 0x18, "X26": 0x20,
                            "X27": 0x28, "X24": 0x30, "X25": 0x38, "X22": 0x40, "X23": 0x48,
                            "X20": 0x50, "X21": 0x58, "X18": 0x60, "X19": 0x68, "X16": 0x70,
                            "X17": 0x78, "X14": 0x80, "X15": 0x88, "X12": 0x90, "X13": 0x98,
                            "X10": 0xA0, "X11": 0xA8, "X8": 0xB0, "X9": 0xB8, "X6": 0xC0,
                            "X7": 0xC8, "X4": 0xD0, "X5": 0xD8, "X2": 0xE0, "X3": 0xE8,
                            "X0": 0xF0, "X1": 0xF8, "X29": 0x100, "PC": 0x108, "SP": 0x110,
                            "W26": 0x20, "W27": 0x28, "W24": 0x30, "W25": 0x38, "W22": 0x40,
                            "W23": 0x48, "W20": 0x50, "W21": 0x58, "W18": 0x60, "W19": 0x68,
                            "W16": 0x70, "W17": 0x78, "W14": 0x80, "W15": 0x88, "W12": 0x90,
                            "W13": 0x98, "W10": 0xA0, "W11": 0xA8, "W8": 0xB0, "W9": 0xB8,
                            "W6": 0xC0, "W7": 0xC8, "W4": 0xD0, "W5": 0xD8, "W2": 0xE0,
                            "W3": 0xE8, "W0": 0xF0, "W1": 0xF8, "W29": 0x100}

ACLASS_AARCH64_NON_INT_STACKFRAME = {
                            "DAIF": 0x0, "0": 0x8, "X27": 0x10, "X28": 0x18, "X25": 0x20,
                            "X26": 0x28, "X23": 0x30, "X24": 0x38, "X21": 0x40, "X22": 0x48,
                            "X19": 0x50, "X20": 0x58, "X29": 0x60, "PC": 0x68, "SP": 0x70,
                            "W27": 0x10, "W28": 0x18, "W25": 0x20, "W26": 0x28, "W23": 0x30,
                            "W24": 0x38, "W21": 0x40, "W22": 0x48, "W19": 0x50, "W20": 0x58,
                            "W29": 0x60}

ACLASS_AARCH64_VFP_INT_STACKFRAME = {
                            "SPSR": 0x0, "ELR": 0x8, "FPSR": 0x10, "FPCR": 0x18, "Q30": 0x20,
                            "Q31": 0x30, "Q28": 0x40, "Q29": 0x50, "Q26": 0x60, "Q27": 0x70,
                            "Q24": 0x80, "Q25": 0x90, "Q22": 0xA0, "Q23": 0xB0, "Q20": 0xC0,
                            "Q21": 0xD0, "Q18": 0xE0, "Q19": 0xF0, "Q16": 0x100, "Q17": 0x110,
                            "Q14": 0x120, "Q15": 0x130, "Q12": 0x140, "Q13": 0x150, "Q10": 0x160,
                            "Q11": 0x170, "Q8": 0x180, "Q9": 0x190, "Q6": 0x1A0, "Q7": 0x1B0,
                            "Q4": 0x1C0, "Q5": 0x1D0, "Q2": 0x1E0, "Q3": 0x1F0, "Q0": 0x200,
                            "D30": 0x20, "D31": 0x30, "D28": 0x40, "D29": 0x50, "D26": 0x60,
                            "D27": 0x70, "D24": 0x80, "D25": 0x90, "D22": 0xA0, "D23": 0xB0,
                            "D20": 0xC0, "D21": 0xD0, "D18": 0xE0, "D19": 0xF0, "D16": 0x100,
                            "D17": 0x110, "D14": 0x120, "D15": 0x130, "D12": 0x140, "D13": 0x150,
                            "D10": 0x160, "D11": 0x170, "D8": 0x180, "D9": 0x190, "D6": 0x1A0,
                            "D7": 0x1B0, "D4": 0x1C0, "D5": 0x1D0, "D2": 0x1E0, "D3": 0x1F0,
                            "D0": 0x200, "S30": 0x20, "S31": 0x30, "S28": 0x40, "S29": 0x50,
                            "S26": 0x60, "S27": 0x70, "S24": 0x80, "S25": 0x90, "S22": 0xA0,
                            "S23": 0xB0, "S20": 0xC0, "S21": 0xD0, "S18": 0xE0, "S19": 0xF0,
                            "S16": 0x100, "S17": 0x110, "S14": 0x120, "S15": 0x130, "S12": 0x140,
                            "S13": 0x150, "S10": 0x160, "S11": 0x170, "S8": 0x180, "S9": 0x190,
                            "S6": 0x1A0, "S7": 0x1B0, "S4": 0x1C0, "S5": 0x1D0, "S2": 0x1E0,
                            "S3": 0x1F0, "S0": 0x200, "H30": 0x20, "H31": 0x30, "H28": 0x40,
                            "H29": 0x50, "H26": 0x60, "H27": 0x70, "H24": 0x80, "H25": 0x90,
                            "H22": 0xA0, "H23": 0xB0, "H20": 0xC0, "H21": 0xD0, "H18": 0xE0,
                            "H19": 0xF0, "H16": 0x100, "H17": 0x110, "H14": 0x120, "H15": 0x130,
                            "H12": 0x140, "H13": 0x150, "H10": 0x160, "H11": 0x170, "H8": 0x180,
                            "H9": 0x190, "H6": 0x1A0, "H7": 0x1B0, "H4": 0x1C0, "H5": 0x1D0,
                            "H2": 0x1E0, "H3": 0x1F0, "H0": 0x200, "Q1": 0x210, "X28": 0x220,
                            "reserved": 0x228, "X26": 0x230, "X27": 0x238,
                            "X24": 0x240, "X25": 0x248, "X22": 0x250, "X23": 0x258, "X20": 0x260,
                            "X21": 0x268, "X18": 0x270, "X19": 0x278, "X16": 0x280, "X17": 0x288,
                            "X14": 0x290, "X15": 0x298, "X12": 0x2A0, "X13": 0x2A8, "X10": 0x2B0,
                            "X11": 0x2B8, "X8": 0x2C0, "X9": 0x2C8, "X6": 0x2D0, "X7": 0x2D8,
                            "X4": 0x2E0, "X5": 0x2E8, "X2": 0x2F0, "X3": 0x2F8, "X0": 0x300,
                            "X1": 0x308, "X29": 0x310, "PC": 0x318, "SP": 0x320, "W28": 0x220,
                            "W26": 0x230, "W27": 0x238, "W24": 0x240, "W25": 0x248, "W22": 0x250,
                            "W23": 0x258, "W20": 0x260, "W21": 0x268, "W18": 0x270, "W19": 0x278,
                            "W16": 0x280, "W17": 0x288, "W14": 0x290, "W15": 0x298, "W12": 0x2A0,
                            "W13": 0x2A8, "W10": 0x2B0, "W11": 0x2B8, "W8": 0x2C0, "W9": 0x2C8,
                            "W6": 0x2D0, "W7": 0x2D8, "W4": 0x2E0, "W5": 0x2E8, "W2": 0x2F0,
                            "W3": 0x2F8, "W0": 0x300, "W1": 0x308, "W29": 0x310}

ACLASS_AARCH64_VFP_NON_INT_STACKFRAME = {
                            "DAIF": 0x0, "0": 0x8, "FPSR": 0x10, "FPCR": 0x18, "Q14": 0x20,
                            "Q15": 0x30, "Q12": 0x40, "Q13": 0x50, "Q10": 0x60, "Q11": 0x70,
                            "Q8": 0x80, "Q9": 0x90, "D14": 0x20, "D15": 0x30, "D12": 0x40,
                            "D13": 0x50, "D10": 0x60, "D11": 0x70, "D8": 0x80, "D9": 0x90,
                            "S14": 0x20, "S15": 0x30, "S12": 0x40, "S13": 0x50, "S10": 0x60,
                            "S11": 0x70, "S8": 0x80, "S9": 0x90, "H14": 0x20, "H15": 0x30,
                            "H12": 0x40, "H13": 0x50, "H10": 0x60, "H11": 0x70, "H8": 0x80,
                            "H9": 0x90, "X27": 0xA0, "X28": 0xA8, "X25": 0xB0, "X26": 0xB8,
                            "X23": 0xC0, "X24": 0xC8, "X21": 0xD0, "X22": 0xD8, "X19": 0xE0,
                            "X20": 0xE8, "X29": 0xF0, "PC": 0xF8, "SP": 0x100, "W27": 0xA0,
                            "W28": 0xA8, "W25": 0xB0, "W26": 0xB8, "W23": 0xC0,  "W24": 0xC8,
                            "W21": 0xD0, "W22": 0xD8, "W19": 0xE0, "W20": 0xE8, "W29": 0xF0}

# Non-FPU M-class CPU Stack Frame
MCLASS = {"R4"      : 0x00,
          "R5"      : 0x04,
          "R6"      : 0x08,
          "R7"      : 0x0C,
          "R8"      : 0x10,
          "R9"      : 0x14,
          "R10"     : 0x18,
          "R11"     : 0x1C,
          "R0"      : 0x20,
          "R1"      : 0x24,
          "R2"      : 0x28,
          "R3"      : 0x2C,
          "R12"     : 0x30,
          "LR"      : 0x34,
          "PC"      : 0x38,
          "XPSR"    : 0x3C,
          "SP"      : 0x40}

# FPU M-class CPU Stack Frame
MCLASS_VFP = {"S0"      : 0x00,
              "S1"      : 0x04,
              "S2"      : 0x08,
              "S3"      : 0x0C,
              "S4"      : 0x10,
              "S5"      : 0x14,
              "S6"      : 0x18,
              "S7"      : 0x1C,
              "S8"      : 0x20,
              "S9"      : 0x24,
              "S10"     : 0x28,
              "S11"     : 0x2C,
              "S12"     : 0x30,
              "S13"     : 0x34,
              "S14"     : 0x38,
              "S15"     : 0x3C,
              "S16"     : 0x40,
              "S17"     : 0x44,
              "S18"     : 0x48,
              "S19"     : 0x4C,
              "S20"     : 0x50,
              "S21"     : 0x54,
              "S22"     : 0x58,
              "S23"     : 0x5C,
              "S24"     : 0x60,
              "S25"     : 0x64,
              "S26"     : 0x68,
              "S27"     : 0x6C,
              "S28"     : 0x70,
              "S29"     : 0x74,
              "S30"     : 0x78,
              "S31"     : 0x7C,
              "D0"      : 0x00,
              "D1"      : 0x08,
              "D2"      : 0x10,
              "D3"      : 0x18,
              "D4"      : 0x20,
              "D5"      : 0x28,
              "D6"      : 0x30,
              "D7"      : 0x38,
              "D8"      : 0x40,
              "D9"      : 0x48,
              "D10"     : 0x50,
              "D11"     : 0x58,
              "D12"     : 0x60,
              "D13"     : 0x68,
              "D14"     : 0x70,
              "D15"     : 0x78,
              "FPSCR"   : 0x80,
              "R4"      : 0x84,
              "R5"      : 0x88,
              "R6"      : 0x8C,
              "R7"      : 0x90,
              "R8"      : 0x94,
              "R9"      : 0x98,
              "R10"     : 0x9C,
              "R11"     : 0xA0,
              "R0"      : 0xA4,
              "R1"      : 0xA8,
              "R2"      : 0xAC,
              "R3"      : 0xB0,
              "R12"     : 0xB4,
              "LR"      : 0xB8,
              "PC"      : 0xBC,
              "XPSR"    : 0xC0,
              "SP"      : 0xC4}

class ContextsProvider(ExecutionContextsProvider):

    def getCurrentOSContext(self, debugger):
        tcb = getGlobalPointer(debugger, "_tx_thread_current_ptr", "TX_THREAD")
        #we are in the thread scheduler routine
        if(tcb.readAsNumber() == 0):
            return OSContext(0, "System ISR", "READY")
        else:
            #proceed as normal
            return self.createContextFromTaskControlBlock(debugger, tcb.dereferencePointer())

    def getAllOSContexts(self, debugger):
        tcbs = getListHead(debugger, ListTypes.THREAD).dereferencePointer()
        allTCBList = readList(tcbs, ListTypes.THREAD)
        return [self.createContextFromTaskControlBlock(debugger, tcb) for tcb in allTCBList]

    def getOSContextSavedRegister(self, debugger, context, name):
        offset = context.getAdditionalData()["register_map"].get(name, None)
        if offset == None:
            return None
        base = context.getAdditionalData()["stack_ptr"]
        base = base.addOffset(offset)
        if name == "SP":
            return debugger.evaluateExpression("(long)" + str(base))
        else:
            return debugger.evaluateExpression("(long*)" + str(base))

    def hasVFP(self, debugger, members):
        name = "tx_thread_vfp_enable"

        if members.containsKey(name) \
            and members[name].readAsNumber() == 1:
            return True
        else:
            return False

    def createContextFromTaskControlBlock(self, debugger, tcb):
        members = tcb.getStructureMembers()
        id = tcb.getLocationAddress().getLinearAddress()
        threadId = members["tx_thread_id"].readAsNumber()
        name = members["tx_thread_name"].readAsNullTerminatedString()
        state = StateNames[members["tx_thread_state"].readAsNumber()]

        context = OSContext(id, name, state)
        stackPointer = members["tx_thread_stack_ptr"].readAsAddress()
        context.getAdditionalData()["stack_ptr"] = stackPointer

        # the first word on the stack indicates the interrupted status of the frame
        cpuArch = debugger.getTargetInformation().getArchitecture().getName()
        hasVFP = self.hasVFP(debugger, members)
        isInterruptedFrame = debugger.evaluateExpression("*(long)" + str(stackPointer)).readAsNumber() == 1
        is64Bit = debugger.evaluateExpression("sizeof($PC)").readAsNumber() == 8

        context.getAdditionalData()["register_map"] = self.getRegisterMap(cpuArch, hasVFP, isInterruptedFrame, is64Bit)

        return context

    def getRegisterMap(self, cpuArch, hasVFP, isInterruptedFrame, is64Bit):
        if cpuArch == "ARMv7M" or cpuArch == "ARMv6M":
            # M-class registers
            if hasVFP:
                return MCLASS_VFP
            else:
                return MCLASS
        else:
            # A-class or R-class registers
            isV8A = re.match('ARMv8.*A', cpuArch) != None
            isAArch64 = (isV8A and is64Bit)
            if isInterruptedFrame:
                #this is an interrupted stack frame
                if hasVFP:
                    if isAArch64:
                        return ACLASS_AARCH64_VFP_INT_STACKFRAME
                    else:
                        return ACLASS_VFP_INT_STACKFRAME
                else:
                    if isAArch64:
                        return ACLASS_AARCH64_INT_STACKFRAME
                    else:
                        return ACLASS_INT_STACKFRAME
            else:
                if hasVFP:
                    if isAArch64:
                        return ACLASS_AARCH64_VFP_NON_INT_STACKFRAME
                    else:
                        return ACLASS_VFP_NON_INT_STACKFRAME
                else:
                    if isAArch64:
                        return ACLASS_AARCH64_NON_INT_STACKFRAME
                    else:
                        return ACLASS_NON_INT_STACKFRAME



    def getNonGlobalRegisterNames(self):
        result = set()
        result.update(ACLASS_INT_STACKFRAME.keys())
        result.update(ACLASS_NON_INT_STACKFRAME.keys())
        result.update(ACLASS_VFP_INT_STACKFRAME.keys())
        result.update(ACLASS_VFP_NON_INT_STACKFRAME.keys())
        
        result.update(ACLASS_AARCH64_INT_STACKFRAME.keys())
        result.update(ACLASS_AARCH64_NON_INT_STACKFRAME.keys())
        result.update(ACLASS_AARCH64_VFP_INT_STACKFRAME.keys())
        result.update(ACLASS_AARCH64_VFP_NON_INT_STACKFRAME.keys())
        
        result.update(MCLASS.keys())
        result.update(MCLASS_VFP.keys())
        
        return result
    