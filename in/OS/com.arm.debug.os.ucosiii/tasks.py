# Copyright (C) 2013-2014,2017 Arm Limited (or its affiliates). All rights reserved.

from utils import *
from osapi import *
from globs import *

class Tasks(Table):

    CONTROL_BLOCK_TYPE = 0

    # Task display fields are generated for most of the fields of TCB, with exceptions of the
    # Next/Prev pointers, and the following values which may not be in scope:
    # PendDataEntries, PendDataTblPtr, RegTbl
    # and the following optional entries that are depends on user setting which the kernel does not
    # keep in parameters.

    # TCB:
    #    CPU_STK *StkPtr;
    #    void *ExtPtr;
    #    CPU_STK *StkLimitPtr;
    #    OS_TCB *NextPtr;
    #    OS_TCB *PrevPtr;
    #    OS_TCB *TickNextPtr;
    #    OS_TCB *TickPrevPtr;
    #    OS_TICK_SPOKE *TickSpokePtr;
    #    OS_CHAR *NamePtr;
    #    CPU_STK *StkBasePtr;
    #    OS_TASK_PTR TaskEntryAddr;
    #    void *TaskEntryArg;
    #    OS_PEND_DATA *PendDataTblPtr;
    #    OS_STATE PendOn;
    #    OS_STATUS PendStatus;
    #    OS_STATE TaskState;
    #    OS_PRIO Prio;
    #    CPU_STK_SIZE StkSize;
    #    OS_OPT Opt;
    #    OS_OBJ_QTY PendDataEntries;
    #    CPU_TS TS;
    #    OS_SEM_CTR SemCtr;
    #    OS_TICK TickCtrPrev;
    #    OS_TICK TickCtrMatch;
    #    OS_TICK TickRemain;
    #    OS_TICK TimeQuanta;
    #    OS_TICK TimeQuantaCtr;
    #    void *MsgPtr;
    #    OS_MSG_SIZE MsgSize;
    #    OS_MSG_Q MsgQ;
    #    CPU_TS MsgQPendTime;
    #    CPU_TS MsgQPendTimeMax;
    #    OS_REG RegTbl[OS_TASK_REG_TBL_SIZE];
    #    OS_FLAGS FlagsPend;
    #    OS_FLAGS FlagsRdy;
    #    OS_OPT FlagsOpt;
    #    OS_NESTING_CTR SuspendCtr;
    #    OS_CPU_USAGE CPUUsage;
    #    OS_CTX_SW_CTR CtxSwCtr;
    #    CPU_TS CyclesDelta;
    #    CPU_TS CyclesStart;
    #    OS_CYCLES CyclesTotal;
    #    OS_CYCLES CyclesTotalPrev;
    #    CPU_TS SemPendTime;
    #    CPU_TS SemPendTimeMax;
    #    CPU_STK_SIZE StkUsed;
    #    CPU_STK_SIZE StkFree;
    #    CPU_TS IntDisTimeMax;
    #    CPU SchedLockTimeMax;    # OS_CFG_SCHED_LOCK_TIME_MEAS_EN is not kept as readable expr from debugger
    #    OS_TCB DbgNextPtr;
    #    OS_TCB DbgPrevPtr;
    #    CPU_CHAR DbgNamePtr;
    def __init__(self):
        id = "tasks"
        fields = [createPrimaryField(id, "tcb_addr", TEXT),
                  createField(id, "name", TEXT),
                  createField(id, "cpu_stk_ptr", TEXT),
                  createField(id, "stk_ext_ptr", TEXT),
                  createField(id, "stk_lmt_ptr", TEXT),
                  createField(id, "stk_base_ptr", TEXT),
                  createField(id, "stk_used", TEXT),
                  createField(id, "stk_free", TEXT),
                  createField(id, "stk_size", DECIMAL),
                  createField(id, "priority", DECIMAL),
                  createField(id, "state", TEXT),
                  createField(id, "pend_on", TEXT),
                  createField(id, "cxw_ctr", TEXT),
                  createField(id, "tick_spoke_ptr", TEXT),
                  createField(id, "tick_ctr_match", TEXT),
                  createField(id, "tick_remain", HEXADECIMAL),
                  createField(id, "task_entry_addr", TEXT),
                  createField(id, "task_entry_arg", TEXT),
                  createField(id, "pend_status", TEXT),
                  createField(id, "opt", TEXT),
                  createField(id, "ts", DECIMAL),
                  createField(id, "time_quanta", DECIMAL),
                  createField(id, "time_quanta_ctr", DECIMAL),
                  createField(id, "msg_q", TEXT),
                  createField(id, "msg_ptr", TEXT),
                  createField(id, "msg_size", TEXT),
                  createField(id, "msg_q_pending", TEXT),
                  createField(id, "msg_q_pending_max", TEXT),
                  createField(id, "flags_pend", TEXT),
                  createField(id, "flags_rdy", TEXT),
                  createField(id, "flags_opt", TEXT),
                  createField(id, "cpu_usage", TEXT), #this is a runtime value, not an accumulate record. hence no interests to display.
                  createField(id, "cycles_delta", TEXT),
                  createField(id, "cycles_start", TEXT),
                  createField(id, "cycles_total", TEXT),
                  createField(id, "sem_pend", TEXT),
                  createField(id, "sem_pend_max", TEXT),
                  createField(id, "suspend_ctr", TEXT),
                  createField(id, "sem_ctr", DECIMAL),
                  createField(id, "TaskID", TEXT)
                 ]
        Table.__init__(self, id, fields)

    def readTask(self, id, members, debugger):
        tickSpokePtrName = getMemberName( OS_TCB_TICK_LIST_PTR, members )
        tickCtrMatch = "N/A"
        tickCtrMatchName = getMemberName( OS_TCB_TICK_MATCH, members )
        if tickCtrMatchName:
            tickCtrMatch = str( members[ tickCtrMatchName ].readAsNumber( ) )
        taskId = "N/A"
        taskIdName = getMemberName( OS_TCB_TASK_ID, members )
        if taskIdName:
            taskId = members[ taskIdName ].readAsNumber( )
        cells = [
                 createTextCell(id),
                 createTextCell(members["NamePtr"].readAsNullTerminatedString()),
                 createTextCell(members["StkPtr"].readAsAddress().toString()),
                 createTextCell(members["ExtPtr"].readAsAddress().toString()),
                 createTextCell(members["StkLimitPtr"].readAsAddress().toString()),
                 createTextCell(members["StkBasePtr"].readAsAddress().toString()),
                 createTextCell(getOptionalValues("OSDbg_StatTaskStkChkEn", members, "StkUsed", "number", debugger)),
                 createTextCell(getOptionalValues("OSDbg_StatTaskStkChkEn", members, "StkFree", "number", debugger)),
                 createNumberCell(members["StkSize"].readAsNumber()),
                 createNumberCell(members["Prio"].readAsNumber()),
                 createTextCell(getBitOptNames(TASK_STATE_NAMES, members.get("TaskState").readAsNumber())),
                 createTextCell(getBitOptNames(PENDING_STATE_NAMES, members.get("PendOn").readAsNumber())),
                 createTextCell(getOptionalValues("OSDbg_TaskProfileEn", members, "CtxSwCtr", "number", debugger)),
                 createTextCell(members[tickSpokePtrName].readAsAddress().toString()),
                 createTextCell( tickCtrMatch ),
                 createNumberCell(members["TickRemain"].readAsNumber()),
                 createTextCell(members["TaskEntryAddr"].readAsAddress().toString()),
                 createTextCell(members["TaskEntryArg"].readAsAddress().toString()),
                 createTextCell(getBitOptNames(PENDING_STATUS_NAMES, members.get("PendStatus").readAsNumber())),
                 createTextCell(getBitOptNames(TASK_OPTIONS_NAMES, members.get("Opt").readAsNumber())),
                 createNumberCell(members["TS"].readAsNumber()),
                 createNumberCell(members["TimeQuanta"].readAsNumber()),
                 createNumberCell(members["TimeQuantaCtr"].readAsNumber()),
                 createTextCell(getMessageValues(members["MsgQ"], "address", debugger)),
                 createTextCell(getMessageValues(members["MsgPtr"], "address", debugger)),
                 createTextCell(getMessageValues(members["MsgSize"], "number", debugger)),
                 createTextCell(getMessageValues(members["MsgQPendTime"], "number", debugger)),
                 createTextCell(getMessageValues(members["MsgQPendTimeMax"], "number", debugger)),
                 createTextCell(getOptionalValues("OSDbg_FlagEn", members, "FlagsPend", "number", debugger)),
                 createTextCell(getOptionalValues("OSDbg_FlagEn", members, "FlagsRdy", "number", debugger)),
                 createTextCell(getOptionalValues("OSDbg_FlagEn", members, "FlagsOpt", "enum", debugger)),
                 createTextCell(getOptionalValues("OSDbg_TaskProfileEn", members, "CPUUsage", "usage", debugger)), #cpu usage
                 createTextCell(getOptionalValues("OSDbg_TaskProfileEn", members, "CyclesDelta", "number", debugger)),
                 createTextCell(getOptionalValues("OSDbg_TaskProfileEn", members, "CyclesStart", "number", debugger)),
                 createTextCell(getOptionalValues("OSDbg_TaskProfileEn", members, "CyclesTotal", "number", debugger)),
                 createTextCell(getOptionalValues("OSDbg_TaskProfileEn", members, "SemPendTime", "number", debugger)),
                 createTextCell(getOptionalValues("OSDbg_TaskProfileEn", members, "SemPendTimeMax", "number", debugger)),
                 createTextCell(getOptionalValues("OSDbg_TaskSuspendEn", members, "SuspendCtr", "number", debugger)),
                 createNumberCell(members["SemCtr"].readAsNumber()),
                 createTextCell(taskId)
                ]
        print cells
                 #createTextCell(getPendingValues("PendDataTblPtr", members, debugger))]
        return self.createRecord(cells)

    def getRecords(self, debugSession):
        if debugSession.evaluateExpression("OSRunning").readAsNumber() == 1:

            records = []

            osTaskDbgListPtr = debugSession.evaluateExpression( "OSTaskDbgListPtr" )
            head = osTaskDbgListPtr
            while head.readAsNumber( ) != 0:
                id = head.readAsAddress( ).toString( )
                print id
                members = head.dereferencePointer( ).getStructureMembers( )
                records.append( self.readTask( id, members, debugSession ) )
                head = head.dereferencePointer( ).getStructureMembers( )['DbgNextPtr']

            return records

