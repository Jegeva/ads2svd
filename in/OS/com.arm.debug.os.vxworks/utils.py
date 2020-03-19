# Copyright (C) 2015,2017 Arm Limited (or its affiliates). All rights reserved.

"""
Implementation of OS support for Wind River VxWorks RTOS
"""

from osapi import *
import ctypes

# Task state bits.
WIND_READY          = 0x00
WIND_SUSPEND        = 0x01
WIND_PEND           = 0x02
WIND_DELAY          = 0x04
WIND_DEAD           = 0x08
WIND_STOP           = 0x10
WIND_STATE_CHANGE   = 0x20
# Task state string mappings.
TASK_STATE_MAP = \
{
    WIND_READY                                       : "READY",
    WIND_DEAD                                        : "DEAD",
    WIND_SUSPEND                                     : "SUSPEND",
    WIND_SUSPEND | WIND_PEND                         : "PEND+S",
    WIND_SUSPEND | WIND_PEND | WIND_DELAY            : "PEND+S+T",
    WIND_SUSPEND | WIND_PEND | WIND_DELAY | WIND_STOP: "ST+P+T+S",
    WIND_SUSPEND | WIND_PEND |              WIND_STOP: "STOP+P+S",
    WIND_SUSPEND |             WIND_DELAY            : "DELAY+S",
    WIND_SUSPEND |             WIND_DELAY | WIND_STOP: "STOP+T+S",
    WIND_SUSPEND |                          WIND_STOP: "STOP+S",
                   WIND_PEND                         : "PEND",
                   WIND_PEND | WIND_DELAY            : "PEND+T",
                   WIND_PEND | WIND_DELAY | WIND_STOP: "STOP+P+T",
                   WIND_PEND |              WIND_STOP: "STOP+P",
                               WIND_DELAY            : "DELAY",
                               WIND_DELAY | WIND_STOP: "STOP+T",
                                            WIND_STOP: "STOP",
}

# Task option bits.
VX_USER_MODE            = 0x00000000
VX_SUPERVISOR_MODE      = 0x00000001
VX_UNBREAKABLE          = 0x00000002
VX_DEALLOC_STACK        = 0x00000004
VX_STDIO                = 0x00000010
VX_ADA_DEBUG            = 0x00000020
VX_FORTRAN              = 0x00000040
VX_PRIVATE_ENV          = 0x00000080
VX_NO_STACK_FILL        = 0x00000100
VX_PRIVATE_CWD          = 0x00000200
VX_DEALLOC_EXC_STACK    = 0x00001000
VX_NO_STACK_PROTECT     = 0x00004000
VX_DEALLOC_TCB          = 0x00008000
VX_PRIVATE_UMASK        = 0x00008000
VX_FP_TASK              = 0x01000000

def getTaskState( tcbMembers ):
    return getTaskStatusText(tcbMembers["status"].readAsNumber())

def getTaskStatusText( state ):
    return TASK_STATE_MAP[state] if state in TASK_STATE_MAP else "UNKNOWN"

def readDLList(debugger, dlList, itemType, listOffset):
    """
    @brief  Reads a doubly-linked list. This is a core component of VxWorks
            whereby objects have lists embedded within them and, if one knows
            the type of object and the offset of the list within it, the
            full list of objects can be easily derived.
    @param  debugger    The DebugSession to resolve with.
    @param  dlList      ExpressionResult representing a DL_LIST type (or
                        equivalent).
    @param  itemType    ExpressionType of the type of object structure to read.
    @param  listOffset  int offset, in bytes, of the dlList within the object
                        structure being read.
    @return List of ExpressionResults of pointers to classType from the list.
    """
    nextPtr = dlList.getStructureMembers()['head']
    items = []
    while nextPtr.readAsNumber() != 0 :
        itemAddr = nextPtr.readAsAddress().addOffset(-listOffset)
        itemPtr = debugger.constructPointer(itemType, itemAddr)
        items.append(itemPtr)
        nextPtr = nextPtr.dereferencePointer().getStructureMembers()['next']
    return items

