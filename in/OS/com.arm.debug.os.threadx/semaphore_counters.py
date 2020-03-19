# Copyright (C) 2013,2017 Arm Limited (or its affiliates). All rights reserved.

from utils import *
from osapi import createAddressCell

class SemaphoreCounters(Table):
    def __init__(self):
        id = "semaphorecounters"
        fields = [createField(id, "name", TEXT),
              createField(id, "value", DECIMAL),
                  createField(id, "description", TEXT)]

        Table.__init__(self, id, fields)


    def getRecords(self, debugSession):
        records = []
        makeRec = lambda n, v, t: self.createRecord([createTextCell(n), createNumberCell(v), createTextCell(t)])

        if  debugSession.symbolExists("_tx_semaphore_performance_put_count") is False:
            return records

        records.append(makeRec("Put count",
                debugSession.evaluateExpression("_tx_semaphore_performance_put_count").readAsNumber(),
                "Total number of semaphore puts"))

        records.append(makeRec("Get count",
                debugSession.evaluateExpression("_tx_semaphore_performance_get_count").readAsNumber(),
                "Total number of semaphore gets"))

        records.append(makeRec("Suspension count",
                debugSession.evaluateExpression("_tx_semaphore_performance_suspension_count").readAsNumber(),
                "Total number of semaphore suspensions"))


        records.append(makeRec("Timeout",
                                debugSession.evaluateExpression("_tx_semaphore_performance_timeout_count").readAsNumber(),
                                "Total number of semaphore timeouts"))

        records.append(makeRec("Created count",
                                debugSession.evaluateExpression("_tx_semaphore_created_count").readAsNumber(),
                                "Total number of created semaphores in the system"))

        return records

