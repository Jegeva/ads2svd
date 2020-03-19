# Copyright (C) 2013,2017 Arm Limited (or its affiliates). All rights reserved.

from utils import *
from osapi import createAddressCell

class EventFlagsCounters(Table):
    def __init__(self):
        id = "eventflagscounters"
        fields = [createField(id, "name", TEXT),
              createField(id, "value", DECIMAL),
                  createField(id, "description", TEXT)]

        Table.__init__(self, id, fields)


    def getRecords(self, debugSession):
        records = []
        makeRec = lambda n, v, t: self.createRecord([createTextCell(n), createNumberCell(v), createTextCell(t)])

        if debugSession.symbolExists("_tx_event_flags_performance_set_count") is False:
            return records

        records.append(makeRec("Set count",
                debugSession.evaluateExpression("_tx_event_flags_performance_set_count").readAsNumber(),
                "Total number of event flags sets"))

        records.append(makeRec("Get count",
                debugSession.evaluateExpression("_tx_event_flags_performance_get_count").readAsNumber(),
                "Total number of event flags gets "))

        records.append(makeRec("Suspension count",
                debugSession.evaluateExpression("_tx_event_flags_performance_suspension_count").readAsNumber(),
                "Total number of event flags suspensions."))


        records.append(makeRec("Timeout",
                                debugSession.evaluateExpression("_tx_event_flags_performance_timeout_count").readAsNumber(),
                                "Total number of event flags timeouts"))

        return records

