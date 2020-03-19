################################################################################
#
# Copyright (C) 2014,2017 Arm Limited (or its affiliates). All rights reserved.
#
# Quadros RTXC
#
#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

from itertools import *
from osapi import *
from utils import *

M_CLASS_REG_MAP = dict(chain(
    [("R4", -1),
     ("R5", -1),
     ("R6", -1),
     ("R7", -1),
     ("R8", -1),
     ("R9", -1),
     ("R10", -1),
     ("R11", -1),
     ("R0", -1),
     ("R1", -1),
     ("R2", -1),
     ("R3", -1),
     ("R12", -1),
     ("R14", -1),
     ("LR", -1),
     ("PC", -1),
     ("xPSR", -1),
     ("CPSR", -1),
     ("SP", 0)],
     make_reg_range(1000, 8, "D", 0, 16),
     make_reg_range(1000, 4, "S", 0, 32),
     make_reg_list(1128, 4, "FPSCR")
    ))


A_CLASS_REG_MAP = dict(chain(
    [("FPEXC", -1),
     ("xPSR", -1),
     ("CPSR", -1),
     ("R0", -1),
     ("R1", -1),
     ("R2", -1),
     ("R3", -1),
     ("R4", -1),
     ("R5", -1),
     ("R6", -1),
     ("R7", -1),
     ("R8", -1),
     ("R9", -1),
     ("R10", -1),
     ("R11", -1),
     ("R12", -1),
     ("R14", -1),
     ("LR", -1),
     ("PC", -1),
     ("SP", 0)],
    make_reg_range(1000, 4, "S", 0, 32),
    make_reg_range(1000, 8, "D", 0, 32)
))

class ContextsProvider( ExecutionContextsProvider ):

    createdMap = 0

    def getCurrentOSContext( self, debugSession ):

        if self.createdMap == 0:
            archName = debugSession.getTargetInformation( ).getArchitecture( ).getName( )
            if archName == "ARMv7M" or archName == "ARMv7R" or archName == "ARMv6M":
                createRegisterMap( M_CLASS_REG_MAP, M_REG_GEN_NAMES, debugSession )
            else:
                createRegisterMap( A_CLASS_REG_MAP, A_REG_GEN_NAMES, debugSession )
            self.createdMap = 1;

        hipritsk = gethipritsk( debugSession )

        return self.createContextFromTaskControlBlock( hipritsk, debugSession  )

    def getAllOSContexts( self, debugSession ):

        contexts = [ ]

        pocdt = getocdt( TASK_KCLASS, debugSession )

        n_statics = getStatics( pocdt, debugSession )
        n_objects = getObjects( pocdt, debugSession )

        for i in range( n_statics + 1 ):
            contexts.append( self.createContextFromTaskControlBlock( GETPTCB( pocdt, debugSession, i ), debugSession ) )

        for i in range( n_statics + 1, n_objects + 1 ):
            j = i - n_statics - 1
            if isObjectInuse( pocdt, j, debugSession ):
                contexts.append( self.createContextFromTaskControlBlock( GETPTCB( pocdt, debugSession, i ), debugSession ) )

        return contexts

    def getOSContextSavedRegister( self, debugSession, context, name ):

        offset = context.getAdditionalData( )[ "register_map" ].get( name, None )
        if offset == None:
            return None

        if offset >= 1000:
            offset = offset - 1000
            base = context.getAdditionalData( )[ "pvfpregs" ]
            if base == None:
                return None
            if debugSession.evaluateExpression( "(long)" + str( base ) ).readAsNumber( ) == 0:
                return None
        else:
            base = context.getAdditionalData( )[ "stack_ptr" ]

        if name == "SP":
            return debugSession.evaluateExpression( "(long)" + str( base ) )
        else:
            addr = base.addOffset( offset )
            return debugSession.evaluateExpression( "(long*)" + str( addr ) )

    def createContextFromTaskControlBlock( self, tcbPtr, debugSession ):

        tcbMembers = tcbPtr.dereferencePointer( ).getStructureMembers( )

        taskId = tcbMembers[ "task" ].readAsNumber( )

        taskName = GetObjectName( TASK_KCLASS, taskId, debugSession )

        taskStatus = tcbMembers[ "status" ].readAsNumber( )

        taskStatusText = getTaskStatusText( taskStatus )

        contexts = OSContext( taskId, taskName, taskStatusText )

        stackPointer = tcbMembers[ "sp" ].readAsAddress( )

        if taskStatus in ( QUEUE_WAIT, MAILBOX_WAIT, PARTITION_WAIT, ALARM_WAIT, MUTEX_WAIT, SEMAPHORE_WAIT ):
            stackPointer = debugSession.evaluateExpression( "*(unsigned long*)" + str( stackPointer ) ).readAsAddress( )

        contexts.getAdditionalData( )[ "stack_ptr" ] = stackPointer

        archName = debugSession.getTargetInformation( ).getArchitecture( ).getName( )
        if archName == "ARMv7M" or archName == "ARMv7R" or archName == "ARMv6M":
            if isMember("pvfpregs", tcbMembers ):
                pvfpregs = tcbMembers[ "pvfpregs" ].readAsAddress( )
                contexts.getAdditionalData( )[ "pvfpregs" ] = pvfpregs
            contexts.getAdditionalData( )[ "register_map" ] = M_CLASS_REG_MAP
        else:
            pvfpregs = tcbMembers[ "pvfpregs" ].readAsAddress( )
            contexts.getAdditionalData( )[ "pvfpregs" ] = pvfpregs
            contexts.getAdditionalData( )[ "register_map" ] = A_CLASS_REG_MAP

        return contexts
 
    def getNonGlobalRegisterNames(self):
        result = set()
        set.update({n for (n,_) in M_REG_GEN_NAMES})
        set.update({n for (n,_) in A_REG_GEN_NAMES})
        set.update({n for (n,_) in REG_VFP_NAMES})
        return result
