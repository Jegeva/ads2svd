# Copyright (C) 2013,2017 Arm Limited (or its affiliates). All rights reserved.

from utils import *

class TimerCounters(Table):
    def __init__(self):
        id = "timercounters"
        fields = [createField(id, "name", TEXT),
                  createField(id, "value", DECIMAL),
                  createField(id, "description", TEXT)]

        Table.__init__(self, id, fields)

    def getRecords(self, debugSession):
        records = []
        makeRec = lambda n, v, t: self.createRecord([createTextCell(n), createNumberCell(v), createTextCell(t)])

        if debugSession.symbolExists("_tx_timer_performance_activate_count") is False:
            return records

        records.append(makeRec("Activation count",
                                debugSession.evaluateExpression("_tx_timer_performance_activate_count").readAsNumber(),
                                "Total number of timer activations"))

        records.append(makeRec("Reactivation count",
                                debugSession.evaluateExpression("_tx_timer_performance_reactivate_count").readAsNumber(),
                                "Total number of timer reactivations"))

        records.append(makeRec("Deactivation count",
                                debugSession.evaluateExpression("_tx_timer_performance_deactivate_count").readAsNumber(),
                                "Total number of timer deactivation"))

        records.append(makeRec("Expiration count",
                                debugSession.evaluateExpression("_tx_timer_performance_expiration_count").readAsNumber(),
                                "Total number of timer expiration"))

        records.append(makeRec("Adjustments count",
                                debugSession.evaluateExpression("_tx_timer_performance_expiration_adjust_count").readAsNumber(),
                                "Total number of time adjustments in the system"))

        return records
