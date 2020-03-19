################################################################################
#
# Copyright (C) 2014,2017 Arm Limited (or its affiliates). All rights reserved.
#
#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

from osapi import *
from utils import *

M_CLASS_AR_REG_MAP = \
{
       "SP":  0,

       "R4":  4,
       "R5":  8,
       "R6": 12,
       "R7": 16,
       "R8": 20,
       "R9": 24,
      "R10": 28,
      "R11": 32,

       "R0": 36,
       "R1": 40,
       "R2": 44,
       "R3": 48,
      "R12": 52,
      "R14": 56,
       "LR": 56,
       "PC": 60,
     "CPSR": 64
}

M_CLASS_AR_FPU32_REG_MAP = \
{
       "SP":  0,

       "R4":  4,
       "R5":  8,
       "R6": 12,
       "R7": 16,
       "R8": 20,
       "R9": 24,
      "R10": 28,
      "R11": 32,

    "FPSXC": 36,
     "xPSR": 36,

       "S0": 40,
       "S1": 44,
       "S2": 48,
       "S3": 52,
       "S4": 56,
       "S5": 60,
       "S6": 64,
       "S7": 68,
       "S8": 72,
       "S9": 76,
      "S10": 80,
      "S11": 84,
      "S12": 88,
      "S13": 92,
      "S14": 96,
      "S15": 100,
      "S16": 104,
      "S17": 108,
      "S18": 112,
      "S19": 116,
      "S20": 120,
      "S21": 124,
      "S22": 128,
      "S23": 132,
      "S24": 136,
      "S25": 140,
      "S26": 144,
      "S27": 148,
      "S28": 152,
      "S29": 156,
      "S30": 160,
      "S31": 164,

       "D0": 40,
       "D1": 48,
       "D2": 56,
       "D3": 64,
       "D4": 72,
       "D5": 80,
       "D6": 88,
       "D7": 96,
       "D8": 104,
       "D9": 112,
      "D10": 120,
      "D11": 128,
      "D12": 136,
      "D13": 144,
      "D14": 152,
      "D15": 160,

       "Q0": 40,
       "Q1": 56,
       "Q2": 72,
       "Q3": 88,
       "Q4": 104,
       "Q5": 120,
       "Q6": 136,
       "Q7": 152,

       "R0": 168,
       "R1": 172,
       "R2": 176,
       "R3": 180,
      "R12": 184,
      "R14": 188,
       "LR": 188,
       "PC": 192,
     "CPSR": 196
}

A_CLASS_AR_REG_MAP = \
{
       "SP":  0,

       "R4":  4,
       "R5":  8,
       "R6": 12,
       "R7": 16,
       "R8": 20,
       "R9": 24,
      "R10": 28,
      "R11": 32,

       "R0": 36,
       "R1": 40,
       "R2": 44,
       "R3": 48,
      "R12": 52,
     "CPSR": 56,
      "R14": 60,
       "LR": 60,
       "PC": 64
}

A_CLASS_AR_FPU32_REG_MAP = \
{
       "SP":  0,

       "R4":  4,
       "R5":  8,
       "R6": 12,
       "R7": 16,
       "R8": 20,
       "R9": 24,
      "R10": 28,
      "R11": 32,

    "FPSXC": 36,
     "xPSR": 36,

       "S0": 40,
       "S1": 44,
       "S2": 48,
       "S3": 52,
       "S4": 56,
       "S5": 60,
       "S6": 64,
       "S7": 68,
       "S8": 72,
       "S9": 76,
      "S10": 80,
      "S11": 84,
      "S12": 88,
      "S13": 92,
      "S14": 96,
      "S15": 100,
      "S16": 104,
      "S17": 108,
      "S18": 112,
      "S19": 116,
      "S20": 120,
      "S21": 124,
      "S22": 128,
      "S23": 132,
      "S24": 136,
      "S25": 140,
      "S26": 144,
      "S27": 148,
      "S28": 152,
      "S29": 156,
      "S30": 160,
      "S31": 164,

       "D0": 40,
       "D1": 48,
       "D2": 56,
       "D3": 64,
       "D4": 72,
       "D5": 80,
       "D6": 88,
       "D7": 96,
       "D8": 104,
       "D9": 112,
      "D10": 120,
      "D11": 128,
      "D12": 136,
      "D13": 144,
      "D14": 152,
      "D15": 160,

       "Q0": 40,
       "Q1": 56,
       "Q2": 72,
       "Q3": 88,
       "Q4": 104,
       "Q5": 120,
       "Q6": 136,
       "Q7": 152,

       "R0": 168,
       "R1": 172,
       "R2": 176,
       "R3": 180,
      "R12": 184,
     "CPSR": 188,
      "R14": 192,
       "LR": 192,
       "PC": 196
}

