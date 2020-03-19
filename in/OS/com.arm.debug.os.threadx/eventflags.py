# Copyright (C) 2013,2017 Arm Limited (or its affiliates). All rights reserved.

from utils import *
from osapi import createAddressCell, createTextCell

class EventFlags(Table):
    def __init__(self):
        id = "eventflags"
        fields = [createField(id, "symbol", TEXT),
                  createField(id, "location", ADDRESS),
                  createField(id, "groupname", TEXT),
                  createField(id, "eventflags", HEXADECIMAL),
                  createField(id, "susp_count", DECIMAL),
                  createField(id, "susp_list", TEXT),
                  createField(id, "delayed_clear", HEXADECIMAL)]
        Table.__init__(self, id, fields)

    def readEventFlag(self, ef, sym):
        members = ef.getStructureMembers()

        cells = [createTextCell(sym),
                 createAddressCell(ef.getLocationAddress()),
                 makeTextCell(members, "tx_event_flags_group_name"),
                 makeNumberCell(members, "tx_event_flags_group_current"),
                 makeNumberCell(members, "tx_event_flags_group_suspended_count"),
                 createTextCell(getThreadNameList(members, 'tx_event_flags_group_suspension_list')),
                 makeNumberCell(members, "tx_event_flags_group_delayed_clear")]

        return self.createRecord(cells)

    def getRecords(self, debugSession):
        if not listSymbolsExist(debugSession, ListTypes.EVENTFLAG):
            return []
        createdptr = getListHead(debugSession, ListTypes.EVENTFLAG)
        if createdptr.readAsNumber() == 0:
            return []
        createdEventFlags = createdptr.dereferencePointer()
        syms = [createdptr.resolveAddressAsString()]
        allEventFlags = readListWithSymbols(createdEventFlags, ListTypes.EVENTFLAG, syms)
        records = map(self.readEventFlag, allEventFlags, syms)
        return records