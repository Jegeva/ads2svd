# ###############################################################################
#
# Copyright (C) 2014,2017 Arm Limited (or its affiliates). All rights reserved.
#
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

# this script effectively implements com.arm.debug.extension.os.IOSProvider

from osapi import *
from contexts import ContextsProvider
from NuTasks import NuTasks
from NuTaskCtrl import NuTaskCtrl
from NuTaskProcs import NuTaskProcs
from NuTaskStacks import NuTaskStacks
from NuHighLevelISR import NuHighLevelISR
from NuHighLevelISRStacks import NuHighLevelISRStacks
from NuTimers import NuTimers
from NuDynamicMemory import NuDynamicMemory
from NuDynamicMemorySuspend import NuDynamicMemorySuspend
from NuEventGroups import NuEventGroups
from NuEventGroupsSuspend import NuEventGroupsSuspend
from NuQueues import NuQueues
from NuQueueSuspend import NuQueueSuspend
from NuSemaphores import NuSemaphores
from NuSemaphoreSuspend import NuSemaphoreSuspend
from NuMailboxes import NuMailboxes
from NuMailboxSuspend import NuMailboxSuspend
from NuPipes import NuPipes
from NuPipeSuspend import NuPipeSuspend
from NuPartitionMemory import NuPartitionMemory
from NuPartitionSuspend import NuPartitionSuspend
from NuKernelData import NuKernelData
from NuProcesses import NuProcesses
from NuProcImageInfo import NuProcImageInfo
from NuSpinlocks import NuSpinlocks

def getOSContextProvider():
    return ContextsProvider()

def getDataModel():
    return Model("nucleus", [NuTasks(),
                             NuTaskCtrl(),
                             NuTaskProcs(),
                             NuTaskStacks(),
                             NuHighLevelISR(),
                             NuHighLevelISRStacks(),
                             NuTimers(),
                             NuDynamicMemory(),
                             NuDynamicMemorySuspend(),
                             NuEventGroups(),
                             NuEventGroupsSuspend(),
                             NuQueues(),
                             NuQueueSuspend(),
                             NuSemaphores(),
                             NuSemaphoreSuspend(),
                             NuSpinlocks(),
                             NuMailboxes(),
                             NuMailboxSuspend(),
                             NuPipes(),
                             NuPipeSuspend(),
                             NuPartitionMemory(),
                             NuPartitionSuspend(),
                             NuKernelData(),
                             NuProcesses(),
                             NuProcImageInfo()
                             ])

def isOSInitialised(debugger):
    return debugger.evaluateExpression("INC_Initialize_State").readAsNumber() == 2

def areOSSymbolsLoaded(debugger):
    return debugger.symbolExists("INC_Initialize_State")