A_CLASS_AR_FPU64_REG_MAP = \
{
       "SP":  0,

       "R4":  4,
       "R5":  8,
       "R6": 12,
       "R7": 16,
       "R8": 20,
       "R9": 24,
      "R10": 28,
      "R11": 32,

    "FPSXC": 36,
     "xPSR": 36,

       "S0": 40,
       "S1": 44,
       "S2": 48,
       "S3": 52,
       "S4": 56,
       "S5": 60,
       "S6": 64,
       "S7": 68,
       "S8": 72,
       "S9": 76,
      "S10": 80,
      "S11": 84,
      "S12": 88,
      "S13": 92,
      "S14": 96,
      "S15": 100,
      "S16": 104,
      "S17": 108,
      "S18": 112,
      "S19": 116,
      "S20": 120,
      "S21": 124,
      "S22": 128,
      "S23": 132,
      "S24": 136,
      "S25": 140,
      "S26": 144,
      "S27": 148,
      "S28": 152,
      "S29": 156,
      "S30": 160,
      "S31": 164,
      "S32": 168,
      "S33": 172,
      "S34": 176,
      "S35": 180,
      "S36": 184,
      "S37": 188,
      "S38": 192,
      "S39": 196,
      "S40": 200,
      "S41": 204,
      "S42": 208,
      "S43": 212,
      "S44": 216,
      "S45": 220,
      "S46": 224,
      "S47": 228,
      "S48": 232,
      "S49": 236,
      "S50": 240,
      "S51": 244,
      "S52": 248,
      "S53": 252,
      "S54": 256,
      "S55": 260,
      "S56": 264,
      "S57": 268,
      "S58": 272,
      "S59": 276,
      "S60": 280,
      "S61": 284,
      "S62": 288,
      "S63": 292,

       "D0": 40,
       "D1": 48,
       "D2": 56,
       "D3": 64,
       "D4": 72,
       "D5": 80,
       "D6": 88,
       "D7": 96,
       "D8": 104,
       "D9": 112,
      "D10": 120,
      "D11": 128,
      "D12": 136,
      "D13": 144,
      "D14": 152,
      "D15": 160,
      "D16": 168,
      "D17": 176,
      "D18": 184,
      "D19": 192,
      "D20": 200,
      "D21": 208,
      "D22": 216,
      "D23": 224,
      "D24": 232,
      "D25": 240,
      "D26": 248,
      "D27": 256,
      "D28": 264,
      "D29": 272,
      "D30": 280,
      "D31": 288,

       "Q0": 40,
       "Q1": 56,
       "Q2": 72,
       "Q3": 88,
       "Q4": 104,
       "Q5": 120,
       "Q6": 136,
       "Q7": 152,
       "Q8": 168,
       "Q9": 184,
      "Q10": 200,
      "Q11": 216,
      "Q12": 232,
      "Q13": 248,
      "Q14": 264,
      "Q15": 280,

       "R0": 296,
       "R1": 300,
       "R2": 304,
       "R3": 308,
      "R12": 312,
     "CPSR": 316,
      "R14": 320,
       "LR": 320,
       "PC": 324
}

M_CLASS_TS_REG_MAP = \
{
       "SP":  0,

       "R4":  4,
       "R5":  8,
       "R6": 12,
       "R7": 16,
       "R8": 20,
       "R9": 24,
      "R10": 28,
      "R11": 32,
       "PC": 36
}

