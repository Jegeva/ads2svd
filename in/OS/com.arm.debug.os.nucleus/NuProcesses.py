################################################################################
#
# Copyright (C) 2014,2017 Arm Limited (or its affiliates). All rights reserved.
#
#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

from osapi import *
from utils import *

class NuProcesses( Table ):

    def __init__( self ):
        cid = "proc"
        fields = [createPrimaryField(cid, "cb", ADDRESS)]
        fields.append( createField(cid, "name", TEXT ))

        fields.append(createField(cid, "id", DECIMAL))
        fields.append(createField(cid, "root_task", ADDRESS))
        fields.append(createField(cid, "total_tasks", DECIMAL))
        fields.append(createField(cid, "last_sched_task", ADDRESS))
        fields.append(createField(cid, "load_addr", ADDRESS))
        fields.append(createField(cid, "exit_code", DECIMAL))

        fields.append(createField(cid, "state", TEXT))
        fields.append(createField(cid, "pool", ADDRESS))

        #These can be ifdeffed out
        fields.append(createField(cid, "translation", ADDRESS))
        fields.append(createField(cid, "owned_regions", ADDRESS))
        fields.append(createField(cid, "owned_total", DECIMAL))
        fields.append(createField(cid, "prev_state", TEXT))

        fields.append(createField(cid, "semaphore", ADDRESS))
        fields.append(createField(cid, "queue", ADDRESS))
        fields.append(createField(cid, "timer_queue", ADDRESS))

        fields.append(createField(cid, "buffer", ADDRESS))
        fields.append(createField(cid, "sym_using", ADDRESS))
        fields.append(createField(cid, "sym_using_count", DECIMAL))
        fields.append(createField(cid, "sym_used_count", DECIMAL))
        fields.append(createField(cid, "abort_flag", DECIMAL))
        fields.append(createField(cid, "exit_protect", DECIMAL))

        fields.append(createField(cid, "access", DECIMAL))
        fields.append(createField(cid, "registers", ADDRESS))

        Table.__init__( self, cid, fields )

    def readRecord(self, cbPtr, debugSession):
        cbMembers = cbPtr.dereferencePointer().getStructureMembers()
        #This should always be present
        imageInfoPtr = cbMembers.get("image_info")
        imageInfoMembers = []
        if imageInfoPtr.readAsNumber != 0 :
            dereffed = imageInfoPtr.dereferencePointer()
            imageInfoMembers = dereffed.getStructureMembers()

        cells = [createAddressCell(cbPtr.readAsAddress())]
        addIfPresent(cells, imageInfoMembers, "name", strFun)
        addIfPresent(cells, cbMembers, "id", intFun)
        addIfPresent(cells, cbMembers, "root_task", addrFun)
        addIfPresent(cells, cbMembers, "total_tasks", intFun)
        addIfPresent(cells, cbMembers, "last_sched_task", addrFun)
        addIfPresent(cells, cbMembers, "load_addr", addrFun)
        addIfPresent(cells, cbMembers, "exit_code", intFun)
        addIfPresent(cells, cbMembers, "state", pStateFun)
        addIfPresent(cells, cbMembers, "pool", addrFun)

        #ifdef CFG_NU_OS_KERN_PROCESS_CORE_ENABLE
        addIfPresent(cells, cbMembers, "translation", addrFun)
        addIfPresent(cells, cbMembers, "owned_regions", addrFun)
        addIfPresent(cells, cbMembers, "owned_total", intFun)
        addIfPresent(cells, cbMembers, "prev_state", pStateFun)

        addIfPresent(cells, cbMembers, "semaphore", addrOfFun)
        addIfPresent(cells, cbMembers, "queue", addrOfFun)
        addIfPresent(cells, cbMembers, "timer_queue", addrFun)

        addIfPresent(cells, cbMembers, "buffer", addrOfFun)
        addIfPresent(cells, cbMembers, "sym_using", addrOfFun)
        addIfPresent(cells, cbMembers, "sym_using_count", intFun)
        addIfPresent(cells, cbMembers, "sym_used_count", intFun)
        addIfPresent(cells, cbMembers, "abort_flat", intFun)
        addIfPresent(cells, cbMembers, "exit_protect", intFun)

        addIfPresent(cells, cbMembers, "access", intFun)
        addIfPresent(cells, cbMembers, "registers", addrOfFun)

        return self.createRecord(cells)

    def getRecords( self, debugSession ):
        procIter = listIter(debugSession, getFirstProcess, getNextProcess)
        result = [self.readRecord(procPtr, debugSession) for procPtr in procIter]
        return result;

def pStateFun(val) :
    return enumFun(PROC_STATES, val)
