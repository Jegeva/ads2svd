# Copyright (C) 2013,2017 Arm Limited (or its affiliates). All rights reserved.

from utils import *
from osapi import createAddressCell

class QueueCounters(Table):
    def __init__(self):
        id = "queuecounters"
        fields = [createField(id, "name", TEXT),
                          createField(id, "value", DECIMAL),
                  createField(id, "description", TEXT)]

        Table.__init__(self, id, fields)


    def getRecords(self, debugSession):
        records = []
        makeRec = lambda n, v, t: self.createRecord([createTextCell(n), createNumberCell(v), createTextCell(t)])

        if debugSession.symbolExists("_tx_queue_performance_messages_sent_count") is False:
            return records

        records.append(makeRec("Sent count",
                                                  debugSession.evaluateExpression("_tx_queue_performance_messages_sent_count").readAsNumber(),
                                                  "Total number of messages sent"))

        records.append(makeRec("Received count",
                                                  debugSession.evaluateExpression("_tx_queue_performance_messages_received_count").readAsNumber(),
                                                  "Total number of messages received"))

        records.append(makeRec("Empty suspension",
                                                  debugSession.evaluateExpression("_tx_queue_performance_empty_suspension_count").readAsNumber(),
                                                  "Total number of queue empty suspensions"))

        records.append(makeRec("Full suspension",
                                                  debugSession.evaluateExpression("_tx_queue_performance_full_suspension_count").readAsNumber(),
                                                  "Total number of queue full suspensions"))

        records.append(makeRec("Queue full",
                                                  debugSession.evaluateExpression("_tx_queue_performance_full_error_count").readAsNumber(),
                                                 "Total number of queue full errors"))

        records.append(makeRec("Timeout",
                                                 debugSession.evaluateExpression("_tx_queue_performance_timeout_count").readAsNumber(),
                                                 "Total number of queue timeouts"))

        return records

