# Copyright (C) 2013-2014,2017 Arm Limited (or its affiliates). All rights reserved.

from itertools import *
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
M_CLASS_EXTENDED_REGISTERS_MAP = dict(chain(
    # Thirty-two 64-bit double-word registers, D0-D31. (FPU register bank)
    make_reg_range(0, 4, "S", 0, 32),
    make_reg_range(0, 8, "D", 0, 16),
    make_reg_list(128, 4, "FPSCR"),
    make_reg_range(132, 4, "R", 4, 8),
    make_reg_range(164, 4, "R", 0, 4),
    make_reg_list(180, 4, "R12", "LR", "PC", "XPSR", "SP")
    ))

# ARM A9 basic register stack
A_CLASS_BASIC_REGISTERS_MAP = dict(chain(
    make_reg_list(0, 4, "CPSR"),
    make_reg_range(4, 4, "R", 0, 13),
    make_reg_list(56, 4, "LR", "PC", "SP")
    ))

# ARM A9 floating point register stack (task registers NOT saved)
A_CLASS_EXTENDED_REGISTERS_MAP = dict(chain(
    make_reg_list(0, 4, "FPEXC", "FPEXC", "CPSR"),
    make_reg_range(12, 4, "R", 0, 13),
    make_reg_list(64, 4, "LR", "PC", "SP")
    ))

# ARM A9 floating point register stack (half registers saved)
A_CLASS_EXTENDED_FP16_REGISTERS_MAP = dict(chain(
    make_reg_list(0, 4, "FPEXC"),
    make_reg_range(4, 8, "D", 0, 16),
    make_reg_range(4, 4, "S", 0, 32),
    make_reg_list(132, 4, "FPSCR", "CPSR"),
    make_reg_range(140, 4, "R", 0, 13),
    make_reg_list(192, 4, "LR", "PC", "SP")
    ))

# ARM A9 floating point register stack (all registers saved)
A_CLASS_EXTENDED_FP32_REGISTERS_MAP = dict(chain(
    make_reg_list(0, 4, "FPEXC"),
    make_reg_range(4, 8, "D", 0, 32),
    make_reg_range(4, 4, "S", 0, 32),
    make_reg_list(260, 4, "FPSCR", "CPSR"),
    make_reg_range(268, 4, "R", 0, 13),
    make_reg_list(320, 4, "LR", "PC", "SP")
    ))

class ContextsProvider( ExecutionContextsProvider ):

    # Get context of current executing task
    def getCurrentOSContext( self, debugger ):
        # This symbol points to the TCB of the current executing task
        osTCBCurName = globGetName( OS_TCB_CUR, debugger )
        if osTCBCurName:
            tcb = debugger.evaluateExpression( osTCBCurName )
            # Its id is based on the address of the TCB
            id = tcb.readAsAddress( ).getLinearAddress( )
            # Get all structure members of the TCB
            members = tcb.dereferencePointer( ).getStructureMembers( )
            # Create task context
            return self.createContextFromTaskControlBlock( id, members, debugger )

    # Get context of all executing tasks
    def getAllOSContexts( self, debugger ):
        contexts = []   # List is empty
        # Get table of all tasks (these table contains pointers of each TCB)
        osTCBPrioTblName = globGetName( OS_TCB_PRIO_TBL, debugger )
        if osTCBPrioTblName:
            taskPtrs = debugger.evaluateExpression( osTCBPrioTblName ).getArrayElements( )
            # Get each TCB in the table
            for taskPtr in taskPtrs:
                # If no task created, pointer to TCB is NULL
                if taskPtr.readAsNumber( ) > 1:
                    # Use address of TCB as its id
                    id = taskPtr.readAsAddress( ).getLinearAddress( )
                    # Get all structure members of the TCB
                    members = taskPtr.dereferencePointer( ).getStructureMembers( )
                    # Create task context and add to list
                    contexts.append( self.createContextFromTaskControlBlock( id, members, debugger ) )
        return contexts

    # Get register contents saved on task stack
    def getOSContextSavedRegister( self, debugger, context, name ):
        offset = context.getAdditionalData( )[ "register_map" ].get( name, None )
        if offset == None:
            return None
        base = context.getAdditionalData( )[ "stack_ptr" ]
        base = base.addOffset( offset )
        if name == "SP":
            return debugger.evaluateExpression( "(long)" + str( base ) )
        else:
            return debugger.evaluateExpression( "(long*)" + str( base ) )

    # Determine if uCOS-II is compiled with floating point support
    def isFpEnabled( self, debugger ):

        fpOpt = 0     # Default is no support for FPU

        # Symbol possibly exists only on Cortex M4 ports
        if globGetName( OS_CPU_FP_REG_PUSH, debugger ):
            fpOpt = 1     # Must be compiled with floating point enabled
        else:

            # Symbol exists on Cortex A series ports
            functionName = globGetName( OS_CPU_ARM_DREG_CNT_GET, debugger )
            if functionName:

                # Determine register count from first instruction of function:
                #
                #    MOV     R0, #<no of registers>
                #
                # The number of registers is hard coded in first 8 bits of the instruction.
                functionAddr = debugger.evaluateExpression( functionName ).getLocationAddress( ).getLinearAddress( )
                instrPtr = debugger.evaluateExpression( "(long*)" + str( functionAddr ) )
                instr = instrPtr.dereferencePointer( ).readAsNumber( )
                regCount = instr & 0xFF

                # Check for legal values
                if regCount == 16 or regCount == 32:
                    fpOpt = regCount

        # Floating point option
        return fpOpt

    # Determine if uCOS-II task floating point support option set
    def isTaskFpEnabled( self, members ):
        enabled = 0     # Default is no support for FPU
        # Task options symbol name
        osTCBOptName = getMemberName( OS_TCB_OPT, members )
        if osTCBOptName:
            # Get value ...
            opts = members[ osTCBOptName ].readAsNumber( )
            if opts & 4:    # .., and check if option bit set
                enabled = 1
        return enabled

    def createContextFromTaskControlBlock( self, id, members, debugger ):
        if id == 0:
            # now we are at a system/other core task which is not properly setup
            # no need to go further
            return None
        else:
            osTCBTaskName = getMemberName( OS_TCB_TASKNAME, members )
            if osTCBTaskName:
                nameAddr = members[ osTCBTaskName ].readAsNumber( )
                name = members[ osTCBTaskName ].readAsNullTerminatedString( )
            else:
                return None

        # Current execution status of task
        osTCBStatName = getMemberName( OS_TCB_STAT, members )
        if not osTCBStatName:
            return None

        state = getBitOptNames( TASK_STATE_NAMES, members.get( osTCBStatName ).readAsNumber( ) )

        context = ExecutionContext( id, name, state )

        osTCBStkPtrName = getMemberName( OS_TCB_STKPTR, members )
        if not osTCBStkPtrName:
            return None

        stackPointer = members[ osTCBStkPtrName ].readAsAddress( )
        context.getAdditionalData( )[ "stack_ptr" ] = stackPointer

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
        result.update(A_CLASS_BASIC_REGISTERS_MAP.keys())
        result.update(A_CLASS_EXTENDED_REGISTERS_MAP.keys())
        result.update(A_CLASS_EXTENDED_FP16_REGISTERS_MAP.keys())
        result.update(A_CLASS_EXTENDED_FP32_REGISTERS_MAP.keys())
        return result
        

