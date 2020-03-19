# ###############################################################################
#
# Copyright (C) 2014,2017 Arm Limited (or its affiliates). All rights reserved.
#
# FreeRTOS - V7.6.0 / V8.0.0RC ARM Cortex M / A
#
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

from osapi import *
from globs import *
from utils import *
from itertools import *


# ARM M3/M4 (No FPU) basic register stack
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
     "xPSR": 60L,
     "CPSR": 60L,
       "SP": 64L
}

# ARM M4F register stack - no task FPU
M_CLASS_EXTENDED_REGISTERS_MAP = \
{
       "R4":  0L,
       "R5":  4L,
       "R6":  8L,
       "R7": 12L,
       "R8": 16L,
       "R9": 20L,
      "R10": 24L,
      "R11": 28L,
       "LR": 32L,
       "R0": 36L,
       "R1": 40L,
       "R2": 44L,
       "R3": 48L,
      "R12": 52L,
       "LR": 56L,
       "PC": 60L,
     "xPSR": 64L,
     "CPSR": 64L,
       "SP": 68L
}

# ARM M4F register stack - with task FPU
M_CLASS_FPU_REGISTERS_MAP = \
{
       "R4":   0L,
       "R5":   4L,
       "R6":   8L,
       "R7":  12L,
       "R8":  16L,
       "R9":  20L,
      "R10":  24L,
      "R11":  28L,
       "LR":  32L,
      "S16":  36L,
      "S17":  40L,
      "S18":  44L,
      "S19":  48L,
      "S20":  52L,
      "S21":  56L,
      "S22":  60L,
      "S23":  64L,
      "S24":  68L,
      "S25":  72L,
      "S26":  76L,
      "S27":  80L,
      "S28":  84L,
      "S29":  88L,
      "S30":  92L,
      "S31":  96L,
       "D8":  36L,
       "D9":  44L,
      "D10":  52L,
      "D11":  60L,
      "D12":  68L,
      "D13":  76L,
      "D14":  84L,
      "D15":  92L,
       "R0": 100L,
       "R1": 104L,
       "R2": 108L,
       "R3": 112L,
      "R12": 116L,
       "LR": 120L,
       "PC": 124L,
     "xPSR": 128L,
     "CPSR": 128L,
       "S0": 132L,
       "S1": 136L,
       "S2": 140L,
       "S3": 144L,
       "S4": 148L,
       "S5": 152L,
       "S6": 156L,
       "S7": 160L,
       "S8": 164L,
       "S9": 168L,
      "S10": 172L,
      "S11": 176L,
      "S12": 180L,
      "S13": 184L,
      "S14": 188L,
      "S15": 192L,
       "D0": 132L,
       "D1": 140L,
       "D2": 148L,
       "D3": 156L,
       "D4": 164L,
       "D5": 172L,
       "D6": 180L,
       "D7": 188L,
    "FPSCR": 196L,
       "SP": 200L
}

# ARM A9 basic register stack
A_CLASS_BASIC_REGISTERS_MAP = \
{
       "R0":   8L,
       "R1":  12L,
       "R2":  16L,
       "R3":  20L,
       "R4":  24L,
       "R5":  28L,
       "R6":  32L,
       "R7":  36L,
       "R8":  40L,
       "R9":  44L,
      "R10":  48L,
      "R11":  52L,
      "R12":  56L,
       "LR":  60L,
       "PC":  64L,
     "xPSR":  68L,
     "CPSR":  68L,
       "SP":  72L
}

# ARM A9 extended register stack
A_CLASS_FPU_REGISTERS_MAP = dict(chain(
    [("FPSCR",   4L)],
    # Thirty-two 64-bit double-word registers, D0-D31. (FPU register bank)
    make_reg_range(8L, 8L, "D", 0, 32),
    # Thirty-two 32-bit double-word registers, S0-S31. (FPU register bank) (aliased with D0-D16)
    make_reg_range(8L, 4L, "S", 0, 32),
     # Basic registers
    make_reg_range(268L, 4L, "R", 0, 13),
    make_reg_list(320, 4, "LR", "PC", "CPSR", "SP")
    ))

