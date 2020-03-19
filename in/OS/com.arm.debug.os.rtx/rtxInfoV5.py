# Copyright (C) 2018 Arm Limited (or its affiliates). All rights reserved.

from itertools import chain

from osapi import TEXT
from utils import toHex
from rtxIterator import *

class RtxInfoV5:

    KERNEL_STATE_READY       = 1
    KERNEL_STATE_RUNNING     = 2

    OS_FLAGS_WAIT_ANY        = 0x00000000L    #Wait for any flag (default).
    OS_FLAGS_WAIT_ALL        = 0x00000001L    #Wait for all flags.

    ControlBlockIdentifier = {
        'Invalid'         : 0,
        'Thread'          : 1,
        'Timer'           : 2,
        'EventFlags'      : 3,
        'Mutex'           : 4,
        'Semaphore'       : 5,
        'MemoryPool'      : 6,
        'Message'         : 7,
        'MessageQueue'    : 8
    }


    kernelState = {
        0                 : 'osKernelInactive',         # Inactive.
        1                 : 'osKernelReady',            # Ready.
        2                 : 'osKernelRunning',          # Running.
        3                 : 'osKernelLocked',           # Locked.
        4                 : 'osKernelSuspended',        # Suspended.
        -1                : 'osKernelError',            # Error.
    }


    THREAD_BLOCKED_STATE_ID  = 3

    THREAD_STATES = {
        0                                : "INACTIVE",
        1                                : "READY",
        2                                : "RUNNING",
        THREAD_BLOCKED_STATE_ID          : "BLOCKED",
        4                                : "TERMINATED",
        (THREAD_BLOCKED_STATE_ID | 0x10) : "WAIT_DELAY",
        (THREAD_BLOCKED_STATE_ID | 0x20) : "WAIT_JOIN",
        (THREAD_BLOCKED_STATE_ID | 0x30) : "WAIT_THREAD_FLAGS",
        (THREAD_BLOCKED_STATE_ID | 0x40) : "WAIT_EVENT_FLAGS",
        (THREAD_BLOCKED_STATE_ID | 0x50) : "WAIT_MUTEX",
        (THREAD_BLOCKED_STATE_ID | 0x60) : "WAIT_SEMAPHORE",
        (THREAD_BLOCKED_STATE_ID | 0x70) : "WAIT_MEMORY_POOL",
        (THREAD_BLOCKED_STATE_ID | 0x80) : "WAIT_MESSAGE_GET",
        (THREAD_BLOCKED_STATE_ID | 0x90) : "WAIT_MESSAGE_PUT"
    }

    def getVersion(self):
        return "V5"

    def isKernelInitialised(self, dbg):
        kernel_state = dbg.evaluateExpression("osRtxInfo.kernel.state").readAsNumber()
        return (kernel_state==RtxInfoV5.KERNEL_STATE_READY) or (kernel_state==RtxInfoV5.KERNEL_STATE_RUNNING)

    def getKernelState(self, dbg):
        kernel_state = dbg.evaluateExpression("osRtxInfo.kernel.state").readAsNumber()
        return RtxInfoV5.kernelState[kernel_state]

    def getMemberName(self, name):
        return name

    def getCType(self, cbName):
        return "osRtx" + cbName + "_t*"

    def getActiveTasks(self, dbg):
        # - thread.run.curr holds the current task.
        # - When context switching thread.run.next holds the next task to
        #   execute, which will have been removed from all the other thread
        #   lists. At all other times it duplicates thread.run.curr.
        # - thread.ready.thread_list holds the list of all threads that are
        #   ready to run.
        # - thread.delay_list holds the list of all threads which have called
        #   osDelay. It can duplicate items in thread.wait_list.
        # - thread.wait_list holds the list of all threads which are waiting
        #   to run. It can duplicate items in thread.delay_list.
        observed_tasks = set()
        active_tasks = []
        for task in chain(toIterator(dbg, "osRtxInfo.thread.run.curr", ""),
                          toIterator(dbg, "osRtxInfo.thread.run.next", ""),
                          toIterator(dbg, "osRtxInfo.thread.ready.thread_list", "thread_next"),
                          toIterator(dbg, "osRtxInfo.thread.delay_list", "delay_next"),
                          toIterator(dbg, "osRtxInfo.thread.wait_list",  "delay_next")):
            task_ptr = task.readAsNumber()
            if task_ptr not in observed_tasks:
                observed_tasks.add(task_ptr)
                active_tasks.append(task)
        return active_tasks

    def getTaskIdType(self):
        return TEXT #address

    def getTaskId(self, tcbPtr, members):
        return tcbPtr.readAsNumber()

    def getDisplayableTaskId(self, tcbPtr, members):
        return toHex(self.getTaskId(tcbPtr, members))

    def getCurrentTask(self, dbg):
        return dbg.evaluateExpression("osRtxInfo.thread.run.curr")

    def getTaskState(self, stateId, members=None):
        if((stateId & 0x0F) != RtxInfoV5.THREAD_BLOCKED_STATE_ID):
            stateId = stateId & 0x0F

        name = RtxInfoV5.THREAD_STATES[stateId]

        if (members and ((name == "WAIT_THREAD_FLAGS") or (name == "WAIT_EVENT_FLAGS"))):
            flagsOption = members["flags_options"].readAsNumber()
            name += "_ALL" if ((flagsOption & RtxInfoV5.OS_FLAGS_WAIT_ALL) != 0) else "_ANY"

        return name if name else str(stateId)

    def getControlBlockIdentifiers(self):
        return RtxInfoV5.ControlBlockIdentifier

    def getStackInfo(self, dbg):
        return dbg.evaluateExpression("osRtxConfig.flags").readAsNumber()

    def isStackUsageWatermarkEnabled(self, dbg):
        return (self.getStackInfo(dbg) & 0x4) != 0

    def isStackOverflowCheckEnabled(self, dbg):
        return (self.getStackInfo(dbg) & 0x2) != 0

    def getStackSize(self, members, dbg):
        return members["stack_size"].readAsNumber()

