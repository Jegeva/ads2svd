# Copyright (C) 2013,2017 Arm Limited (or its affiliates). All rights reserved.

from utils import *
from osapi import createAddressCell

class MutexCounters(Table):
    def __init__(self):
        id = "mutexcounters"
        fields = [createField(id, "name", TEXT),
                  createField(id, "value", DECIMAL),
                  createField(id, "description", TEXT)]

        Table.__init__(self, id, fields)


    def getRecords(self, debugSession):
        records = []
        makeRec = lambda n, v, t: self.createRecord([createTextCell(n), createNumberCell(v), createTextCell(t)])

        if debugSession.symbolExists("_tx_mutex_performance_put_count") is False:
            return records

        records.append(makeRec("Puts",
                                 debugSession.evaluateExpression("_tx_mutex_performance_put_count").readAsNumber(),
                                 "Total number of mutex puts"))

        records.append(makeRec("Gets",
                                  debugSession.evaluateExpression("_tx_mutex_performance_get_count").readAsNumber(),
                                  "Total number of mutex gets"))

        records.append(makeRec("Suspensions",
                                debugSession.evaluateExpression("_tx_mutex_performance_suspension_count").readAsNumber(),
                                "Total number of mutex suspensions"))


        records.append(makeRec("Timeout",
                                debugSession.evaluateExpression("_tx_mutex_performance_timeout_count").readAsNumber(),
                                "Total number of mutex timeouts"))

        records.append(makeRec("Priority inversions",
                                debugSession.evaluateExpression("_tx_mutex_performance_priority_inversion_count").readAsNumber(),
                                "Total number of priority inversions count"))

        records.append(makeRec("Priority inheritance",
                                debugSession.evaluateExpression("_tx_mutex_performance_priority_inheritance_count").readAsNumber(),
                                "Total number of priority inheritance conditions"))

        return records

