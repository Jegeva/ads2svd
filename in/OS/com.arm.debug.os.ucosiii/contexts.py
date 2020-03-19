# Copyright (C) 2013-2014,2017 Arm Limited (or its affiliates). All rights reserved.

from osapi import *
from utils import *
from globs import *

# ARM M3 basic register stack
M_CLASS_BASIC_REGISTERS_MAP = \
{
       "R4":  0L,
       "R5":  4L,
       "R6":  8L,
       "R7": 12L,
       "R8": 16L,
       "R9": 20L,
      "R10": 24L,
      "R11": 28L,
       "R0": 32L,
       "R1": 36L,
       "R2": 40L,
       "R3": 44L,
      "R12": 48L,
       "LR": 52L,
       "PC": 56L,
     "CPSR": 60L,
     "XPSR": 60L,
       "SP": 64L
}

# ARM M4 floating point register stack
M_CLASS_EXTENDED_REGISTERS_MAP = \
{
       "S0": 0L,
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
       "D0":   0L,
       "D1":   8L,
       "D2":  16L,
       "D3":  24L,
       "D4":  32L,
       "D5":  40L,
       "D6":  48L,
       "D7":  56L,
       "D8":  64L,
       "D9":  72L,
      "D10":  80L,
      "D11":  88L,
      "D12":  96L,
      "D13": 104L,
      "D14": 112L,
      "D15": 120L,
    "FPSCR": 128L,
       "R4": 132L,
       "R5": 136L,
       "R6": 140L,
       "R7": 144L,
       "R8": 148L,
       "R9": 152L,
      "R10": 156L,
      "R11": 160L,
       "R0": 164L,
       "R1": 168L,
       "R2": 172L,
       "R3": 176L,
      "R12": 180L,
       "LR": 184L,
       "PC": 188L,
     "CPSR": 192L,
     "XPSR": 192L,
       "SP": 196L
}

# ARM A9 basic register stack
A_CLASS_BASIC_REGISTERS_MAP = \
{
     "CPSR": 0L,
       "R0": 4L,
       "R1": 8L,
       "R2": 12L,
       "R3": 16L,
       "R4": 20L,
       "R5": 24L,
       "R6": 28L,
       "R7": 32L,
       "R8": 36L,
       "R9": 40L,
      "R10": 44L,
      "R11": 48L,
      "R12": 52L,
       "LR": 56L,
       "PC": 60L,
       "SP": 64L
}

# ARM A9 floating point register stack (task registers NOT saved)
A_CLASS_EXTENDED_REGISTERS_MAP = \
{
    "FPEXC": 0L,
    "FPEXC": 4L,
     "CPSR": 8L,
       "R0": 12L,
       "R1": 16L,
       "R2": 20L,
       "R3": 24L,
       "R4": 28L,
       "R5": 32L,
       "R6": 36L,
       "R7": 40L,
       "R8": 44L,
       "R9": 48L,
      "R10": 52L,
      "R11": 56L,
      "R12": 60L,
       "LR": 64L,
       "PC": 68L,
       "SP": 72L
}

# ARM A9 floating point register stack (half registers saved)
A_CLASS_EXTENDED_FP16_REGISTERS_MAP = \
{
    "FPEXC": 0L,
       "D0": 4L,
       "D1": 12L,
       "D2": 20L,
       "D3": 28L,
       "D4": 36L,
       "D5": 44L,
       "D6": 52L,
       "D7": 60L,
       "D8": 68L,
       "D9": 76L,
      "D10": 84L,
      "D11": 92L,
      "D12": 100L,
      "D13": 108L,
      "D14": 116L,
      "D15": 124L,
    "FPSCR": 132L,
     "CPSR": 136L,
       "R0": 140L,
       "R1": 144L,
       "R2": 148L,
       "R3": 152L,
       "R4": 156L,
       "R5": 160L,
       "R6": 164L,
       "R7": 168L,
       "R8": 172L,
       "R9": 176L,
      "R10": 180L,
      "R11": 184L,
      "R12": 188L,
       "LR": 192L,
       "PC": 196L,
       "SP": 200L
}

