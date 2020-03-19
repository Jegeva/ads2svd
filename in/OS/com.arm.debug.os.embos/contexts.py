################################################################################
#
# Copyright (C) 2014,2017 Arm Limited (or its affiliates). All rights reserved.
#
# embOS - 3.88c ARM Cortex M / 3.88h ARM Cortex A
#
#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

from itertools import *
from globs import *
from utils import *

# ARM M3/M4 basic register stack
M_CLASS_BASIC_REGISTERS_MAP = \
{
       "R4":  4L,
       "R5":  8L,
       "R6": 12L,
       "R7": 16L,
       "R8": 20L,
       "R9": 24L,
      "R10": 28L,
      "R11": 32L,
       "LR": 36L,
       "R0": 40L,
       "R1": 44L,
       "R2": 48L,
       "R3": 52L,
      "R12": 56L,
      "R14": 60L,
       "PC": 64L,
     "xPSR": 68L,
     "CPSR": 68L,
       "SP": 72L
}

# ARM M4 floating point register stack
M_CLASS_EXTENDED_REGISTERS_MAP = dict(chain(
    # Standard registers
    make_reg_list(0, 4, "R4", "R5", "R6", "R7", "R8", "R9", "R10", "R11"),
    make_reg_list(36, 4, "LR", "R0", "R1", "R2", "R3", "R12", "R14", "PC", "xPSR"),
    # Sixteen 64-bit double-word registers, D0-D15. (FPU register bank)
    make_reg_range(72, 8, "D", 0, 16),
     # Thirty-two 32-bit single-word registers, S0-S31. (FPU register bank)
    make_reg_range(72, 4, "S", 0, 32),
    # Remaining registers
    make_reg_list(200, 4, "FPSCR", "SP")
    ))


# ARM A9 basic register stack
A_CLASS_BASIC_REGISTERS_MAP = \
{
       "R4":   4L,
       "R5":   8L,
       "R6":  12L,
       "R7":  16L,
       "R8":  20L,
       "R9":  24L,
      "R10":  28L,
      "R11":  32L,
       "PC":  36L,
       "SP":  40L
}

# ARM A9 basic interrupt register stack
A_CLASS_BASIC_INT_REGISTERS_MAP = \
{
       "R4":   4L,
       "R5":   8L,
       "R6":  12L,
       "R7":  16L,
       "R8":  20L,
       "R9":  24L,
      "R10":  28L,
      "R11":  32L,
       "PC":  36L,
       "R0":  40L,
       "R1":  44L,
       "R2":  48L,
       "R3":  52L,
      "R12":  56L,
       "LR":  60L,
     "XPSR":  68L,
     "CPSR":  68L,
       "SP":  72L
}

# ARM A9 FPU D16 register stack
A_CLASS_EXTENDED_FPU16_REGISTERS_MAP =  dict(chain(
    # Sixteen 64-bit double-word registers, D0-D15. (FPU register bank)
    make_reg_range(-136L, 8, "D", 0, 16),
    # Thirty-two 32-bit single-word registers, S0-S31. (FPU register bank)
    make_reg_range(-136L, 4, "S", 0, 32),
    make_reg_list(-8, 4, "FPSCR", "FPSXC"),
    # Basic Registers
    make_reg_list(0, 4, "CC", "R4", "R5", "R6", "R7", "R8", "R9", "R10", "R11", "PC"),
    # Remaining registers
    [("SP", 40L)]
    ))

# ARM A9 FPU D16 interrupt register stack
A_CLASS_EXTENDED_FPU16_INT_REGISTERS_MAP =  dict(chain(
    # Sixteen 64-bit double-word registers, D0-D15. (FPU register bank)
    make_reg_range(-136L, 8, "D", 0, 16),
    # Thirty-two 32-bit single-word registers, S0-S31. (FPU register bank)
    make_reg_range(-136L, 4, "S", 0, 32, ),
    make_reg_list(-8, 4, "FPSCR", "FPSXC"),
    # Basic Registers
    make_reg_list(0, 4, "CC", "R4", "R5", "R6", "R7", "R8", "R9", "R10", "R11", "PC"),
    # Remaining registers
    make_reg_list(40, 4, "R0", "R1", "R2", "R3", "R12", "LR", "CPSR", "SP")
    ))

