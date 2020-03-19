# Copyright (C) 2013,2015,2017,2018 Arm Limited (or its affiliates). All rights reserved.

from osapi import *
import cfg
from rtx_member_names import MEMBER_NAME_BY_VERSION
from rtxIterator import *


def getVersion():
    return cfg.rtxInfo.getVersion()

def setVersion(version):
    cfg.rtxInfo = version

def isVersion4():
    return cfg.rtxInfo.getVersion() == "V4"

def isVersion5():
    return cfg.rtxInfo.getVersion() == "V5"

def getKernelState(dbg):
    return cfg.rtxInfo.getKernelState(dbg)

def getControlBlockIdentifiers():
    return cfg.rtxInfo.getControlBlockIdentifiers()

def getControlBlockId(cbName):
    return getControlBlockIdentifiers()[cbName]

def getControlBlockName(cbId):
    return next((name for (name, id) in getControlBlockIdentifiers().items() if id == cbId), None)

def getControlBlockIdentifierFromPointer(cbPtr):
    return getControlBlockName(getMember(getPtrMemBers(cbPtr),"id").readAsNumber())

def isThreadControlBlock(cbPtr):
    return getControlBlockIdentifiers()['Thread'] == getMember(getPtrMemBers(cbPtr), "id").readAsNumber()

def getCType(cbName):
    return cfg.rtxInfo.getCType(cbName)

def getCurrentTask(dbg):
    return cfg.rtxInfo.getCurrentTask(dbg)

def getTaskIdType():
    return cfg.rtxInfo.getTaskIdType()

def getActiveTasks(dbg):
    return cfg.rtxInfo.getActiveTasks(dbg)

def getTaskId(tcbPtr, members):
    return cfg.rtxInfo.getTaskId(tcbPtr, members)

def getDisplayableTaskId(tcbPtr, members):
    return cfg.rtxInfo.getDisplayableTaskId(tcbPtr, members)

def makeNumberCell(members, name):
    return createNumberCell(getMember(members, name).readAsNumber() if (getMemberName(name) in members) else None)

def makeAddressCell(members, name):
    return createAddressCell(getMember(members, name).readAsAddress())

def makeAddressOfCell(members, name):
    return createAddressCell(getMember(members, name).getLocationAddress())

def makeNameCell(members, name):
    return createTextCell(getSimpleName(members, name))

def makeTaskIdCell(tcbPtr, members):
    return createTextCell(cfg.rtxInfo.getDisplayableTaskId(tcbPtr, members))

def makeTaskCell(members, name):
    tcbPtr = getMember(members, name)

    return makeTaskIdCell(tcbPtr, tcbPtr.dereferencePointer().getStructureMembers())

def makeStateCell(members):
    return createTextCell(getTaskState(getMember(members,"state").readAsNumber(), members))

def makeTaskWaitersCell(members, name):
    tcbPtr = getMember(members,name)
    result = []

    while nonNullPtr(tcbPtr):
        members = getPtrMemBers(tcbPtr)
        result.append(str(cfg.rtxInfo.getDisplayableTaskId(tcbPtr, members)))
        tcbPtr = getMember(members, "thread_next")

    return createTextCell(', '.join(result))

def getSimpleName(members, name):
    member = getMember(members, name)
    location = member.resolveAddressAsString()
    index = location.find("+")
    if(index != -1):
        location = str(location)[:index]

    return location

#The table classes should only use the field names defined in RTX5
#When the image is from RTX4, the RTX5 field names are mapped to the corresponding names in RTX4
def getMemberName(name):
    return cfg.rtxInfo.getMemberName(name)

def getMember(members, name):
    return members[getMemberName(name)]

def getTaskState(stateId, members=None):
    return cfg.rtxInfo.getTaskState(stateId, members)

def dereferenceThreadPointer(tcbPtr):
    return tcbPtr.dereferencePointer(getCType("Thread"))

def isStackOverflowCheckEnabled(dbg):
    return cfg.rtxInfo.isStackOverflowCheckEnabled(dbg)

def isStackUsageWatermarkEnabled(dbg):
    return cfg.rtxInfo.isStackUsageWatermarkEnabled(dbg)

def getStackSize(members, dbg):
    return cfg.rtxInfo.getStackSize(members, dbg)

def nextPtr(ptr, nextMemberName):
    return getMember(getPtrMemBers(ptr), nextMemberName)

def getPtrMemBers(ptr, type=None):
    if type:
        return ptr.dereferencePointer(type).getStructureMembers()
    else:
        return ptr.dereferencePointer().getStructureMembers()

def isNullPtr(ptr):
    return ptr.readAsNumber() == 0

def nonNullPtr(ptr):
    return ptr.readAsNumber() != 0

# turn int/long to hex without the irritating "L" added to the end for longs
def toHex(x):
    return "0x%X" % x

# Base class for task control block structures
class RtxTable(Table):

    def __init__(self, id, fields):
        Table.__init__(self, id, fields)

    def getRecords(self, dbg):
        return list(map(lambda cbPtr: self.createRecordFromControlBlock(cbPtr, dbg), self.getControlBlocks(dbg)))

    def getControlBlocks(self, dbg):
        return getActiveTasks(dbg)

    def createRecordFromControlBlock(self, cbPtr, dbg):
        raise NotImplementedError


class RtxInterTaskCommTable(RtxTable):

    def __init__(self, id, fields, functions, tcbType):
        RtxTable.__init__(self, id, fields)
        self.functions = functions
        self.tcbType   = tcbType

    def getRecords(self, dbg):
        records = []
        for tcbPtr in self.getControlBlocks(dbg):
            if nonNullPtr(tcbPtr):

                threadPrev = getMember(dereferenceThreadPointer(tcbPtr).getStructureMembers(),"thread_prev")

                if nonNullPtr(threadPrev):
                    cells = self.createRecordFromControlBlock(threadPrev, dbg)

                    if cells:
                        records.append(self.createRecord(cells))

        return records

    def createRecordFromControlBlock(self, threadPrev, dbg):
        members = threadPrev.dereferencePointer(getCType(self.tcbType)).getStructureMembers()

        if (getMember(members,"id").readAsNumber() == getControlBlockId(self.tcbType)):
            return [function(members, threadPrev) for function in self.functions]

        return []
