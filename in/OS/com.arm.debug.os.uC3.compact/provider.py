# Copyright (C) 2015,2017 Arm Limited (or its affiliates). All rights reserved.

"""
Implementation of OS support for eForce uC3 Compact-Profile RTOS
"""

from osapi import *
from kernel import TS_CYC
from contexts import ContextsProvider
from tasks import Tasks
from semaphores import Semaphores
from eventflags import Eventflags
from dataqueues import DataQueues
from mailboxes import Mailboxes
from memory_pools_fixed import MemoryPoolsFixed
from cyclic_handlers import CyclicHandlers
from shared_stacks import SharedStacks
from system import System

from com.arm.debug.extension import DebugSessionException

def getOSContextProvider():
    return ContextsProvider()

def getDataModel():
    return Model("uC3_compact", [Tasks(), Semaphores(), Eventflags(), DataQueues(), Mailboxes(), MemoryPoolsFixed(), CyclicHandlers(), SharedStacks(), System()])

def areOSSymbolsLoaded(debugger):
    try:
        return debugger.symbolExists('_kernel_cnstbl')
    except DebugSessionException:
        return False

def isOSInitialised(debugger):
    """
    uC3 compact-profile does not have a flag to indicate the OS is up and running.
    Detecting it is correctly initialised is also difficult because all of the system
    resources are statically allocated - although to some extent the OS can always be
    considered initialised.

    The _kernel_systbl.dspint1.b.ctxl flag is set during initialisation but is also used
    when handling interrupts so cannot be used. The main thing done during the OS
    initialisation, and the main thing that will trip up the debugger if it's not
    correctly detected, is that the wait queues will not be initialised. Thus we can
    use this as a check.
    """
    try:
        systbl = debugger.evaluateExpression('_kernel_systbl').getStructureMembers()
        cnstbl = debugger.evaluateExpression('_kernel_cnstbl').getStructureMembers()

        # Check the wait queues contain sensible information (these are used as
        # array indexes by the debugger so if they are wrong we will end up
        # reading bogus memory. Unfortunately this means walking the entire
        # wait queue each time the target stops...
        # This echoes the setup code in uC3krncm1.c
        id_max = cnstbl['id_max'].readAsNumber()
        waique = cnstbl['waique'].getArrayElements(id_max+1)
        atrtbl = cnstbl['atrtbl'].getArrayElements(id_max+1)
        for i in range(1, id_max+1):
            if (atrtbl[i].readAsNumber() & 0xF0) != TS_CYC:
                wq = waique[i].getStructureMembers()
                nid = wq['nid'].readAsNumber()
                pid = wq['pid'].readAsNumber()
                if     nid < 1 or nid > id_max \
                    or pid < 1 or pid > id_max:
                    return False
        return True

    except DebugSessionException, e:
        return False
