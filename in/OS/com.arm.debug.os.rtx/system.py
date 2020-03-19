# Copyright (C) 2013,2015,2017,2018 Arm Limited (or its affiliates). All rights reserved.

from utils import *

class System(Table):

    def __init__(self):
        id = "system"
        fields = [createField(id, "item", TEXT), createField(id, "value", TEXT)]

        Table.__init__(self, id, fields)

    def getRecords(self, debugSession):
        clockrate     = debugSession.evaluateExpression(getMemberName("osRtxConfig.tick_freq")).readAsNumber()
        robin_timeout = debugSession.evaluateExpression(getMemberName("osRtxConfig.robin_timeout")).readAsNumber()
        stackInfo     = debugSession.evaluateExpression(getMemberName("osRtxConfig.flags")).readAsNumber()

        records = []

        if isVersion4():
            os_stack_sz = debugSession.evaluateExpression("os_stack_sz").readAsNumber()

            records.append(self.buildRecord("system.record.clockrate", clockrate))
            records.append(self.buildRecord("system.record.default_stack_size", toHex(stackInfo & 0xFFFF)))
            records.append(self.buildRecord("system.record.robin_timeout", robin_timeout))
            records.append(self.buildRecord("system.record.private_stack_info", ((stackInfo >> 16) & 0xFF)))
            records.append(self.buildRecord("system.record.total_private_stack", toHex(os_stack_sz)))

            records.append(self.buildRecord("system.record.stack_overflow_check", self.isStackOverflowCheckEnabled(debugSession)))
            records.append(self.buildRecord("system.record.task_usage",  self.getTaskUsage(debugSession)))
            records.append(self.buildRecord("system.record.user_timers", self.getUserTimers(debugSession)))

        else:
            kernelId          = debugSession.evaluateExpression("osRtxInfo.os_id").readAsNullTerminatedString()
            kernel_state      = getKernelState(debugSession)
            kernel_tick_count = debugSession.evaluateExpression("osRtxInfo.kernel.tick").readAsNumber()
            robin_tick_count  = debugSession.evaluateExpression(getMemberName("osRtxInfo.thread.robin.tick")).readAsNumber()

            dynMemBase = debugSession.evaluateExpression("osRtxConfig.mem.common_addr")


            headDynMem = dynMemBase.dereferencePointer("mem_head_t*")
            used = headDynMem.getStructureMembers().get("used").readAsNumber()


            dynMemSize = debugSession.evaluateExpression("osRtxConfig.mem.common_size").readAsNumber()


            records.append(self.buildRecord("system.record.kernel_id", kernelId))
            records.append(self.buildRecord("system.record.kernel_state", kernel_state))
            records.append(self.buildRecord("system.record.kernel_tick_count", kernel_tick_count))
            records.append(self.buildRecord("system.record.kernel_tick_frequency", clockrate))
            records.append(self.buildRecord("system.record.robin_tick_count", robin_tick_count))
            records.append(self.buildRecord("system.record.robin_timeout", robin_timeout))

            (defaultStackSize, thread_obj_mem, num_user_thread, num_user_thread_def_stack, total_user_stack_size) = self.getThreadConfiguration(debugSession)
            nbOfActiveTasks = sum(1 for _ in getActiveTasks(debugSession))

            records.append(self.buildRecord("system.record.global_dyn_mem", "Base:%s, Size:%d, Used:%d" % (toHex(dynMemBase.readAsNumber()), dynMemSize, used)))
            records.append(self.buildRecord("system.record.thr_mem_pool", "Enabled" if thread_obj_mem else "Disabled"))
            records.append(self.buildRecord("system.record.num_user_thread", num_user_thread))
            records.append(self.buildRecord("system.record.num_user_thread_def_stack", num_user_thread_def_stack))
            records.append(self.buildRecord("system.record.total_user_stack", toHex(total_user_stack_size)))
            records.append(self.buildRecord("system.record.default_stack_size", toHex(defaultStackSize)))
            records.append(self.buildRecord("system.record.stack_overflow_check", self.isStackOverflowCheckEnabled(debugSession)))
            records.append(self.buildRecord("system.record.stack_usage_watermark", self.isStackUsageWatermarkEnabled(debugSession)))
            records.append(self.buildRecord("system.record.active_tasks", nbOfActiveTasks))
            records.append(self.buildRecord("system.record.user_timers", self.getUserTimers(debugSession)))

        return records

    def buildRecord(self, item, value):
        return self.createRecord([createTextCell(item), createTextCell(str(value))])

    def getUserTimers(self, debugSession):
        return sum(1 for _ in toIterator(debugSession, getMemberName("osRtxInfo.timer.list"), "next"))

    #RTX5 only
    def getThreadConfiguration(self, dbg):
        default_stack_size  = dbg.evaluateExpression("osRtxConfig.thread_stack_size").readAsNumber()
        user_stack_size     = 0

        num_user_thread = 0
        num_user_thread_def_stack = self.getNumberTasksWithDefaultStackSize(dbg)

        thread_obj_mem = False
        mpi_tcb = dbg.evaluateExpression("osRtxConfig.mpi.thread")

        if(nonNullPtr(mpi_tcb)):
            thread_obj_mem  = True
            num_user_thread = dbg.evaluateExpression("osRtxConfig.mpi.thread->max_blocks").readAsNumber()
            user_stack_size = dbg.evaluateExpression("osRtxConfig.mem.stack_size").readAsNumber()

        return (default_stack_size, thread_obj_mem, num_user_thread, num_user_thread_def_stack, user_stack_size)

    def getNumberTasksWithDefaultStackSize(self, dbg):
        mpi_stack = dbg.evaluateExpression("osRtxConfig.mpi.stack")

        return mpi_stack.dereferencePointer().getStructureMembers().get("max_blocks").readAsNumber() if(nonNullPtr(mpi_stack)) else 0

    #RTX4 only
    def getTaskUsage(self, debugSession):
        activeTCB   = debugSession.evaluateExpression("os_active_TCB").getArrayElements()
        activeTasks = sum(1 for _ in filter(lambda ptr: nonNullPtr(ptr), activeTCB))

        return "system.task_usage.description" + Localiser.FORMAT_SEPARATOR + str(len(activeTCB)) + Localiser.FORMAT_SEPARATOR + str(activeTasks)

    def isStackOverflowCheckEnabled(self, dbg):
        if isStackOverflowCheckEnabled(dbg):
            return "system.stack_overflow_check.yes"
        else:
            return "system.stack_overflow_check.no"

    def isStackUsageWatermarkEnabled(self, dbg):
        if isStackUsageWatermarkEnabled(dbg):
            return "system.stack_usage_watermark.yes"
        else:
            return "system.stack_usage_watermark.no"