M_CLASS_TS_FPU_REG_MAP = \
{
       "SP":  0,

       "R4":  4,
       "R5":  8,
       "R6": 12,
       "R7": 16,
       "R8": 20,
       "R9": 24,
      "R10": 28,
      "R11": 32,
       "PC": 36,

    "FPSXC": 40,
     "xPSR": 40,

       "S0": 44,
       "S1": 48,
       "S2": 52,
       "S3": 56,
       "S4": 60,
       "S5": 64,
       "S6": 68,
       "S7": 72,
       "S8": 76,
       "S9": 80,
      "S10": 84,
      "S11": 88,
      "S12": 92,
      "S13": 96,
      "S14": 100,
      "S15": 104,
      "S16": 108,
      "S17": 112,
      "S18": 116,
      "S19": 120,
      "S20": 124,
      "S21": 128,
      "S22": 132,
      "S23": 136,
      "S24": 140,
      "S25": 144,
      "S26": 148,
      "S27": 152,
      "S28": 156,
      "S29": 160,
      "S30": 164,
      "S31": 168,

       "D0": 44,
       "D1": 52,
       "D2": 60,
       "D3": 68,
       "D4": 76,
       "D5": 84,
       "D6": 92,
       "D7": 100,
       "D8": 108,
       "D9": 116,
      "D10": 124,
      "D11": 132,
      "D12": 140,
      "D13": 148,
      "D14": 156,
      "D15": 164
}

A_CLASS_TS_REG_MAP = \
{
       "SP":  0,

       "R4":  4,
       "R5":  8,
       "R6": 12,
       "R7": 16,
       "R8": 20,
       "R9": 24,
      "R10": 28,
      "R11": 32,
       "PC": 36
}

A_CLASS_TS_FPU_REG_MAP = \
{
       "SP":  0,

       "R4":  4,
       "R5":  8,
       "R6": 12,
       "R7": 16,
       "R8": 20,
       "R9": 24,
      "R10": 28,
      "R11": 32,
       "PC": 36,

    "FPSXC": 40,
     "xPSR": 40,

      "S16": 44,
      "S17": 48,
      "S18": 52,
      "S19": 56,
      "S20": 60,
      "S21": 64,
      "S22": 68,
      "S23": 72,
      "S24": 76,
      "S25": 80,
      "S26": 84,
      "S27": 88,
      "S28": 92,
      "S29": 96,
      "S30": 100,
      "S31": 104,

       "D8": 44,
       "D9": 52,
      "D10": 60,
      "D11": 68,
      "D12": 76,
      "D13": 84,
      "D14": 92,
      "D15": 100,

       "Q4": 44,
       "Q5": 60,
       "Q6": 76,
       "Q7": 92
}

IDLE_REGISTERS_MAP = \
{
       "SP": 0L
}

