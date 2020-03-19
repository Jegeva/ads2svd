# Copyright (C) 2017 Arm Limited (or its affiliates). All rights reserved.

"""
Implementation of OS support for Wind River VxWorks RTOS
"""

from osapi import *
from utils import *

# Matches the SEM_TYPE enum from semLibCommon.h
_SEM_TYPE = {
        0: 'sem.type.binary',
        1: 'sem.type.mutex',
        2: 'sem.type.counting',
        3: 'sem.type.rw',
    }
# Semaphore option definitions from semLibCommon.h
_SEM_Q_FIFO    = 0x00
_SEM_Q_PRIO    = 0x01
_SEM_DEL_SAFE  = 0x04
_SEM_INV_SAFE  = 0x08
_SEM_ERR_NOTIF = 0x10
_SEM_INTERRUPT = 0x20

class Semaphores(Table):

    def __init__(self):

        cid = "sem"

        fields = [ createPrimaryField( cid, "semid", ADDRESS ) ]

        fields.append( createField( cid, "type", TEXT ) )
        fields.append( createField( cid, "qtype", TEXT ) )
        fields.append( createField( cid, "qsize", DECIMAL ) )
        fields.append( createField( cid, "count", DECIMAL ) )
        fields.append( createField( cid, "full", TEXT ) )
        fields.append( createField( cid, "owner", TEXT ) )
        fields.append( createField( cid, "delsafe", TEXT ) )
        fields.append( createField( cid, "invsafe", TEXT ) )
        fields.append( createField( cid, "errnotify", TEXT ) )
        fields.append( createField( cid, "interrupt", TEXT ) )

        Table.__init__( self, cid, fields )

    def readRecord(self, debugSession, semPtr, is64Bit):
        sem = semPtr.dereferencePointer().getStructureMembers()

        semAddr = semPtr.readAsAddress()
        semType = getSemType(debugSession, sem['semType'])

        # Parse options.
        options = sem['options'].readAsNumber()
        prioQueue = options & _SEM_Q_PRIO
        delSafe   = options & _SEM_DEL_SAFE if semType == 'sem.type.mutex' else None
        invSafe   = options & _SEM_INV_SAFE if semType == 'sem.type.mutex' and prioQueue else None
        errNotify = options & _SEM_ERR_NOTIF
        interrupt = options & _SEM_INTERRUPT

        # Parse queue.
        qType = 'sem.qtype.prio' if prioQueue else 'sem.qtype.fifo'
        qPtr = debugSession.constructPointer(debugSession.resolveType('Q_HEAD'),
                                             sem['qHead'].getLocationAddress())
        if prioQueue:
            queue = readTaskPrioQueue(debugSession, qPtr)
        else:
            queue = readTaskFIFOQueue(debugSession, qPtr)
        qSize = len(queue)

        # Parse state.
        count = None
        full = None
        owner = None
        if semType == 'sem.type.binary':
            full = sem['state'].getStructureMembers()['owner'].readAsNumber() == 0
        elif semType == 'sem.type.mutex':
            ownerER = sem['state'].getStructureMembers()['owner']
            if ownerER.readAsNumber() != 0:
                # The final bit of the TCB address is used to indicate whether the task is queued.
                owner = ownerER.readAsNumber() & ~0x1
        elif semType == 'sem.type.counting':
            count = sem['state'].getStructureMembers()['count'].readAsNumber()
        elif semType == 'sem.type.rw':
            ownerER = sem['state'].getStructureMembers()['owner']
            if ownerER.readAsNumber() != 0:
                # The final bit of the TCB address is used to indicate whether the task is queued.
                owner = ownerER.readAsNumber() & ~0x1

        cells = []
        cells.append(createAddressCell(semAddr))
        cells.append(createLocalisedTextCell(semType))
        cells.append(createLocalisedTextCell(qType))
        cells.append(createNumberCell(qSize))
        cells.append(createNumberCell(count))
        cells.append(createYesNoTextCell(full))
        cells.append(createTextCell(longToHex(owner, 64 if is64Bit else 32)))
        cells.append(createYesNoTextCell(delSafe))
        cells.append(createYesNoTextCell(invSafe))
        cells.append(createYesNoTextCell(errNotify))
        cells.append(createYesNoTextCell(interrupt))

        return self.createRecord( cells )

    def getRecords(self, debugSession):
        semPtrList = readSemaphoreList(debugSession)
        is64Bit = debugSession.evaluateExpression("sizeof $PC").readAsNumber() == 8
        return [ self.readRecord(debugSession, semPtr, is64Bit) for semPtr in semPtrList ]

def getSemType(debugger, semTypeId):
    # Ideally we could cast to SEM_TYPE and use readAsEnum, but for some reason
    # SEM_TYPE in the compiled code has been typedef'd to a uint8 - I assume as
    # some sort of optimisation. Instead we replicate the definition.
    id = semTypeId.readAsNumber()
    return _SEM_TYPE[id] if id in _SEM_TYPE else 'sem.type.custom'
