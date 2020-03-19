# Copyright (C) 2013-2014,2017 Arm Limited (or its affiliates). All rights reserved.

from osapi import *
from utils import traverse_list
from utils import getMemberName
from globs import *

# Timer options as defined in os.h
TIMER_OPTS = ["NONE",
              "ONE_SHOT",
              "PERIODIC",
              "CALLBACK",
              "CALLBACK_ARG"]

# Timer states as defined in os.h
TIMER_STATES = ["UNUSED",
                "STOPPED",
                "RUNNING",
                "COMPLETED"]

class Timers(Table):

    def __init__(self):
        id = "timers"

        fields = [createField(id, "name", TEXT),
                  createField(id, "callback", TEXT),
                  createField(id, "args", ADDRESS),
                  createField(id, "match", TEXT),
                  createField(id, "remain", DECIMAL),
                  createField(id, "delay", DECIMAL),
                  createField(id, "period", DECIMAL),
                  createField(id, "options", TEXT),
                  createField(id, "state", TEXT)
                  ]
        Table.__init__(self, id, fields)

    def getTimerOptionStr(self, value):
        if value >= len(TIMER_OPTS):
            return "INVALID OPTIONS"
        return TIMER_OPTS[value]

    def getTimerStateStr(self, value):
        if value >= len(TIMER_STATES):
            return "INVALID STATE"
        return TIMER_STATES[value]

    def timerRecord(self, expression):
        structure = expression.dereferencePointer().getStructureMembers()
        match = "N/A"
        matchName = getMemberName( OS_TMR_MATCH, structure )
        if matchName:
            match = str( structure[ matchName ].readAsNumber( ) )
        cells = [
                 createTextCell(structure['NamePtr'].readAsNullTerminatedString()),
                 createTextCell(structure['CallbackPtr'].resolveAddressAsString()),
                 createAddressCell(structure['CallbackPtrArg'].readAsAddress()),
                 createTextCell( match ),
                 createNumberCell(structure['Remain'].readAsNumber()),
                 createNumberCell(structure['Dly'].readAsNumber()),
                 createNumberCell(structure['Period'].readAsNumber()),
                 createTextCell(self.getTimerOptionStr(structure['Opt'].readAsNumber())),
                 createTextCell(self.getTimerStateStr(structure['State'].readAsNumber()))
                 ]

        return self.createRecord(cells)

    def getRecords(self, debugger):
        if debugger.symbolExists("OSTmrDbgListPtr"):
            list_head = debugger.evaluateExpression("OSTmrDbgListPtr")
            return traverse_list(list_head, 'DbgNextPtr', self.timerRecord)
        return []