def readClassList(debugger, classIdStruct, classType):
    """
    @brief  Reads a *ClassId struct and returns all instances of the class as
            given by the object public and private lists.
    @param  debugger       The DebugSession to resolve with.
    @param  classIdStruct  String name of the global class id structure holding
                           the class id to read.
    @param  classType      String name of the type of class structures to read.
    @return List of ExpressionResults of pointers to classType as given by the
            class id structure.
    """
    if not debugger.symbolExists(classIdStruct):
        return []
    classId = debugger.evaluateExpression(classIdStruct)
    # The classId structure can either be a CLASS_ID type (OBJ_CLASS*) or an
    # OBJ_CLASS type directly. If it's a pointer, dereference it.
    if classId.getType().isPointerType():
        if not classId.readAsNumber():
            return []
        classId = classId.dereferencePointer()
    classIdMembers = classId.getStructureMembers()
    # Calculate the type and offset of the object items.
    classType = debugger.resolveType(classType)
    listOffset = getStructureMemberOffset(debugger, 'OBJ_CORE', 'classNode')
    # Read the private and public object lists.
    classList = []
    classList += readDLList(debugger, classIdMembers["objPrivList"], classType, listOffset)
    classList += readDLList(debugger, classIdMembers["objPubList"],  classType, listOffset)
    return classList

def readFIFOQueue(debugger, queue, objectType, listOffset):
    """
    @brief  Reads a FIFO Queue and returns a list of items within it.
    @param  debugger    The DebugSession to resolve with.
    @param  queue       ExpressionResult pointer to the queue to read.
    @param  objectType  String name of the type of structure making up the FIFO
                        queue.
    @param  listOffset  int offset, in bytes, of the queue within the object
                        structure being read.
    @return List of ExpressionResults of pointers to objectType from the list.
    """
    if queue.readAsNumber() == 0:
        return []
    head = queue.dereferencePointer('Q_FIFO_HEAD*').getStructureMembers()
    objectType = debugger.resolveType(objectType)
    return readDLList(debugger, head['list'], objectType, listOffset)

def readPrioQueue(debugger, queue, objectType, listOffset):
    """
    @brief  Reads a Priority Queue and returns a list of items within it.
    @param  debugger    The DebugSession to resolve with.
    @param  queue       ExpressionResult pointer to the queue to read.
    @param  objectType  String name of the type of structure making up the
                        priority queue.
    @param  listOffset  int offset, in bytes, of the queue within the object
                        structure being read.
    @return List of ExpressionResults of pointers to objectType from the list.
    """
    if queue.readAsNumber() == 0:
        return []
    head = queue.dereferencePointer('Q_PRI_HEAD*').getStructureMembers()
    objectType = debugger.resolveType(objectType)
    return readDLList(debugger, head['list'], objectType, listOffset)

def readTaskList(debugger):
    """
    @brief  Reads a list of all tasks.
    @param  debugger  The DebugSession to resolve with.
    @return List of ExpressionResults of pointers to windTcb objects.
    """
    return readClassList(debugger, 'taskClassId', 'windTcb')

def readSemaphoreList(debugger):
    """
    @brief  Reads a list of all semaphores.
    @param  debugger  The DebugSession to resolve with.
    @return List of ExpressionResults of pointers to semaphore objects.
    """
    return readClassList(debugger, 'semClassId', 'semaphore')

def readFileDescriptorList(debugger):
    """
    @brief  Reads a list of all file descriptors.
    @param  debugger  The DebugSession to resolve with.
    @return List of ExpressionResults of pointers to FD_ENTRY objects.
    """
    # fdClassId is defined to &fdClass.
    return readClassList(debugger, 'fdClass', 'FD_ENTRY')

def readDeviceList(debugger):
    """
    @brief  Reads a list of all devices.
    @param  debugger  The DebugSession to resolve with.
    @return List of ExpressionResults of pointers to DEV_HDR objects.
    """
    # This isn't a class object but just a simple global DL-list.
    deviceList = debugger.evaluateExpression('iosDvList')
    deviceType = debugger.resolveType('DEV_HDR')
    listOffset = getStructureMemberOffset(debugger, 'DEV_HDR', 'node')
    return readDLList(debugger, deviceList, deviceType, listOffset)

def readTaskFIFOQueue(debugger, queue):
    """
    @brief  Reads a FIFO queue, interpreting all nodes as pointers to tasks and
            returns an ordered list of them.
    @param  debugger  The DebugSession to resolve with.
    @param  queue     ExpressionResult pointer to the FIFO queue to read.
    @return List of ExpressionResults of pointers to windTcb.
    """
    listOffset = getStructureMemberOffset(debugger, 'windTcb', 'qNode')
    return readFIFOQueue(debugger, queue, 'windTcb', listOffset)

