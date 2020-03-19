################################################################################
#
# Copyright (C) 2014,2017 Arm Limited (or its affiliates). All rights reserved.
#
#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

from osapi import *
from utils import *

class NuSpinlocks(Table):

    def __init__(self):
        cid = "spinlocks"
        fields = [createPrimaryField(cid, "cb", ADDRESS)]
        fields.append(createField(cid, "id", DECIMAL))
        fields.append(createField(cid, "lock_count", DECIMAL))
        fields.append(createField(cid, "owner_thread", ADDRESS))

        fields.append(createField(cid, "lock_flag", DECIMAL))
        fields.append(createField(cid, "lock_flag2", DECIMAL))
        fields.append(createField(cid, "last_owner_cpu_id", DECIMAL))
        fields.append(createField(cid, "last_released_cpu_id", DECIMAL))
        fields.append(createField(cid, "own_count", DECIMAL))
        fields.append(createField(cid, "max_spin_count", DECIMAL))

        Table.__init__(self, cid, fields)

    def readRecord(self, scbPtr, debugSession):
        cells = [createAddressCell(scbPtr.readAsAddress())]
        scbMembers = scbPtr.dereferencePointer().getStructureMembers()

        addIfPresent(cells, scbMembers, "sl_id", intFun)
        addIfPresent(cells, scbMembers, "sl_lock_count", intFun)
        addIfPresent(cells, scbMembers, "sl_thread_ptr", addrFun)

        slLockMembers = scbMembers.get("sl_lock").getStructureMembers()
        addIfPresent(cells, slLockMembers, "lock_flag", intFun)
        addIfPresent(cells, slLockMembers, "lock_flag2", intFun)
        addIfPresent(cells, slLockMembers, "last_owner_cpu_id", intFun)
        addIfPresent(cells, slLockMembers, "last_released_cpu_id", intFun)
        addIfPresent(cells, slLockMembers, "own_count", intFun)
        addIfPresent(cells, slLockMembers, "max_spin_count", intFun)

        return self.createRecord(cells)

    def getRecords(self, debugSession):
        spinlockIter = listIter(debugSession, getFirstSpinlock, getNextSpinlock)
        return [self.readRecord(spinlockPtr, debugSession) for spinlockPtr in spinlockIter]
