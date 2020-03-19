# Copyright (C) 2013-2014,2017 Arm Limited (or its affiliates). All rights reserved.

from osapi import Table
from osapi import createField
from osapi import createTextCell, createNumberCell
from osapi import TEXT, DECIMAL
from utils import traverse_list, obj_name, pend_name
from utils import getMemberName
from globs import *

class Mutexes(Table):

    def __init__(self):
        id = "mutexes"

        fields = [
                  createField(id, "name", TEXT),
                  createField(id, "owner", TEXT),
                  createField(id, "pend", TEXT),
                  createField(id, "nesting", DECIMAL),
                  createField(id, "timestamp", TEXT),
                  createField(id, "MutexID", TEXT)
                  ]

        Table.__init__(self, id, fields)

    def mutex_record(self, expression):
        structure = expression.dereferencePointer().getStructureMembers()

        owner = structure['OwnerTCBPtr']
        owner_name = obj_name(owner) if owner.readAsNumber() != 0 else 'No owner'

        pend_head = structure['PendList'].getStructureMembers()['HeadPtr']
        waiters = traverse_list(pend_head,'NextPtr', pend_name)
        show_waiters = ', '.join(waiters) if len(waiters) > 0 else 'No Waiters'

        nesting = structure['OwnerNestingCtr'].readAsNumber()

        timestamp = structure['TS'].readAsNumber()
        show_ts = str(timestamp) if timestamp > 0 else 'Not Present'

        mutexQId = "N/A"
        mutexQIdName = getMemberName( OS_MUTEX_MUTEX_ID, structure )
        if mutexQIdName:
            mutexQId = structure[ mutexQIdName ].readAsNumber( )

        cells = [
                 createTextCell(structure['NamePtr'].readAsNullTerminatedString()),
                 createTextCell(owner_name),
                 createTextCell(show_waiters),
                 createNumberCell(nesting),
                 createTextCell(show_ts),
                 createTextCell(mutexQId)
                 ]

        return self.createRecord(cells)

    def getRecords(self, debugger):
        if debugger.symbolExists("OSMutexDbgListPtr"):
            list_head = debugger.evaluateExpression("OSMutexDbgListPtr")
            return traverse_list(list_head, 'DbgNextPtr', self.mutex_record)
        return []