def readTaskPrioQueue(debugger, queue):
    """
    @brief  Reads a priority queue, interpreting all nodes as pointers to tasks
            and returns an ordered list of them.
    @param  debugger  The DebugSession to resolve with.
    @param  queue     ExpressionResult pointer to the priority queue to read.
    @return List of ExpressionResults of pointers to windTcb.
    """
    listOffset = getStructureMemberOffset(debugger, 'windTcb', 'qNode')
    return readPrioQueue(debugger, queue, 'windTcb', listOffset)

def readRTPList(debugger):
    """
    @brief  Reads a list of all active RTPs in the system.
    @param  debugger  The DebugSession to resolve with.
    @return List of tuples of RTP identifier and RTP structure (dictionary). The
            hierarchy of the processes will not be preserved or encoded in any
            way - the processes will be read depth-first from the kernel. The
            kernel process is always the first item and ID 0.
    """
    def _readRTPListRecursive(debugger, outList, rtpType, rtpListOffset, rtp):
        rtp = rtp.dereferencePointer().getStructureMembers()
        rtpId = rtp['rtpHandleId'].readAsNumber()
        # Add the RTP to the list.
        outList.append((rtpId, rtp))
        # Read the RTP's children and add them to the list as well.
        childRtps = readDLList(debugger, rtp['rtpChildList'], rtpType, rtpListOffset)
        for childRtp in childRtps:
            _readRTPListRecursive(debugger, outList, rtpType, rtpListOffset, childRtp)
    # Derive constants based on RTP structure.
    rtpType = debugger.resolveType('WIND_RTP')
    rtpListOffset = getStructureMemberOffset(debugger, 'WIND_RTP', 'rtpChildList')
    # All processes are children of the kernel and thus accessible by walking
    # its child hierarchy.
    kernelRtp = debugger.evaluateExpression('"kernelLib.c"::kernelId')
    outList = []
    _readRTPListRecursive(debugger, outList, rtpType, rtpListOffset, kernelRtp)
    return outList

def getCoreId(debugger, is_v8a):
    if is_v8a:
        return debugger.evaluateExpression('$MPIDR_EL1').readAsNumber() & 0xFF
    else:
        return debugger.evaluateExpression('$MPIDR.CPUID').readAsNumber()

def getTaskDelay(debugger, taskMembers, state):
    delay = 0
    if state == WIND_DELAY:
        tickNodeAddr = taskMembers[ "tickNode" ].getLocationAddress( ).getLinearAddress( )
        evalexp = "(Q_PRI_NODE*)" + str( tickNodeAddr )
        priNodePtr = debugger.evaluateExpression( evalexp )
        priNodeMembers = priNodePtr.dereferencePointer( ).getStructureMembers( )
        delay = priNodeMembers[ "key" ].readAsNumber( )
    return delay

def unsigned( n, bits ):
    return n & ((1 << bits) - 1)

def longToHex( n, bits ):
    if n is None:
        return None
    uint = unsigned( n, bits )
    fmts = '0x%%0%dX' % (bits // 4)
    return fmts % (uint)

def createYesNoTextCell( n ):
    """
    @brief  Converts a truthy object into a localised text cell.
    @param  n   An object to test (any Python object).
    @param  A localised text cell containing either a 'yes/no' type string based
            on the truth status of the given object, or an empty cell if n is
            None.
    """
    if n is None:
        return createLocalisedTextCell(None)
    return createLocalisedTextCell('misc.yes' if n else 'misc.no')

def getClassName(objCore, defaultName='<unset>'):
    # The task creation flow looks like:
    # * Fill in non-optional task data members (address, status, etc).
    # * Zero-out the remaining (optional) members (including objCore struct).
    # * Add to the task list (objPrivList).
    # * Fill in optional members (objCore struct (less .name), system viewer,
    #   windSmpInfo, credentials, objCore.name).
    # * Increment "taskLib.c"::taskActivityCount
    # * Call create hooks if configured (which do things like co-processor setup
    #   etc).
    # * Resize stack space if necessary.
    # Thus, there is no single definitive point after the task has been added to
    # objPrivList to tell whether the initialisation has actually truly
    # finished. As a result we must deal with all optional state potentially
    # being NULL/zero (including the name).
    name = objCore.getStructureMembers()["name"]
    if name.readAsNumber() == 0:
        return defaultName
    return name.readAsNullTerminatedString(1024)
