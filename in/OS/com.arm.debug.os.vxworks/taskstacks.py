# Copyright (C) 2015,2017 Arm Limited (or its affiliates). All rights reserved.

"""
Implementation of OS support for Wind River VxWorks RTOS
"""

from osapi import *
from utils import *

class TaskStacks( Table ):

    STACK_WATERMARK_PATTERN = 0xEEEEEEEE

    def __init__( self ):

        cid = "tskstks"

        fields = []
        fields.append(createPrimaryField(cid, "tid", ADDRESS))
        fields.append(createField(cid, "name", TEXT))
        fields.append(createField(cid, "type", TEXT))
        fields.append(createField(cid, "base", ADDRESS))
        fields.append(createField(cid, "end", ADDRESS))
        fields.append(createField(cid, "size", DECIMAL))

        Table.__init__(self, cid, fields)

    def createTaskRecords(self, taskPtr, debugSession):

        tcbMembers = taskPtr.dereferencePointer().getStructureMembers()

        taskAddr = taskPtr.readAsAddress()
        taskName = getClassName(tcbMembers['objCore'])
        regBank = tcbMembers['regs'].getStructureMembers()
        if 'sp' in regBank:
            stackPtr = regBank['sp'].readAsAddress()
        else:
            stackPtr = regBank['r'].getArrayElements()[13].readAsAddress()

        # Extract execution stack details.
        exeStackBase = tcbMembers["pStackBase"].readAsAddress()
        exeStackEnd = tcbMembers["pStackEnd"].readAsAddress()
        exeStackSize = exeStackBase.getLinearAddress() - exeStackEnd.getLinearAddress()

        # Extract exception stack details.
        excStackBase = tcbMembers["pExcStackBase"].readAsAddress()
        excStackEnd = tcbMembers["pExcStackEnd"].readAsAddress()
        excStackSize = excStackBase.getLinearAddress() - excStackEnd.getLinearAddress()

        # Work out which stack (if any) the SP falls in.
        spInExeStack = addrInStack(stackPtr, exeStackBase, exeStackEnd)
        spInExcStack = addrInStack(stackPtr, excStackBase, excStackEnd)
        exeStackType = 'Execution' + ('*' if spInExeStack else '')
        excStackType = 'Exception' + ('*' if spInExcStack else '')

        # Build execution stack cells.
        exeCells = []
        exeCells.append(createAddressCell(taskAddr))
        exeCells.append(createTextCell(taskName))
        exeCells.append(createTextCell(exeStackType))
        exeCells.append(createAddressCell(exeStackBase))
        exeCells.append(createAddressCell(exeStackEnd))
        exeCells.append(createNumberCell(exeStackSize))

        # Build exception stack cells.
        excCells = []
        excCells.append(createAddressCell(taskAddr))
        excCells.append(createTextCell(taskName))
        excCells.append(createTextCell(excStackType))
        excCells.append(createAddressCell(excStackBase))
        excCells.append(createAddressCell(excStackEnd))
        excCells.append(createNumberCell(excStackSize))

        return [self.createRecord(exeCells), self.createRecord(excCells)]

    def getRecords( self, debugSession ):
        tcbPtrList = readTaskList( debugSession )
        records = []
        for taskPtr in tcbPtrList:
            records += self.createTaskRecords( taskPtr, debugSession )
        return records

def addrInStack(addr, base, end):
    addr_la = addr.getLinearAddress()
    base_la = base.getLinearAddress()
    end_la  =  end.getLinearAddress()
    return addr_la <= base_la and addr_la > end_la
