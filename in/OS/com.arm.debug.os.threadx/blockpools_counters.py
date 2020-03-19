# Copyright (C) 2013,2017 Arm Limited (or its affiliates). All rights reserved.

from utils import *

class BlockpoolCounters(Table):
    def __init__(self):
        id = "blockpoolcounters"
        fields = [createField(id, "name", TEXT),
                      createField(id, "value", DECIMAL),
                      createField(id, "description", TEXT)]

        Table.__init__(self, id, fields)

    def getRecords(self, debugSession):
        records = []
        makeRec = lambda n, v, t: self.createRecord([createTextCell(n), createNumberCell(v), createTextCell(t)])

        if debugSession.symbolExists("_tx_block_pool_performance_allocate_count") is False:
            return records


        records.append(makeRec("Allocation count",
                                  debugSession.evaluateExpression("_tx_block_pool_performance_allocate_count").readAsNumber(),
                                  "Total number of blocks allocated"))

        records.append(makeRec("Release count",
                                 debugSession.evaluateExpression("_tx_block_pool_performance_release_count").readAsNumber(),
                                 "Total number of blocks released"))

        records.append(makeRec("Suspension count",
                                debugSession.evaluateExpression("_tx_block_pool_performance_suspension_count").readAsNumber(),
                                "Total number of byte pool suspensions"))

        records.append(makeRec("Timeout count",
                                debugSession.evaluateExpression("_tx_block_pool_performance_timeout_count").readAsNumber(),
                                "Total number of block pool timeouts"))

        return records
