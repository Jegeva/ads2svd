# Copyright (C) 2013-2014,2017 Arm Limited (or its affiliates). All rights reserved.

from osapi import Table
from osapi import createField
from osapi import createTextCell
from osapi import TEXT
from itertools import chain
from utils import traverse_list
from utils import getMemberName
from globs import *

FLAG_OPTS = [
             "CLR_ALL",
             "CLR_ANY",
             "SET_ALL",
             "SET_ANY",
             "CONSUME",
             ]

class Flags(Table):

    def __init__(self):
        id = "flags"

        fields = [
                  createField(id, "name", TEXT),
                  createField(id, "bitmap", TEXT),
                  createField(id, "pend", TEXT),
                  createField(id, "needed", TEXT),
                  createField(id, "option", TEXT),
                  createField(id, "timestamp", TEXT),
                  createField(id, "FlagId", TEXT)
                  ]

        Table.__init__(self, id, fields)

    def flag_records(self, expression):
        structure = expression.dereferencePointer().getStructureMembers()

        pend_head = structure['PendList'].getStructureMembers()['HeadPtr']
        waiters = traverse_list(pend_head,'NextPtr', sub_record)
        if not waiters:
            waiters = [[
                      createTextCell('No Waiters'),
                      createTextCell('-'),
                      createTextCell('-'),
                      ]]

        timestamp = structure['TS'].readAsNumber()
        show_ts = str(timestamp) if timestamp > 0 else 'Not Present'

        flagId = "N/A"
        flagIdName = getMemberName( OS_FLAG_GRP_FLAG_ID, structure )
        if flagIdName:
            flagId = structure[ flagIdName ].readAsNumber( )

        cells = [
                 createTextCell(structure['NamePtr'].readAsNullTerminatedString()),
                 createTextCell(hex(structure['Flags'].readAsNumber())),
                 createTextCell(show_ts),
                 createTextCell(flagId)
                 ]

        return map(lambda waiter: self.merge(cells, waiter), waiters)

    def merge(self, record, sub_record):
        pos = 2
        return self.createRecord(record[:pos] + sub_record + record[pos:])

    def getRecords(self, debugger):
        if debugger.symbolExists("OSFlagDbgListPtr"):
            list_head = debugger.evaluateExpression("OSFlagDbgListPtr")
            stacked_records = traverse_list(list_head, 'DbgNextPtr', self.flag_records)
            return list(chain(*stacked_records))
        return []

def show_opts(bitmap):
    return ', '.join([opt for (set, opt) in zip(bin(bitmap), FLAG_OPTS) if set])


def sub_record(pend_data):
    tcb_ptr = pend_data.dereferencePointer().getStructureMembers()['TCBPtr']
    tcb = tcb_ptr.dereferencePointer().getStructureMembers()
    return [
            createTextCell(tcb['NamePtr'].readAsNullTerminatedString()),
            createTextCell(hex(tcb['FlagsPend'].readAsNumber())),
            createTextCell(show_opts(tcb['FlagsOpt'].readAsNumber())),
            ]

def bin(n):
    #bin is not implemented in 2.5
    #HACK:consume bit appended to the end
    return map(lambda x:(n>>x)&1, range(len(FLAG_OPTS) - 1)) + [(n>>8&1)]