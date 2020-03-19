# Copyright (C) 2013-2014,2017 Arm Limited (or its affiliates). All rights reserved.

from osapi import Table
from osapi import createField
from osapi import createTextCell, createNumberCell
from osapi import TEXT, DECIMAL, PERCENTAGE
from utils import traverse_list, pend_name
from utils import getMemberName
from globs import *

class Messages(Table):

    def __init__(self):
        id = "messages"

        fields = [
                  createField(id, "name", TEXT),
                  createField(id, "listening", TEXT),
                  createField(id, "next", TEXT),
                  createField(id, "capacity", DECIMAL),
                  createField(id, "utilisation", PERCENTAGE),
                  createField(id, "peak", PERCENTAGE),
                  createField(id, "MsgQID", TEXT)
                  ]

        Table.__init__(self, id, fields)

    def q_record(self, debugger, expression):
        structure = expression.dereferencePointer().getStructureMembers()

        pend_head = structure['PendList'].getStructureMembers()['HeadPtr']
        waiters = traverse_list(pend_head, 'NextPtr', pend_name)
        show_waiters = ', '.join(waiters) if len(waiters) > 0 else 'No Listeners'

        msg_structure = structure['MsgQ'].getStructureMembers()
        msg_head = msg_structure['OutPtr']

        size = msg_structure['NbrEntriesSize'].readAsNumber()
        entries = msg_structure['NbrEntries'].readAsNumber()
        peak_entries = msg_structure['NbrEntriesMax'].readAsNumber()

        msgQId = "N/A"
        msgQIdName = getMemberName( OS_Q_MSG_Q_ID, structure )
        if msgQIdName:
            msgQId = structure[ msgQIdName ].readAsNumber( )

        cells = [
                 createTextCell(structure['NamePtr'].readAsNullTerminatedString()),
                 createTextCell(show_waiters),
                 createTextCell(read_message(debugger.evaluateExpression, msg_head)),
                 createNumberCell(size),
                 createNumberCell(float(entries)/size),
                 createNumberCell(float(peak_entries)/size),
                 createTextCell(msgQId)
                 ]
        return self.createRecord(cells)

    def getRecords(self, debugger):
        if debugger.symbolExists("OSQDbgListPtr"):
            list_head = debugger.evaluateExpression("OSQDbgListPtr")
            return traverse_list(list_head, 'DbgNextPtr', lambda q: self.q_record(debugger, q))
        return []

def read_message(evaluator, expression):
    structure = expression.dereferencePointer().getStructureMembers()
    if expression.readAsNumber() == 0 or structure['MsgSize'] == 0:
        return "No Messages"
    LIMIT = 25

    #display hack
    str_pointer = evaluator('(char*)' + hex(structure['MsgPtr'].readAsNumber()))
    display = str_pointer.readAsNullTerminatedString()[:LIMIT]

    if structure['MsgSize'] > 25:
        display = display [:LIMIT - 3] + '...'
    return display