# ARM A9 floating point register stack (all registers saved)
A_CLASS_EXTENDED_FP32_REGISTERS_MAP = \
{
    "FPEXC": 0L,
       "D0": 4L,
       "D1": 12L,
       "D2": 20L,
       "D3": 28L,
       "D4": 36L,
       "D5": 44L,
       "D6": 52L,
       "D7": 60L,
       "D8": 68L,
       "D9": 76L,
      "D10": 84L,
      "D11": 92L,
      "D12": 100L,
      "D13": 108L,
      "D14": 116L,
      "D15": 124L,
      "D16": 132L,
      "D17": 140L,
      "D18": 148L,
      "D19": 156L,
      "D20": 164L,
      "D21": 172L,
      "D22": 180L,
      "D23": 188L,
      "D24": 196L,
      "D25": 204L,
      "D26": 212L,
      "D27": 220L,
      "D28": 228L,
      "D29": 236L,
      "D30": 244L,
      "D31": 252L,
    "FPSCR": 260L,
     "CPSR": 264L,
       "R0": 268L,
       "R1": 272L,
       "R2": 276L,
       "R3": 280L,
       "R4": 284L,
       "R5": 288L,
       "R6": 292L,
       "R7": 296L,
       "R8": 300L,
       "R9": 304L,
      "R10": 308L,
      "R11": 312L,
      "R12": 316L,
       "LR": 320L,
       "PC": 324L,
       "SP": 328L
}