class ContextsProvider( ExecutionContextsProvider ):

    # Get context of current executing task
    def getCurrentOSContext( self, debugger ) :

        # Make sure expression is valid
        if debugger.symbolExists( PX_CURRENT_TCB ) :

            # Get point to TCB of currently executing task
            currentTCBPtr = debugger.evaluateExpression( PX_CURRENT_TCB )

            # Make sure pointer valid
            if currentTCBPtr.readAsNumber( ) :

                # Get TCB
                currentTCB = currentTCBPtr.dereferencePointer( )

                # Create context
                return self.createContextFromTaskControlBlock( debugger, currentTCB, None )

    # Get context of all created tasks
    def getAllOSContexts( self, debugger ):

        # List is empty
        contexts = [ ]

        # Check expressions are valid
        if debugger.symbolExists( PX_CURRENT_TCB ) and \
           debugger.symbolExists( PX_READY_TASKS_LISTS ) and \
           debugger.symbolExists( PX_DELAYED_TASKLIST ) and \
           debugger.symbolExists( PX_OVERFLOW_DELAYED_TASK_LIST ) and \
           debugger.symbolExists( X_PENDING_READY_LIST ) and \
           debugger.symbolExists( X_TASKS_WAITING_TERMINATION ) and \
           debugger.symbolExists( X_SUSPENDED_TASK_LIST ) :

            # Get current task context
            currentTCBPtr = debugger.evaluateExpression( PX_CURRENT_TCB )
            if currentTCBPtr.readAsNumber( ) :
                currentTCB = currentTCBPtr.dereferencePointer( )
                contexts.append( self.createContextFromTaskControlBlock( debugger, currentTCB, None ) )

            # Get ready tasks
            readyLists = debugger.evaluateExpression( PX_READY_TASKS_LISTS ).getArrayElements( )
            for readyList in readyLists :
                tcbListItems = readTCBItems( readyList )
                for tcb in tcbListItems :
                    contexts.append( self.createContextFromTaskControlBlock( debugger, tcb, PX_READY_TASKS_LISTS ) )

            # Get delayed tasks
            delayedTasksListPtr = debugger.evaluateExpression( PX_DELAYED_TASKLIST )
            if delayedTasksListPtr.readAsNumber( ) :
                delayedTasksList = delayedTasksListPtr.dereferencePointer( )
                tcbListItems = readTCBItems( delayedTasksList )
                for tcb in tcbListItems :
                    contexts.append( self.createContextFromTaskControlBlock( debugger, tcb, PX_DELAYED_TASKLIST ) )

            # Get delayed (over-flowed) tasks
            delayedTasksListPtr = debugger.evaluateExpression( PX_OVERFLOW_DELAYED_TASK_LIST )
            if delayedTasksListPtr.readAsNumber( ) :
                delayedTasksList = delayedTasksListPtr.dereferencePointer( )
                tcbListItems = readTCBItems( delayedTasksList )
                for tcb in tcbListItems :
                    contexts.append( self.createContextFromTaskControlBlock( debugger, tcb, PX_OVERFLOW_DELAYED_TASK_LIST ) )

            # Get pending tasks
            pendingTasksList = debugger.evaluateExpression( X_PENDING_READY_LIST )
            tcbListItems = readTCBItems( pendingTasksList )
            for tcb in tcbListItems :
                contexts.append( self.createContextFromTaskControlBlock( debugger, tcb, X_PENDING_READY_LIST ) )

            # Get tasks waiting termination
            waitermTasksList = debugger.evaluateExpression( X_TASKS_WAITING_TERMINATION )
            tcbListItems = readTCBItems( waitermTasksList )
            for tcb in tcbListItems :
                contexts.append( self.createContextFromTaskControlBlock( debugger, tcb, X_TASKS_WAITING_TERMINATION ) )

            # Get suspended tasks
            suspendTasksList = debugger.evaluateExpression( X_SUSPENDED_TASK_LIST )
            tcbListItems = readTCBItems( suspendTasksList )
            for tcb in tcbListItems :
                contexts.append( self.createContextFromTaskControlBlock( debugger, tcb, X_SUSPENDED_TASK_LIST ) )

        # All task contexts
        return contexts

    # Get register contents saved on task stack
    def getOSContextSavedRegister( self, debugger, context, name ):

        # Check if requested register is available
        offset = context.getAdditionalData( )[ "register_map" ].get( name, None )
        if offset == None:
            return None

        # Get stack pointer
        base = context.getAdditionalData( )[ "stack_ptr" ]

        # Get locations of requested register
        base = base.addOffset( offset )

        # Are we reading the stack pointer?
        if name == "SP":
            return debugger.evaluateExpression( "(long)" + str( base ) )
        else:
            return debugger.evaluateExpression( "(long*)" + str( base ) )

    # Create context from task control block
    def createContextFromTaskControlBlock( self, debugger, tcb, listName ):

        # Get structure members of TCB
        members = tcb.getStructureMembers( )

        # Get task id number (use TCB number)
        if TCB_UX_TCB_NUMBER in members:
            taskId = members[ TCB_UX_TCB_NUMBER ].readAsNumber()
        else:
            taskId = tcb.getLocationAddress().getLinearAddress()

        # Get task name
        name = members[ TCB_PC_TASK_NAME ].readAsNullTerminatedString( )

        # Get task state
        if not listName:
            state = "RUNNING"
        else:
            # State depends which list task is in
            state = getStateNameFromList( listName )

        # Create task context
        context = OSContext( taskId, name, state )

        # Get stack pointer
        stackPointer = members[ TCB_PX_TOP_OF_STACK ].readAsAddress( )

        # Save stack pointer
        context.getAdditionalData( )[ "stack_ptr" ] = stackPointer

        # Get register map name
        regMapName = getRegMapName( stackPointer, debugger )

        # Save register map
        context.getAdditionalData( )[ "register_map" ] = self.getRegisterMap( regMapName )

        # Complete task context
        return context

    # Get register map
    def getRegisterMap( self, value ):
        if value == REG_MAP_V7AVFP:
            return A_CLASS_FPU_REGISTERS_MAP
        elif value == REG_MAP_V7ABASIC:
            return A_CLASS_BASIC_REGISTERS_MAP
        elif value == REG_MAP_V7MVFP:
            return M_CLASS_FPU_REGISTERS_MAP
        elif value == REG_MAP_V7MEXT:
            return M_CLASS_EXTENDED_REGISTERS_MAP
        elif value == REG_MAP_V7MBASIC:
            return M_CLASS_BASIC_REGISTERS_MAP


    def getNonGlobalRegisterNames(self):
        result = set()
        result.update(M_CLASS_BASIC_REGISTERS_MAP.keys())
        result.update(M_CLASS_EXTENDED_REGISTERS_MAP.keys())
        result.update(M_CLASS_FPU_REGISTERS_MAP.keys())
        result.update(A_CLASS_BASIC_REGISTERS_MAP.keys())
        result.update(A_CLASS_FPU_REGISTERS_MAP.keys())
        return result
