# Copyright (C) 2013,2017 Arm Limited (or its affiliates). All rights reserved.

from utils import *
from osapi import createAddressCell, createTextCell

class Timers(Table):
    def __init__(self):
        id = "timers"
        fields = [createField(id, "symbol", TEXT),
                  createField(id, "location", ADDRESS),
                  createField(id, "name", TEXT),
                  createField(id, "remaining", DECIMAL),
                  createField(id, "reinit", DECIMAL),
                  createField(id, "timeout_func", TEXT)]
        Table.__init__(self, id, fields)

    def readTimer(self, timer, sym):
        members = timer.getStructureMembers()
        internal = members['tx_timer_internal'].getStructureMembers()
        cells = [createTextCell(sym),
                 createAddressCell(timer.getLocationAddress()),
                 makeTextCell(members, "tx_timer_name"),
                 makeNumberCell(internal, "tx_timer_internal_remaining_ticks"),
                 makeNumberCell(internal, "tx_timer_internal_re_initialize_ticks"),
                 createTextCell(internal["tx_timer_internal_timeout_function"].resolveAddressAsString())]

        return self.createRecord(cells)

    def getRecords(self, debugSession):
        if not listSymbolsExist(debugSession, ListTypes.TIMER):
            return []
        createdptr = getListHead(debugSession, ListTypes.TIMER)
        if createdptr.readAsNumber() == 0:
            return []
        syms = [createdptr.resolveAddressAsString()]
        createdTimers = createdptr.dereferencePointer()
        allTimersList = readListWithSymbols(createdTimers, ListTypes.TIMER, syms)
        records = map(self.readTimer, allTimersList, syms)
        return records