class ContextsProvider( ExecutionContextsProvider ):

    createdMap = 0

    def getCurrentOSContext( self, debugSession ):

        currTCBPtr = getCurrentTask( debugSession )

        return self.createContextFromTaskControlBlock( currTCBPtr, debugSession  )

    def getAllOSContexts( self, debugSession ):

        contexts = [ ]

        firstTaskPtr = nextTaskPtr = getFirstTask( debugSession )

        if firstTaskPtr.readAsNumber( ):

            while True:

                contexts.append( self.createContextFromTaskControlBlock( nextTaskPtr, debugSession  ) )

                nextTaskPtr = getNextTask( nextTaskPtr, debugSession )

                if( nextTaskPtr.readAsNumber( ) == firstTaskPtr.readAsNumber( ) ):
                    break

        return contexts

    def getOSContextSavedRegister( self, debugSession, context, name ):

        offset = context.getAdditionalData( )[ "register_map" ].get( name, None )
        if offset == None:
            return None

        base = context.getAdditionalData( )[ "stack_ptr" ]

        if name == "SP":
            return debugSession.evaluateExpression( "(long)" + str( base ) )
        else:
            addr = base.addOffset( offset )
            return debugSession.evaluateExpression( "(long*)" + str( addr ) )

    def hasFPUSupport( self, members ):
        fpuSupport = False
        if "fpscr" in members:
            fpuSupport = True
        return fpuSupport

    def createContextFromTaskControlBlock( self, tcbPtr, debugSession ):

        # Is there a current task running?
        if tcbPtr == None:

            # No, create a dummy task to keep debugger happy
            taskName = "OS_Idle"
            taskStatusText = "Idle"

            # Get current stack pointer (SP) register value
            stackPointer = debugSession.evaluateExpression( "$SP" ).readAsAddress( )

            # Create a task context
            contexts = ExecutionContext( 0, taskName, taskStatusText )

            # Save stack pointer
            contexts.getAdditionalData( )[ "stack_ptr" ] = stackPointer

            # Set dummy register map
            contexts.getAdditionalData( )[ "register_map" ] = IDLE_REGISTERS_MAP

        # A real task is running
        else:

            taskId = tcbPtr.readAsNumber( )

            tcbMembers = tcbPtr.dereferencePointer( ).getStructureMembers( )

            taskName = tcbMembers[ "tc_name" ].readAsNullTerminatedString( )

            taskStatus = tcbMembers[ "tc_status" ].readAsNumber( )

            taskStatusText = getTaskStatusText( taskStatus )

            contexts = OSContext( taskId, taskName, taskStatusText )

            stackPointer = tcbMembers[ "tc_stack_pointer" ].readAsAddress( )

            contexts.getAdditionalData( )[ "stack_ptr" ] = stackPointer

            #stackType = debugSession.evaluateExpression( "*(unsigned long*)" + str( stackPointer ) ).readAsNumber( )

            stackPtr = tcbMembers[ "tc_stack_pointer" ].readAsNumber( )

            if not isTaskInterruptFrame( tcbMembers, debugSession ):

                sfPtr = debugSession.evaluateExpression( "(" + "ESAL_TS_STK" + "*)(" + hex( stackPtr ) + ")" )
                sfMembers = sfPtr.dereferencePointer( ).getStructureMembers( )
                fpuSupport = self.hasFPUSupport( sfMembers )
                archName = debugSession.getTargetInformation( ).getArchitecture( ).getName( )
                if archName == "ARMv7M" or archName == "ARMv7R" or archName == "ARMv6M":
                    if fpuSupport:
                        contexts.getAdditionalData( )[ "register_map" ] = M_CLASS_TS_FPU_REG_MAP
                    else:
                        contexts.getAdditionalData( )[ "register_map" ] = M_CLASS_TS_REG_MAP
                else:
                    if fpuSupport:
                        contexts.getAdditionalData( )[ "register_map" ] = A_CLASS_TS_FPU_REG_MAP
                    else:
                        contexts.getAdditionalData( )[ "register_map" ] = A_CLASS_TS_REG_MAP
            else:

                sfPtr = debugSession.evaluateExpression( "(" + "ESAL_AR_STK" + "*)(" + hex( stackPtr ) + ")" )
                sfMembers = sfPtr.dereferencePointer( ).getStructureMembers( )
                fpuSupport = self.hasFPUSupport( sfMembers )

                archName = debugSession.getTargetInformation( ).getArchitecture( ).getName( )
                if archName == "ARMv7M" or archName == "ARMv7R" or archName == "ARMv6M":
                    if fpuSupport:
                        contexts.getAdditionalData( )[ "register_map" ] = M_CLASS_AR_FPU32_REG_MAP
                    else:
                        contexts.getAdditionalData( )[ "register_map" ] = M_CLASS_AR_REG_MAP
                else:
                    if fpuSupport:
                        noFpRegs = len( sfMembers[ "s" ].getArrayElements( ) )
                        if noFpRegs == 32:
                            contexts.getAdditionalData( )[ "register_map" ] = A_CLASS_AR_FPU32_REG_MAP
                        else:
                            contexts.getAdditionalData( )[ "register_map" ] = A_CLASS_AR_FPU64_REG_MAP
                    else:
                        contexts.getAdditionalData( )[ "register_map" ] = A_CLASS_AR_REG_MAP

        return contexts
    
    def getNonGlobalRegisterNames(self):
        result = set()
        result.update(M_CLASS_AR_REG_MAP.keys())
        result.update(M_CLASS_AR_FPU32_REG_MAP.keys())
        result.update(A_CLASS_AR_REG_MAP.keys())
        result.update(A_CLASS_AR_FPU32_REG_MAP.keys())
        result.update(A_CLASS_AR_FPU64_REG_MAP.keys())
        result.update(M_CLASS_TS_REG_MAP.keys())
        result.update(M_CLASS_TS_FPU_REG_MAP.keys())
        result.update(A_CLASS_TS_REG_MAP.keys())
        result.update(A_CLASS_TS_FPU_REG_MAP.keys())
        result.update(IDLE_REGISTERS_MAP.keys())
        return result
