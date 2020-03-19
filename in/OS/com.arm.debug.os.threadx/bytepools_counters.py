# Copyright (C) 2013,2017 Arm Limited (or its affiliates). All rights reserved.

from utils import *

class BytepoolCounters(Table):
    def __init__(self):
        id = "bytepoolcounters"
        fields = [createField(id, "name", TEXT),
                      createField(id, "value", DECIMAL),
                      createField(id, "description", TEXT)]

        Table.__init__(self, id, fields)

    def getRecords(self, debugSession):
        records = []
        makeRec = lambda n, v, t: self.createRecord([createTextCell(n), createNumberCell(v), createTextCell(t)])

        if debugSession.symbolExists("_tx_byte_pool_performance_allocate_count") is False:
            return records

        records.append(makeRec("Allocation count",
                                  debugSession.evaluateExpression("_tx_byte_pool_performance_allocate_count").readAsNumber(),
                                  "Total number of memory allocations"))

        records.append(makeRec("Release count",
                                 debugSession.evaluateExpression("_tx_byte_pool_performance_release_count").readAsNumber(),
                                 "Total number of memory release"))

        records.append(makeRec("Merge count",
                               debugSession.evaluateExpression("_tx_byte_pool_performance_merge_count").readAsNumber(),
                              "Total number of adjacent memory fragment merges"))

        records.append(makeRec("Split count",
                                debugSession.evaluateExpression("_tx_byte_pool_performance_split_count").readAsNumber(),
                                "Total number of memory fragment splits"))

        records.append(makeRec("Search count",
                                debugSession.evaluateExpression("_tx_byte_pool_performance_search_count").readAsNumber(),
                                "Total number of memory fragments searched during allocation"))

        records.append(makeRec("Suspension count",
                                debugSession.evaluateExpression("_tx_byte_pool_performance_suspension_count").readAsNumber(),
                                "Total number of byte pool suspensions"))

        records.append(makeRec("Timeout count",
                                debugSession.evaluateExpression("_tx_byte_pool_performance_timeout_count").readAsNumber(),
                                "Total number of byte pool timeouts"))

        return records