class ContextsProvider(ExecutionContextsProvider):

    def getCurrentOSContext(self, debugger):
        osTCBCurPtrName = globGetName( OS_TCB_CUR_PTR, debugger )
        if osTCBCurPtrName:
            tcb = debugger.evaluateExpression(osTCBCurPtrName)
            id = tcb.readAsAddress().getLinearAddress()
            members = tcb.dereferencePointer().getStructureMembers()
            return self.createContextFromTaskControlBlock(id, members, debugger)

    def getAllOSContexts(self, debugger):
        contexts = []

        osTaskDbgListPtrName = globGetName( OS_TASK_DBG_LIST_PTR, debugger )
        if osTaskDbgListPtrName:
            osTaskDbgListPtr = debugger.evaluateExpression( osTaskDbgListPtrName )
            head = osTaskDbgListPtr
            while head.readAsNumber( ) != 0:
                id = head.readAsAddress( ).getLinearAddress( )
                members = head.dereferencePointer( ).getStructureMembers( )
                dbgNextPtrName = getMemberName( OS_TCB_DBG_NEXT_PTR, members )
                if not dbgNextPtrName:
                    break
                contexts.append( self.createContextFromTaskControlBlock( id, members, debugger ) )
                head = head.dereferencePointer( ).getStructureMembers( )[dbgNextPtrName]

        return contexts

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

    # Determine if uCOS-III is compiled with floating point support
    def isFpEnabled( self, debugger ):

        fpOpt = 0     # Default is no support for FPU

        # Symbol possibly exists only on Cortex M4 ports
        if globGetName( OS_CPU_FP_REG_PUSH, debugger ):
            fpOpt = 1     # Must be compiled with floating point enabled
        else:

            # Symbol exists on Cortex A series ports
            functionName = globGetName( OS_CPU_ARM_DREG_CNT_GET, debugger )
            if functionName:

                """
                Determine register count from first instruction of function:

                    MOV     R0, #<no of registers>

                The number of registers is hard coded in first 8 bits of the instruction.
                """
                functionAddr = debugger.evaluateExpression( functionName ).getLocationAddress( ).getLinearAddress( )
                instrPtr = debugger.evaluateExpression( "(long*)" + str( functionAddr ) )
                instr = instrPtr.dereferencePointer( ).readAsNumber( )
                regCount = instr & 0xFF

                # Check for legal values
                if regCount == 16 or regCount == 32:
                    fpOpt = regCount

        # Floating point option
        return fpOpt

    # Determine if uCOS-III task floating point support option set
    def isTaskFpEnabled( self, members ):
        enabled = 0     # Default is no support for FPU
        # Task options sysmbol name
        osTCBOptName = getMemberName( OS_TCB_OPT, members )
        if osTCBOptName:
            # Get value ...
            opts = members[ osTCBOptName ].readAsNumber( )
            if opts & 4:    # .., and check if option bit set
                enabled = 1
        return enabled

    def createContextFromTaskControlBlock(self, id, members, debugger):
        if id == 0:
            # now we are at a system/other core task which is not properly setup
            # no need to go further
            return None
        else:
            tcbNamePtrName = getMemberName( OS_TCB_NAME_PTR, members )
            if tcbNamePtrName:
                name = members[tcbNamePtrName].readAsNullTerminatedString()

        taskStateName = getMemberName( OS_TCB_TASK_STATE, members )
        if not taskStateName:
            return None

        state = getStateName(TASK_STATE_NAMES, members.get(taskStateName).readAsNumber())

        context = ExecutionContext(id, name, state)

        stkPtrName = getMemberName( OS_TCB_STK_PTR, members )
        if not taskStateName:
            return None

        stackPointer = members[stkPtrName].readAsAddress()
        context.getAdditionalData()["stack_ptr"] = stackPointer

        # Get architecture name
        archName = debugger.getTargetInformation( ).getArchitecture( ).getName( )

        # Get floating point capabilities
        taskFpEnabled = 0   # Default task level FVP option
        fpEnabled = self.isFpEnabled( debugger )    # Has uCOS-II been compiled with FVP
        if fpEnabled != 0:      # Now check task level FVP option
            taskFpEnabled = self.isTaskFpEnabled( members )

        # Determine stack frame being used
        if archName == "ARMv7M" or archName == "ARMv7R" or archName == "ARMv6M":
            if fpEnabled != 0 and taskFpEnabled != 0:
                # Compiled with FVP and task has FVP option set
                context.getAdditionalData( )[ "register_map" ] = self.getRegisterMap( "v7MVFP" )
            else:
                # No FVP
                context.getAdditionalData( )[ "register_map" ] = self.getRegisterMap( "v7MBasic" )
        elif fpEnabled == 0:
            # No FVP
            context.getAdditionalData( )[ "register_map" ] = self.getRegisterMap( "v7ABasic" )
        elif fpEnabled == 16:
            # Compiled with FVP and saving half of the registers
            context.getAdditionalData( )[ "register_map" ] = self.getRegisterMap( "v7AExt" )
        else:
            # Compiled with FVP and saving all of the registers
            context.getAdditionalData( )[ "register_map" ] = self.getRegisterMap( "v7AVFP" )

        return context

    def getRegisterMap( self, value ):
        if value == "v7AVFP":
            return A_CLASS_EXTENDED_FP32_REGISTERS_MAP
        elif value == "v7AExt":
            return A_CLASS_EXTENDED_FP16_REGISTERS_MAP
        elif value == "v7ABasic":
            return A_CLASS_BASIC_REGISTERS_MAP
        elif value == "v7MVFP":
            return M_CLASS_EXTENDED_REGISTERS_MAP
        elif value == "v7MBasic":
            return M_CLASS_BASIC_REGISTERS_MAP

    def getNonGlobalRegisterNames(self):
        result = set()
        result.update(M_CLASS_BASIC_REGISTERS_MAP.keys())
        result.update(M_CLASS_EXTENDED_REGISTERS_MAP.keys())
        result.update(A_CLASS_BASIC_REGISTERS_MAP.keys())
        result.update(A_CLASS_EXTENDED_REGISTERS_MAP.keys())
        result.update(A_CLASS_EXTENDED_FP16_REGISTERS_MAP.keys())
        result.update(A_CLASS_EXTENDED_FP32_REGISTERS_MAP.keys())
        return result

        
        
