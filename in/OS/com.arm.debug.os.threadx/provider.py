# Copyright (C) 2013,2017 Arm Limited (or its affiliates). All rights reserved.

from osapi import *
from bytepools_counters import BytepoolCounters
from blockpools_counters import BlockpoolCounters
from timer_counters import TimerCounters
from semaphore_counters import SemaphoreCounters
from eventflags_counters import EventFlagsCounters
from mutex_counters import MutexCounters
from thread_counters import ThreadCounters
from queue_counters import QueueCounters
from threads import Threads
from timers import Timers
from queues import Queues
from semaphores import Semaphores
from mutexes import Mutexes
from eventflags import EventFlags
from blockpools import BlockPools
from bytepools import BytePools
from kernelinfo import KernelInfo
from contexts import ContextsProvider

# this script effectively implements com.arm.debug.extension.os.IOSProvider

def getOSContextProvider():
    return ContextsProvider()

def getDataModel():
    return Model("threadx", [Threads(), Timers(), Queues(), Semaphores(), Mutexes(), EventFlags(),
                            BlockPools(), BytePools(), KernelInfo(), ThreadCounters(), QueueCounters(),
                            MutexCounters(), EventFlagsCounters(), SemaphoreCounters(), TimerCounters(),
                            BytepoolCounters(), BlockpoolCounters()])

def isOSInitialised(debugger):
    # When _tx_thread_system_state equals 0xF0F0F0F0 or 0xF0F0F0F1 the OS is in its initialisation
    # stage. 0x0 indicates a thread is currently executing. Non-zero values indicate an interrupt is
    # being processed, and the more nested interrupts, the higher the value.
    # We therefore wait until this variable changes to indicate executing/idle/isr state.
    # This isn't a fool proof method since the memory could have junk data, and we can't always check
    # for a specific value since the state variable also serves as an interrupt counter during normal
    # operation.
    try:
        state = debugger.evaluateExpression("_tx_thread_system_state")

        if state.getType().isPointerType():
            # If _tx_thread_system_state is a pointer, we don't have debug
            # symbols for the kernel, so deference to the correct type
            state = state.dereferencePointer("unsigned int*")

        state_value = state.readAsNumber()

        # Check for known ThreadX initialisation values
        if state_value == 0xF0F0F0F0 or state_value == 0xF0F0F0F1:
            return False
        # Check for insane interrupt counter values (TheadX uses
        # _tx_thread_system_state to count nested interrupts: anything above a
        # million looks suspiciously like memory have not been initialised to
        # zero, as is the case for some - all? - ARM's models)
        elif state_value > 1000000:
            return False
        else:
            return True
    except DebugSessionException:
        return False;

def areOSSymbolsLoaded(debugger):
    return debugger.symbolExists("_tx_thread_current_ptr")
