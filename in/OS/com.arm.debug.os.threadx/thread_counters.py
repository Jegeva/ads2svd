# Copyright (C) 2013,2017 Arm Limited (or its affiliates). All rights reserved.

from utils import *
from osapi import createAddressCell

class ThreadCounters(Table):
    def __init__(self):
        id = "threadcounters"
        fields = [createField(id, "name", TEXT),
                          createField(id, "value", DECIMAL),
                  createField(id, "description", TEXT)]

        Table.__init__(self, id, fields)


    def getRecords(self, debugSession):
        records = []
        makeRec = lambda n, v, t: self.createRecord([createTextCell(n), createNumberCell(v), createTextCell(t)])

        if debugSession.symbolExists("_tx_thread_performance_resume_count") is False:
            return records

        records.append(makeRec("Resume Count",
                                                       debugSession.evaluateExpression("_tx_thread_performance_resume_count").readAsNumber(),
                                                       "Number of times thread resumption has occurred"))

        records.append(makeRec("Suspend Count",
                                                        debugSession.evaluateExpression("_tx_thread_performance_suspend_count").readAsNumber(),
                                                        "Number of times thread suspension has occurred"))

        records.append(makeRec("Solicited preemption",
                                                       debugSession.evaluateExpression("_tx_thread_performance_solicited_preemption_count").readAsNumber(),
                                                       "Number of times a thread is preempted by calling a ThreadX API service"))

        interrupt_preempt = debugSession.evaluateExpression("_tx_thread_performance_interrupt_preemption_count").readAsNumber()

        records.append(makeRec("Interrupt preemption", interrupt_preempt,
                                                       "Number of times a thread is preempted by an ISR calling a ThreadX API service"))

        records.append(makeRec("Priority inversion",
                                                       debugSession.evaluateExpression("_tx_thread_performance_priority_inversion_count").readAsNumber(),
                                                       "Total number of priority inversions"))

        records.append(makeRec("Timeslice",
                                                       debugSession.evaluateExpression("_tx_thread_performance_time_slice_count").readAsNumber(),
                                                       "Total number of times a thread was time-sliced"))

        records.append(makeRec("Relinquish",
                                                      debugSession.evaluateExpression("_tx_thread_performance_relinquish_count").readAsNumber(),
                                                      "Total number of times a thread relinquished"))

        records.append(makeRec("Timeout",
                                                       debugSession.evaluateExpression("_tx_thread_performance_timeout_count").readAsNumber(),
                                                       "Total number of times threads had a timeout"))

        records.append(makeRec("Abort",
                                                      debugSession.evaluateExpression("_tx_thread_performance_wait_abort_count").readAsNumber(),
                                                      "Number of times a thread had suspension lifted because of the tx_thread_wait_abort service"))

        records.append(makeRec("Idle returns",
                                                       debugSession.evaluateExpression("_tx_thread_performance_idle_return_count").readAsNumber(),
                                                       "Number of idle system thread returns. Each time a thread returns to an idle system (no other thread is ready to run) this variable is incremented"))

        non_idle_returns = debugSession.evaluateExpression("_tx_thread_performance_non_idle_return_count").readAsNumber()

        records.append(makeRec("Non-idle returns", non_idle_returns,
                                                       "Number of non-idle system thread returns. Each time a thread returns to a non-idle system (another thread is ready to run) this variable is incremented"))

        records.append(makeRec("Context Switches", interrupt_preempt + non_idle_returns,
                                                        "Total number of context switches in the system"))

        return records

