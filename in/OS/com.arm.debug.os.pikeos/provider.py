# Copyright (C) 2017 Arm Limited (or its affiliates). All rights reserved.

"""
Implementation of OS support for PikeOS
"""

from osapi import *
from contexts import ContextsProvider
from kernelinfo import KernelInfo

from com.arm.debug.extension import DebugSessionException

def getOSContextProvider():
    return ContextsProvider()

def getDataModel():
    return Model("pikeos", [KernelInfo()])

def areOSSymbolsLoaded(debugger):
    # TODO: Revisit this to ensure the symbols are loaded in the correct address space.
    try:
        return debugger.symbolExists('"src/task.c"::taskdir') and debugger.symbolExists('P4k_thrinfo_t')
    except DebugSessionException:
        return False

def isOSInitialised(debugger):
    # As per the Kernel Reference Manual 1.38.1.14, p4_kdev_init_complete is called at the end of
    # the kernel's initialisation phase. This sets the *init_complete flag to 1. This, like all the
    # kernel's data structures, is uninitialised at the entry point, so 4-bytes of uninitialised
    # memory here reading as 1 would incorrectly signal the OS as initialised, but as all the data
    # structures are uninitialised at first we can't do much better, and 1 in 2^32 aint bad.
    init_sym_v41 = '"kdev/src/sys_kdev.c"::init_complete'
    init_sym_v42 = '"kdev/src/sys_kdev.c"::kdev_init_complete'
    if debugger.symbolExists(init_sym_v41):
        # PikeOS 4.1
        init_complete = debugger.evaluateExpression(init_sym_v41).readAsNumber()
    else:
        # PikeOS4.2
        init_complete = debugger.evaluateExpression(init_sym_v42).readAsNumber()
    return init_complete == 1
