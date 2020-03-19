# Copyright (C) 2013-2014,2017 Arm Limited (or its affiliates). All rights reserved.

from osapi import Table
from osapi import createField
from osapi import createTextCell, createNumberCell
from osapi import TEXT, DECIMAL
from utils import traverse_list, obj_name, pend_name
from utils import getMemberName
from globs import *

class Semaphores(Table):

    def __init__(self):
        id = "semaphores"

        fields = [
                  createField(id, "name", TEXT),
                  createField(id, "value", DECIMAL),
                  createField(id, "pend", TEXT),
                  createField(id, "timestamp", TEXT),
                  createField(id, "SemID", TEXT)
                  ]

        Table.__init__(self, id, fields)

    def mutex_record(self, expression):
        structure = expression.dereferencePointer().getStructureMembers()

        pend_head = structure['PendList'].getStructureMembers()['HeadPtr']
        waiters = traverse_list(pend_head,'NextPtr', pend_name)
        show_waiters = ', '.join(waiters) if len(waiters) > 0 else 'No Waiters'

        timestamp = structure['TS'].readAsNumber()
        show_ts = str(timestamp) if timestamp > 0 else 'Not Present'

        semId = "N/A"
        semIdName = getMemberName( OS_SEM_SEM_ID, structure )
        if semIdName:
            semId = structure[ semIdName ].readAsNumber( )

        cells = [
                 createTextCell(structure['NamePtr'].readAsNullTerminatedString()),
                 createNumberCell(structure['Ctr'].readAsNumber()),
                 createTextCell(show_waiters),
                 createTextCell(show_ts),
                 createTextCell(semId)
                 ]

        return self.createRecord(cells)

    def getRecords(self, debugger):
        if debugger.symbolExists("OSSemDbgListPtr"):
            list_head = debugger.evaluateExpression("OSSemDbgListPtr")
            return traverse_list(list_head, 'DbgNextPtr', self.mutex_record)
        return []