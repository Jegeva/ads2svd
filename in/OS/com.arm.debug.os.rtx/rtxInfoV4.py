# Copyright (C) 2018 Arm Limited (or its affiliates). All rights reserved.

from itertools import chain

from osapi import DECIMAL
from rtxIterator import *
from rtx_member_names import MEMBER_NAME_BY_VERSION


class RtxInfoV4:

    OS_RUNNING_STATE = 1

    ControlBlockIdentifier = {
        'Thread'          : 0,
        'Mailbox'         : 1,
        'Semaphore'       : 2,
        'Mutex'           : 3
    }

    THREAD_STATES = {
        0 : "INACTIVE",
        1 : "READY",
        2 : "RUNNING",
        3 : "WAIT_DLY",
        4 : "WAIT_ITV",
        5 : "WAIT_OR",
        6 : "WAIT_AND",
        7 : "WAIT_SEM",
        8 : "WAIT_MBX",
        9 : "WAIT_MUT"
    }

    def getVersion(self):
        return "V4"

    def isKernelInitialised(self, debugger):
        return debugger.evaluateExpression("os_running").readAsNumber() == 1

    def getKernelState(self, dbg):
        kernel_state = dbg.evaluateExpression("os_running").readAsNumber()
        if (kernel_state == 0):
            return 'kernelNotRunning'
        elif (kernel_state == 1):
            return 'kernelRunning'
        else:
            return 'Unknown'

    def getMemberName(self, name):
        return MEMBER_NAME_BY_VERSION[name]

    def getCType(self, cbName):
        if (cbName == "Thread"):
            return "P_TCB"
        elif (cbName == "Mailbox"):
            return "P_MCB"
        elif (cbName == "Semaphore"):
            return "P_SCB"
        elif (cbName == "Mutex"):
            return "P_MUCB"
        else:
            raise DebugSessionException("Invalid type %s" % cbName)

    def getActiveTasks(self, dbg):
        return chain(toIterator(dbg, "&os_idle_TCB", None),
                     RtxArrayIterator(dbg.evaluateExpression("os_active_TCB").getArrayElements()))

    def getTaskIdType(self):
        return DECIMAL

    def getTaskId(self, tcbPtr, members):
        return members["task_id"].readAsNumber()

    def getDisplayableTaskId(self, tcbPtr, members):
        #for now the id is displayed as a string to be compatible with RTX5 which use task address as identifier
        return str(self.getTaskId(tcbPtr, members))

    def getCurrentTask(self, dbg):
        return dbg.evaluateExpression("os_tsk.run")

    def getTaskState(self, stateId, members=None):
        name = RtxInfoV4.THREAD_STATES[stateId]
        return name if name else str(stateId)

    def getControlBlockIdentifiers(self):
        return RtxInfoV4.ControlBlockIdentifier

    def getStackInfo(self, dbg):
        return dbg.evaluateExpression("os_stackinfo").readAsNumber()

    def isStackUsageWatermarkEnabled(self, dbg):
        return (self.getStackInfo(dbg) & 0xF0000000) > 0

    def isStackOverflowCheckEnabled(self, dbg):
        return (self.getStackInfo(dbg) >> 24) != 0

    def getStackSize(self, members, dbg):
        #The priv_stack member contains the user set stack size for this
        #task, if it contains a value of zero then the task has the
        #system default stack size (os_stackinfo).
        stackSize = members["priv_stack"].readAsNumber()

        if (stackSize == 0):
            stackInfo = dbg.evaluateExpression("os_stackinfo").readAsNumber()
            stackSize = stackInfo & 0xFFFF

        return stackSize

