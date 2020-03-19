# Copyright (C) 2015,2017 Arm Limited (or its affiliates). All rights reserved.

"""
Implementation of OS support for Wind River VxWorks RTOS
"""

from osapi import *
from contexts import ContextsProvider
from devices import Devices
from file_descriptors import FileDescriptors
from kerneldata import KernelData
from semaphores import Semaphores
from tasks import Tasks
from taskopts import TaskOpts
from taskstacks import TaskStacks

def getOSContextProvider():
    return ContextsProvider()

def getDataModel():
    return Model("vxworks", [ Devices(), FileDescriptors(), KernelData(), Semaphores(), Tasks(),
                              TaskOpts(), TaskStacks() ] )

def areOSSymbolsLoaded(debugger):
    return debugger.symbolExists('"taskLib.c"::taskLibInstalled')

def isOSInitialised(debugger):
    return debugger.evaluateExpression('"taskLib.c"::taskLibInstalled').readAsNumber() == 1

def isCoreInitialised(debugger, coreId):
    cpuEnabledFlag = debugger.evaluateExpression('"vxCpuLib.c"::vxCpuEnabled').readAsNumber()
    cpuEnabledMask = 1 << coreId
    return (cpuEnabledFlag & cpuEnabledMask) != 0
