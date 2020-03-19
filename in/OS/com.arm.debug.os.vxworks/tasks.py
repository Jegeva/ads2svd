# Copyright (C) 2015,2017 Arm Limited (or its affiliates). All rights reserved.

"""
Implementation of OS support for Wind River VxWorks RTOS
"""

from osapi import *
from utils import *

class Tasks( Table ):

    def __init__( self ):

        cid = "tasks"

        fields = [ createPrimaryField( cid, "tid", ADDRESS ) ]

        fields.append( createField( cid, "name", TEXT ) )
        fields.append( createField( cid, "entry", ADDRESS ) )
        fields.append( createField( cid, "priority", TEXT ) )
        fields.append( createField( cid, "status", TEXT ) )
        fields.append( createField( cid, "errno", DECIMAL ) )
        fields.append( createField( cid, "delay", DECIMAL ) )
        fields.append( createField( cid, "exccnt", DECIMAL ) )
        fields.append( createField( cid, "loccnt", DECIMAL ) )
        fields.append( createField( cid, "tslice", DECIMAL ) )
        fields.append( createField( cid, "ticks", DECIMAL ) )
        fields.append( createField( cid, "tislice", DECIMAL ) )

        Table.__init__( self, cid, fields )

    def readRecord(self, taskPtr, debugSession):

        tcbMembers = taskPtr.dereferencePointer().getStructureMembers()

        taskAddr = taskPtr.readAsAddress()
        name = getClassName(tcbMembers['objCore'])
        entryAddr = tcbMembers["entry"].readAsAddress()
        priorityCur = tcbMembers["priority"].readAsNumber()
        priorityNormal = tcbMembers["priNormal"].readAsNumber()
        priorityStr = "%d/%d" % (priorityCur, priorityNormal)
        status = tcbMembers["status"].readAsNumber()
        statusStr = "%s (0x%X)" % (getTaskStatusText(status), status)
        errorNum = tcbMembers["errorStatus"].readAsNumber()
        taskDelay = getTaskDelay(tcbMembers, status, debugSession)
        execCount = tcbMembers["excCnt"].readAsNumber()
        lockCount = tcbMembers["lockCnt"].readAsNumber()
        timeSlice = tcbMembers["tslice"].readAsNumber()
        taskTicks = tcbMembers["taskTicks"].readAsNumber()
        taskIncTicks = tcbMembers["taskIncTicks"].readAsNumber()

        cells = []
        cells.append(createAddressCell(taskAddr))
        cells.append(createTextCell(name))
        cells.append(createAddressCell(entryAddr))
        cells.append(createTextCell(priorityStr))
        cells.append(createTextCell(statusStr))
        cells.append(createNumberCell(errorNum))
        cells.append(createNumberCell(taskDelay))
        cells.append(createNumberCell(execCount))
        cells.append(createNumberCell(lockCount))
        cells.append(createNumberCell(timeSlice))
        cells.append(createNumberCell(taskTicks))
        cells.append(createNumberCell(taskIncTicks))

        return self.createRecord(cells)

    def getRecords( self, debugSession ):
        tcbPtrList = readTaskList( debugSession )
        return [ self.readRecord( taskPtr, debugSession ) for taskPtr in tcbPtrList ]

