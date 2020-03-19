# Copyright (C) 2013-2014,2017 Arm Limited (or its affiliates). All rights reserved.

from osapi import *

class KernelData(Table):

    def __init__(self):
        id = "kernel"

        fields = [
                  createField(id, "item", TEXT),
                  createField(id, "value", TEXT),
                  createField(id, "desc", TEXT)
                  ]

        Table.__init__(self, id, fields)

    def readRecord(self, debugSession, expr, exprType):
        record = "N/A"
        if debugSession.symbolExists(expr):
            record = str(debugSession.evaluateExpression(expr).readAsNumber())

        return record

    def readReadyListRecord( self, debugSession, records ):
        osRdyList = "OSRdyList"
        if debugSession.symbolExists( osRdyList ):
            readyLists = debugSession.evaluateExpression( osRdyList ).getArrayElements( )
            level = len( readyLists )
            for prio in range(level):
                readyListEntry = readyLists[ prio ].getStructureMembers( )
                entry = str(readyListEntry[ "NbrEntries" ].readAsNumber( ) )
                item = osRdyList + str( prio )
                desc = "Number of ready tasks at priority " + str( prio )
                records.append( self.createRecord( [ createTextCell( item ), createTextCell( entry ), createTextCell( desc ) ] ) )
        return records

    def readTimerWheelRecords( self, debugSession, timer, records ):
        if debugSession.symbolExists( timer ):
            timerLists = debugSession.evaluateExpression( timer ).getArrayElements( )
            for entryNum in range( len( timerLists ) ):
                parameter = timer + "[" + str( entryNum ) + "]" + ".NbrEntries"
                parameterMax = timer + "[" + str( entryNum ) + "]" + ".NbrEntriesMax"
                timerEntry = timerLists[ entryNum ].getStructureMembers( )
                entry = str( timerEntry[ "NbrEntries" ].readAsNumber( ) )
                records.append( self.createRecord( [ createTextCell( parameter ), createTextCell( entry ), createTextCell( "Number of entries" ) ] ) )
                entryMax = str( timerEntry[ "NbrEntriesMax" ].readAsNumber( ) )
                records.append( self.createRecord( [ createTextCell( parameterMax ), createTextCell( entryMax ), createTextCell( "Maximum number of entries" ) ] ) )
        return records

    def getRecords(self, debug):
        records = []
        # kernel configuration
        records.append(self.createRecord([createTextCell("OSDbg_VersionNbr"), createTextCell(self.readRecord(debug, "OSDbg_VersionNbr", "number")),createTextCell("uCOS-III version")]))
        records.append(self.createRecord([createTextCell("OSDbg_SemEn"), createTextCell(self.readRecord(debug, "OSDbg_SemEn", "number")),createTextCell("Semaphores enabled")]))
        records.append(self.createRecord([createTextCell("OSDbg_SemPendAbortEn"), createTextCell(self.readRecord(debug, "OSDbg_SemPendAbortEn", "number")),createTextCell("Semaphore pending abort enable")]))
        records.append(self.createRecord([createTextCell("OSDbg_SemSetEn"), createTextCell(self.readRecord(debug, "OSDbg_SemSetEn", "number")),createTextCell("Semaphore set enable")]))
        records.append(self.createRecord([createTextCell("OSDbg_SemSize"), createTextCell(self.readRecord(debug, "OSDbg_SemSize", "number")),createTextCell("Size of semaphore")]))
        records.append(self.createRecord([createTextCell("OSDbg_StatTaskEn"), createTextCell(self.readRecord(debug, "OSDbg_StatTaskEn", "number")),createTextCell("Statistical task enable")]))
        records.append(self.createRecord([createTextCell("OSDbg_StatTaskStkChkEn"), createTextCell(self.readRecord(debug, "OSDbg_StatTaskStkChkEn", "number")),createTextCell("Statistical task stack check enable")]))
        records.append(self.createRecord([createTextCell("OSDbg_StkWidth"), createTextCell(self.readRecord(debug, "OSDbg_StkWidth", "number")),createTextCell("Stack width")]))
        records.append(self.createRecord([createTextCell("OSDbg_TCBSize"), createTextCell(self.readRecord(debug, "OSDbg_TCBSize", "number")),createTextCell("Size of TCB (Task Control Block)")]))
        records.append(self.createRecord([createTextCell("OSDbg_TaskChangePrioEn"), createTextCell(self.readRecord(debug, "OSDbg_TaskChangePrioEn", "number")),createTextCell("Task change priority enable")]))
        records.append(self.createRecord([createTextCell("OSDbg_TaskDelEn"), createTextCell(self.readRecord(debug, "OSDbg_TaskDelEn", "number")),createTextCell("Task delete enable")]))
        records.append(self.createRecord([createTextCell("OSDbg_TaskProfileEn"), createTextCell(self.readRecord(debug, "OSDbg_TaskProfileEn", "number")),createTextCell("Task profiling enable")]))
        records.append(self.createRecord([createTextCell("OSDbg_TaskQEn"), createTextCell(self.readRecord(debug, "OSDbg_TaskQEn", "number")),createTextCell("Task queue enable")]))
        records.append(self.createRecord([createTextCell("OSDbg_TaskQPendAbortEn"), createTextCell(self.readRecord(debug, "OSDbg_TaskQPendAbortEn", "number")),createTextCell("Task queue pending abort enable")]))
        records.append(self.createRecord([createTextCell("OSDbg_TaskRegTblSize"), createTextCell(self.readRecord(debug, "OSDbg_TaskRegTblSize", "number")),createTextCell("Task register table size")]))
        records.append(self.createRecord([createTextCell("OSDbg_TaskSemPendAbortEn"), createTextCell(self.readRecord(debug, "OSDbg_TaskSemPendAbortEn", "number")),createTextCell("Task semaphore pending abort enable")]))
        records.append(self.createRecord([createTextCell("OSDbg_TaskSuspendEn"), createTextCell(self.readRecord(debug, "OSDbg_TaskSuspendEn", "number")),createTextCell("Task suspend enable")]))
        records.append(self.createRecord([createTextCell("OSDbg_TickSpokeSize"), createTextCell(self.readRecord(debug, "OSDbg_TickSpokeSize", "number")),createTextCell("Tick spoke size")]))
        records.append(self.createRecord([createTextCell("OSDbg_TimeDlyHMSMEn"), createTextCell(self.readRecord(debug, "OSDbg_TimeDlyHMSMEn", "number")),createTextCell("Time delay enable")]))
        records.append(self.createRecord([createTextCell("OSDbg_TimeDlyResumeEn"), createTextCell(self.readRecord(debug, "OSDbg_TimeDlyResumeEn", "number")),createTextCell("Time delay resume enable")]))
        #records.append(self.createRecord([createTextCell("OSDbg_Tmr"), createTextCell(self.readRecord(debug, "OSDbg_Tmr", "number"))]))
        records.append(self.createRecord([createTextCell("OSDbg_TmrDelEn"), createTextCell(self.readRecord(debug, "OSDbg_TmrDelEn", "number")),createTextCell("Timer delete enable")]))
        records.append(self.createRecord([createTextCell("OSDbg_TmrEn"), createTextCell(self.readRecord(debug, "OSDbg_TmrEn", "number")),createTextCell("Timer enable")]))
        records.append(self.createRecord([createTextCell("OSDbg_TmrSize"), createTextCell(self.readRecord(debug, "OSDbg_TmrSize", "number")),createTextCell("Timer size")]))
        records.append(self.createRecord([createTextCell("OSDbg_TmrSpokeSize"), createTextCell(self.readRecord(debug, "OSDbg_TmrSpokeSize", "number")),createTextCell("Timer spoke size")]))
        self.readTimerWheelRecords(debug, "OSCfg_TmrWheel", records)
        records.append(self.createRecord([createTextCell("OSIntNestingCtr"), createTextCell(self.readRecord(debug, "OSIntNestingCtr", "number")),createTextCell("Interrupt nesting control")]))
        records.append(self.createRecord([createTextCell("OSIntDisTimeMax"), createTextCell(self.readRecord(debug, "OSIntDisTimeMax", "number")),createTextCell("Maximum interrupt disable time")]))
        records.append(self.createRecord([createTextCell("OSFlagQty"), createTextCell(self.readRecord(debug, "OSFlagQty", "number")),createTextCell("Maximum number of flags")]))
        records.append(self.createRecord([createTextCell("OSMemQty"), createTextCell(self.readRecord(debug, "OSMemQty", "number")),createTextCell("Maximum number of memory partitions")]))
        records.append(self.createRecord([createTextCell("OSMutexQty"), createTextCell(self.readRecord(debug, "OSMutexQty", "number")),createTextCell("Maximum number of mutex's")]))
        records.append(self.createRecord([createTextCell("OSSemQty"), createTextCell(self.readRecord(debug, "OSSemQty", "number")),createTextCell("Maximum number of semaphore's")]))
        records.append(self.createRecord([createTextCell("OSTmrQty"), createTextCell(self.readRecord(debug, "OSTmrQty", "number")),createTextCell("Maximum number of timers")]))
        records.append(self.createRecord([createTextCell("OSMsgPool.NbrFree"), createTextCell(self.readRecord(debug, "OSMsgPool.NbrFree", "number")),createTextCell("Number of free memory pools")]))
        records.append(self.createRecord([createTextCell("OSMsgPool.NbrUsed"), createTextCell(self.readRecord(debug, "OSMsgPool.NbrUsed", "number")),createTextCell("Number of memory pools used")]))
        records.append(self.createRecord([createTextCell("OSMsgPool.NbrUsedMax"), createTextCell(self.readRecord(debug, "OSMsgPool.NbrUsedMax", "number")),createTextCell("Maximum number of memory pools used")]))
        records.append(self.createRecord([createTextCell("OSSchedLockTimeMax"), createTextCell(self.readRecord(debug, "OSSchedLockTimeMax", "number")),createTextCell("Maximum scheduler lock time")]))
        records.append(self.createRecord([createTextCell("OSSchedLockTimeMaxCur"), createTextCell(self.readRecord(debug, "OSSchedLockTimeMaxCur", "number")),createTextCell("Current maximum scheduler lock time")]))
        self.readTimerWheelRecords(debug, "OSCfg_TickWheel", records)
        records.append(self.createRecord([createTextCell("OSIdleTaskCtr"), createTextCell(self.readRecord(debug, "OSIdleTaskCtr", "number")),createTextCell("Idle task control")]))
        records.append(self.createRecord([createTextCell("OSTaskCtxSwCtr"), createTextCell(self.readRecord(debug, "OSTaskCtxSwCtr", "number")),createTextCell("Task context switch control")]))
        records.append(self.createRecord([createTextCell("OSTickCtr"), createTextCell(self.readRecord(debug, "OSTickCtr", "number")),createTextCell("Tick control")]))
        records.append(self.createRecord([createTextCell("OSIntQNbrEntries"), createTextCell(self.readRecord(debug, "OSIntQNbrEntries", "number")),createTextCell("Number of interrupt queue entries")]))
        records.append(self.createRecord([createTextCell("OSIntQNbrEntriesMax"), createTextCell(self.readRecord(debug, "OSIntQNbrEntriesMax", "number")),createTextCell("Maximum number of interrupt queue entries")]))
        records.append(self.createRecord([createTextCell("OSIntQOvfCtr"), createTextCell(self.readRecord(debug, "OSIntQOvfCtr", "number")),createTextCell("Interrupt queue control")]))
        records.append(self.createRecord([createTextCell("OSIntQTaskTimeMax"), createTextCell(self.readRecord(debug, "OSIntQTaskTimeMax", "number")),createTextCell("Maximum interrupt queue task time")]))
        self.readReadyListRecord(debug, records)
        #records.append(self.createRecord([createTextCell("Ready Tasks by Priority"), createTextCell(self.readReadyListRecord(debug))]))
        records.append(self.createRecord([createTextCell("OSSchedLockNestingCtr"), createTextCell(self.readRecord(debug, "OSSchedLockNestingCtr", "number")),createTextCell("Scheduler lock nesting control")]))
        records.append(self.createRecord([createTextCell("OSSchedRoundRobinEn"), createTextCell(self.readRecord(debug, "OSSchedRoundRobinEn", "number")),createTextCell("Round robin scheduling enable")]))
        records.append(self.createRecord([createTextCell("OSStatTaskCPUUsage"), createTextCell(self.readRecord(debug, "OSStatTaskCPUUsage", "number")),createTextCell("Statistical task CPU usage")]))
        records.append(self.createRecord([createTextCell("OSStatTaskCtr"), createTextCell(self.readRecord(debug, "OSStatTaskCtr", "number")),createTextCell("Statistical task control")]))
        records.append(self.createRecord([createTextCell("OSStatTaskCtrMax"), createTextCell(self.readRecord(debug, "OSStatTaskCtrMax", "number")),createTextCell("Statistical task control maximum")]))
        records.append(self.createRecord([createTextCell("OSStatTaskTimeMax"), createTextCell(self.readRecord(debug, "OSStatTaskTimeMax", "number")),createTextCell("Statistical task time maximum")]))
        records.append(self.createRecord([createTextCell("OSTmrTaskTimeMax"), createTextCell(self.readRecord(debug, "OSTmrTaskTimeMax", "number")),createTextCell("Timer task timer maximum")]))
        records.append(self.createRecord([createTextCell("OSTmrCtr"), createTextCell(self.readRecord(debug, "OSTmrCtr", "number")),createTextCell("Timer control")]))
        records.append(self.createRecord([createTextCell("OSTaskQty"), createTextCell(self.readRecord(debug, "OSTaskQty", "number")),createTextCell("Maximum number of tasks")]))

        return records