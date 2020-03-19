# Copyright (C) 2015,2017 Arm Limited (or its affiliates). All rights reserved.

"""
Implementation of OS support for eForce uC3 Standard-Profile RTOS
"""

from osapi import *
from contexts import ContextsProvider
from tasks import Tasks
from semaphores import Semaphores
from eventflags import Eventflags
from dataqueues import DataQueues
from mailboxes import Mailboxes
from mutexes import Mutexes
from message_buffers import MessageBuffers
from rendezvous import Rendezvous
from memory_pools_fixed import MemoryPoolsFixed
from memory_pools_variable import MemoryPoolsVariable
from cyclic_handlers import CyclicHandlers
from alarm_handlers import AlarmHandlers
from interrupt_service_routines import InterruptServiceRoutines
from system import System

from com.arm.debug.extension import DebugSessionException

def getOSContextProvider():
    return ContextsProvider()

def getDataModel():
    return Model("uC3_std", [Tasks(), Semaphores(), Eventflags(), DataQueues(), Mailboxes(), Mutexes(), MessageBuffers(), Rendezvous(), MemoryPoolsFixed(), MemoryPoolsVariable(), CyclicHandlers(), AlarmHandlers(), InterruptServiceRoutines(), System()])

def areOSSymbolsLoaded(debugger):
    try:
        return debugger.symbolExists('_kernel_systbl')
    except DebugSessionException:
        return False

def isOSInitialised(debugger):
    """
    uC3 standard-profile does not have a flag to indicate the OS is up and running, so we
    use a heuristic based on the memory allocated for the _kernel_systbl members.

    The first member allocated is the system service block (_kernel_systbl.ssb_free), and
    we can calculate the size of this allocation from the _kernel_systbl.ssb_cnt member
    and the size of the T_SSB structure.

    The second member allocated is the ready queue (_kernel_systbl.qrdq), this is allocated
    contiguously after the service block, so we can check that the address of the queue is
    at the expected location.

    This check is not bullet-proof but it would be unlucky for unallocated/random memory
    values to pass. Zero-initialised memory definitely does not.
    """
    try:
        systbl = debugger.evaluateExpression('_kernel_systbl').getStructureMembers()

        ssb_free_ptr = systbl['ssb_free'].readAsNumber()

        if ssb_free_ptr == 0:
            return False

        ssb_cnt = systbl['ssb_cnt'].readAsNumber()
        t_ssb_size = debugger.evaluateExpression('sizeof(T_SSB)').readAsNumber()

        expected_rdq_ptr = ssb_free_ptr + (ssb_cnt * t_ssb_size)

        qrdq_rdq_ptr = systbl['qrdq'].getStructureMembers()['rdq'].readAsNumber()

        return expected_rdq_ptr == qrdq_rdq_ptr

    except DebugSessionException, e:
        return False