# ARM A9 NEON register stack
A_CLASS_EXTENDED_NEON_REGISTERS_MAP = dict(chain(
    # Sixteen 128-bit quad word registers, Q0-Q16. (Neon register bank)
    make_reg_range(-264L, 16, "Q", 0, 16),
    # Thirty-two 64-bit double-word registers, D0-D31. (FPU register bank)
    make_reg_range(-264L, 8, "D", 0, 32),
    # Thirty-two 32-bit single-word registers, S0-S31. (FPU register bank)
    make_reg_range(-264L, 4, "S", 0, 32),
    make_reg_list(-8, 4, "FPSCR", "FPSXC"),
    # Basic registers
    make_reg_list(0, 4, "CC", "R4", "R5", "R6", "R7", "R8", "R9", "R10", "R11", "PC"),
    # Remaining registers
    [("SP", 40L)]
    ))

# ARM A9 NEON interrupt register stack
A_CLASS_EXTENDED_NEON_INT_REGISTERS_MAP = dict(chain(
    # Sixteen 128-bit quad word registers, Q0-Q16. (Neon register bank)
    make_reg_range(-264L, 16, "Q", 0, 16),
    # Thirty-two 64-bit double-word registers, D0-D31. (FPU register bank)
    make_reg_range( -264L, 8, "D", 0, 32),
    # Thirty-two 32-bit single-word registers, S0-S31. (FPU register bank)
    make_reg_range(-264L, 4, "S", 0, 32),
    make_reg_list(-8, 4, "FPSCR", "FPSXC"),
    # Basic registers
    make_reg_list(0, 4, "CC", "R4", "R5", "R6", "R7", "R8", "R9", "R10", "R11", "PC"),
    # Remaining registers
    make_reg_list(40, 4, "R0", "R1", "R2", "R3", "R12", "LR", "XPSR", "CPSR", "SP")
    ))

# Dummy idle register stack
IDLE_REGISTERS_MAP = \
{
       "SP": 0L
}

