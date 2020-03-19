# Copyright (C) 2017,2018 Arm Limited (or its affiliates). All rights reserved.

from utils import *


class Timers(RtxTable):

    STATES    = ["osRtxTimerInactive", "Stopped", "Running"]
    TYPES     = ["osTimerOnce", "osTimerPeriodic"]

    def __init__(self):
        id = "timers"

        fields = [createField(id, "addr",  ADDRESS),
                  createField(id, "name",  TEXT),
                  createField(id, "type",  TEXT),
                  createField(id, "state", TEXT),
                  createField(id, "delay", DECIMAL),
                  createField(id, "tick",  DECIMAL)]

        RtxTable.__init__(self, id, fields)


    def createRecordFromControlBlock(self, cbPtr, debugger):
        members = cbPtr.dereferencePointer().getStructureMembers()
        info_members = members["finfo"].getStructureMembers()
        name_field = "fp" if "fp" in info_members else "func"

        cells = [createAddressCell(cbPtr.readAsAddress()),
                 makeNameCell(info_members, name_field),
                 createTextCell(self.getType(members)),
                 createTextCell(self.getState(members)),
                 makeNumberCell(members, "load"),
                 createNumberCell(self.getCurrentTick(members))]

        return self.createRecord(cells)

    def getControlBlocks(self, dbg):
        if isVersion4(): return []

        return toIterator(dbg, "osRtxInfo.timer.list", "next")

    #osTimerOnce, osTimerPeriodic
    def getType(self, members):
        type = members["type"].readAsNumber()
        return Timers.TYPES[type] if (type>=0 and type<len(Timers.TYPES)) else "Invalid"

    def getState(self, members):
        state = members["state"].readAsNumber()
        return Timers.STATES[state] if (state>=0 and state<len(Timers.STATES)) else "Inactive"

    def getCurrentTick(self, members):
        prev = members["prev"]
        tick = members["tick"].readAsNumber()

        while(nonNullPtr(prev)):
            prev_members = prev.dereferencePointer().getStructureMembers()
            tick += prev_members.get("tick").readAsNumber()
            prev  = prev_members.get("prev")

        return tick
    