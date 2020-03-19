# Copyright (C) 2013,2015,2017,2018 Arm Limited (or its affiliates). All rights reserved.

from osapi import *
from contexts import ContextsProvider
from com.arm.debug.extension import DebugSessionException
import cfg
from rtxInfoV4 import RtxInfoV4
from rtxInfoV5 import RtxInfoV5

from tasks import Tasks
from timers import Timers
from stacks import Stacks
from mailboxes import Mailboxes
from messagequeues import MessageQueues
from memorypools import MemoryPools
from mutexes import Mutexes
from semaphores import Semaphores
from system import System

# this script effectively implements com.arm.debug.extension.os.IOSProvider

def getOSContextProvider():
    return ContextsProvider()

def getDataModel():
    return Model("rtx", [Mailboxes(), MemoryPools(), MessageQueues(), Mutexes(), Semaphores(), Stacks(), System(), Tasks(), Timers()])

def isOSInitialised(debugger):
    try:
        return cfg.rtxInfo.isKernelInitialised(debugger)
    except DebugSessionException:
        return False

def areOSSymbolsLoaded(debugger):
    if debugger.symbolExists("os_active_TCB"):
        cfg.rtxInfo = RtxInfoV4()
    elif debugger.symbolExists("osRtxInfo"):
        cfg.rtxInfo = RtxInfoV5()

    return True if cfg.rtxInfo else False
