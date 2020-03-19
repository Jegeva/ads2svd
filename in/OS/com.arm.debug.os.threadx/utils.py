# Copyright (C) 2013,2017 Arm Limited (or its affiliates). All rights reserved.

from osapi import *

# Index into this list to find the name of the state.
StateNames = ["READY",
              "COMPLETED",
              "TERMINATED",
              "SUSPENDED",
              "SLEEP",
              "QUEUE_SUSP",
              "SEMAPHORE_SUSP",
              "EVENT_FLAG",
              "BLOCK_MEMORY",
              "BYTE_MEMORY",
              "IO_DRIVER",
              "FILE",
              "TCP_IP",
              "MUTEX_SUSP"]

# Types of linked lists
class ListTypes:
    THREAD, TIMER, QUEUE, SEMAPHORE, MUTEX, THREADS_SUSPENDED, EVENTFLAG, \
        BLOCKPOOL, BYTEPOOL = range(9)

# Linked list next ptr names
ListTypeNextPtrs = {ListTypes.THREAD: "tx_thread_created_next",
                    ListTypes.TIMER: "tx_timer_created_next",
                    ListTypes.QUEUE: "tx_queue_created_next",
                    ListTypes.SEMAPHORE: "tx_semaphore_created_next",
                    ListTypes.MUTEX: "tx_mutex_created_next",
                    ListTypes.THREADS_SUSPENDED: "tx_thread_suspended_next",
                    ListTypes.EVENTFLAG: "tx_event_flags_group_created_next",
                    ListTypes.BLOCKPOOL: "tx_block_pool_created_next",
                    ListTypes.BYTEPOOL: "tx_byte_pool_created_next" }

ListTypePtrs = {ListTypes.THREAD: "_tx_thread_created_ptr",
                ListTypes.TIMER: "_tx_timer_created_ptr",
                ListTypes.QUEUE: "_tx_queue_created_ptr",
                ListTypes.SEMAPHORE: "_tx_semaphore_created_ptr",
                ListTypes.MUTEX: "_tx_mutex_created_ptr",
                ListTypes.EVENTFLAG: "_tx_event_flags_created_ptr",
                ListTypes.BLOCKPOOL: "_tx_block_pool_created_ptr",
                ListTypes.BYTEPOOL: "_tx_byte_pool_created_ptr" }

ListTypeStructures = {ListTypes.THREAD: "TX_THREAD",
                      ListTypes.TIMER: "TX_TIMER",
                      ListTypes.QUEUE: "TX_QUEUE",
                      ListTypes.SEMAPHORE: "TX_SEMAPHORE",
                      ListTypes.MUTEX: "TX_MUTEX",
                      ListTypes.EVENTFLAG: "TX_EVENT_FLAGS_GROUP",
                      ListTypes.BLOCKPOOL: "TX_BLOCK_POOL",
                      ListTypes.BYTEPOOL: "TX_BYTE_POOL" }

def makeTextCell(members, name):
    member = members[name]
    return createTextCell(member.readAsNullTerminatedString())

def makeStateCell(members):
    member = members["tx_thread_state"]
    return createTextCell(StateNames[member.readAsNumber()])

def makeNumberCell(members, name):
    return createNumberCell(members[name].readAsNumber())

def makeAddressCell(members, name):
    return createAddressCell(members[name].readAsAddress())

def addressExprsToLong(expr):
    addr = expr.readAsAddress()
    return addr.getLinearAddress()

def getThreadNameList(members, fieldname):
        # Read a list of threads and return a string repr of their names
        threads = readList(members[fieldname].dereferencePointer(),
                           ListTypes.THREADS_SUSPENDED)
        threadName = lambda tcb : tcb['tx_thread_name'].readAsNullTerminatedString()
        names = [threadName(thread.getStructureMembers()) for thread in threads]
        return ", ".join(names)

def readList(structure, type):
    # Read a circular linked list of threads
    thisBlock = structure
    headAddr = structure.getLocationAddress().getLinearAddress()
    blocks = []
    if headAddr == 0:
        return blocks

    reachedEnd = False
    while not reachedEnd:
        members = thisBlock.getStructureMembers()
        nextptr = members[ListTypeNextPtrs[type]]
        blocks.append(thisBlock)
        thisBlock = nextptr.dereferencePointer()
        reachedEnd = addressExprsToLong(nextptr) == headAddr
    return blocks

def readListWithSymbols(structure, type, syms):
    # Read a circular linked list of threads, storing the resolved symbols of each
    # block in the given list.
    thisBlock = structure
    headAddr = structure.getLocationAddress().getLinearAddress()
    blocks = []
    if headAddr == 0:
        return blocks

    reachedEnd = False
    while not reachedEnd:
        members = thisBlock.getStructureMembers()
        nextptr = members[ListTypeNextPtrs[type]]
        blocks.append(thisBlock)
        thisBlock = nextptr.dereferencePointer()
        reachedEnd = addressExprsToLong(nextptr) == headAddr
        if not reachedEnd:
            syms.append(nextptr.resolveAddressAsString())
    return blocks

def listSymbolsExist(debugger, type):
    try:
        return debugger.evaluateExpression("("+ListTypeStructures[type]+"*)0x0")
    except:
        return False

def getListHead(debugger, type):
    return getGlobalPointer(debugger, ListTypePtrs[type], ListTypeStructures[type])

def getGlobalPointer(debugger, name, expected_type):
    result = debugger.evaluateExpression(name)
    result_type = result.getType()
    if result_type.isPointerType() and not result_type.getPointedAtType().isStructuredType():
        return result.dereferencePointer(expected_type + "**")
    return result

def make_reg_list(offset, size, *reg_names):
    result = [("%s" % reg_names[x], long(offset + x*size)) for x in xrange(len(reg_names))]
    return result

def make_reg_range(offset, size, prefix, start, count):
    result = [("%s%d" % (prefix, start+x), long(offset + x*size)) for x in xrange(0, count)]
    return result