class ContextsProvider( ExecutionContextsProvider ):

    # Get context of current executing task
    def getCurrentOSContext( self, debugSession ):

        # Default task members
        pTaskMembers = ""

        # Get current executing task
        pTaskPtr = debugSession.evaluateExpression( globCreateRef( [ OS_GLOBAL, OS_GLOBALS_PCURRENTTASK ] ) )

        # Get task pointer address
        pTaskAddr = pTaskPtr.readAsAddress( ).getLinearAddress( )

        # Is address valid?
        if pTaskAddr:

            # Get TCB members
            pTaskMembers = pTaskPtr.dereferencePointer( ).getStructureMembers( )

        # Create task context (when no task running, just create a dummy idle task)
        return self.createContextFromTaskControlBlock( pTaskAddr, pTaskMembers, debugSession )

    # Get context of all created tasks
    def getAllOSContexts( self, debugSession ):

        # List is empty
        contexts = [ ]

        # This points to the start of a linked list of all tasks
        pTask = debugSession.evaluateExpression( globCreateRef( [ OS_GLOBAL, OS_GLOBALS_PTASK ] ) )

        # Get all task
        while pTask.readAsNumber( ):

            # Use address of TCB as its id
            pTaskId = pTask.readAsAddress( ).getLinearAddress( )

            # Get all structure members of the TCB
            taskMembers = pTask.dereferencePointer( ).getStructureMembers( )

            # Create task context and add to list
            contexts.append( self.createContextFromTaskControlBlock( pTaskId, taskMembers, debugSession ) )

            # Get pointer to next task
            pTask = taskMembers[ OS_TASK_PNEXT ]

        # All task contexts
        return contexts

    # Get register contents saved on task stack
    def getOSContextSavedRegister( self, debugSession, context, name ):

        # Check if requested register is available
        offset = context.getAdditionalData( )[ "register_map" ].get( name, None )
        if offset == None:
            return None

        # Get stack pointer
        base = context.getAdditionalData( )[ "stack_ptr" ]

        # Get locations of requested register
        addr = base.addOffset( offset )

        # Stack pointer is returned differently for some reason!
        if name == "SP":
            return debugSession.evaluateExpression( "(long)" + str( addr ) )
        else:
            return debugSession.evaluateExpression( "(long*)" + str( addr ) )

    # Create context from task control block
    def createContextFromTaskControlBlock( self, taskAddr, members, debugger ):

        # Is there a current task running?
        if taskAddr == 0:

            # No, create a dummy task to keep debugger happy
            taskName = "OS_Idle"
            taskStatusText = "Idle"

            # Get current stack pointer (SP) register value
            stackPointer = debugger.evaluateExpression( "$SP" ).readAsAddress( )

            # Create a task context
            context = ExecutionContext( taskAddr, taskName, taskStatusText )

            # Save stack pointer
            context.getAdditionalData( )[ "stack_ptr" ] = stackPointer

            # Set dummy register map
            context.getAdditionalData( )[ "register_map" ] = self.getRegisterMap( "idle" )

        # A real task is running
        else:

            # Get name of running task
            taskName = getMemberValue( members, OS_TASK_NAME, FORMAT_STRING_PTR, debugger )

            # Get task status
            taskStatus = members[ OS_TASK_STAT ].readAsNumber( )

            # Convert status code to descriptive text
            taskStatusText = getTaskStatusText( taskStatus )

            # Get stack pointer from TCB (saved on context switch)
            stackPointer = members[ OS_TASK_PSTACK ].readAsAddress( )

            # Create a task context
            context = ExecutionContext( taskAddr, taskName, taskStatusText )

            # Save stack pointer
            context.getAdditionalData( )[ "stack_ptr" ] = stackPointer

            # Get register map name
            regMapName = getRegMapName( stackPointer, members, debugger )

            # Save register map
            context.getAdditionalData( )[ "register_map" ] = self.getRegisterMap( regMapName )

        # Task context
        return context

    # Get register map
    def getRegisterMap( self, value ):
        if value == REG_MAP_V7ANEON:
            return A_CLASS_EXTENDED_NEON_REGISTERS_MAP
        elif value == REG_MAP_V7ANEONINT:
            return A_CLASS_EXTENDED_NEON_INT_REGISTERS_MAP
        elif value == REG_MAP_V7AFPU16:
            return A_CLASS_EXTENDED_FPU16_REGISTERS_MAP
        elif value == REG_MAP_V7AFPU16INT:
            return A_CLASS_EXTENDED_FPU16_INT_REGISTERS_MAP
        elif value == REG_MAP_V7ABASIC:
            return A_CLASS_BASIC_REGISTERS_MAP
        elif value == REG_MAP_V7ABASICINT:
            return A_CLASS_BASIC_INT_REGISTERS_MAP
        elif value == REG_MAP_V7MVFP:
            return M_CLASS_EXTENDED_REGISTERS_MAP
        elif value == REG_MAP_V7MBASIC:
            return M_CLASS_BASIC_REGISTERS_MAP
        else:
            return IDLE_REGISTERS_MAP
        
    def getNonGlobalRegisterNames(self):
        result = set()
        result.update(M_CLASS_BASIC_REGISTERS_MAP.keys())
        result.update(M_CLASS_EXTENDED_REGISTERS_MAP.keys())
        result.update(A_CLASS_BASIC_REGISTERS_MAP.keys())
        result.update(A_CLASS_BASIC_INT_REGISTERS_MAP.keys())
        result.update(A_CLASS_EXTENDED_FPU16_REGISTERS_MAP.keys())
        result.update(A_CLASS_EXTENDED_FPU16_INT_REGISTERS_MAP.keys())
        result.update(A_CLASS_EXTENDED_NEON_REGISTERS_MAP.keys())
        result.update(A_CLASS_EXTENDED_NEON_INT_REGISTERS_MAP.keys())
        return result
