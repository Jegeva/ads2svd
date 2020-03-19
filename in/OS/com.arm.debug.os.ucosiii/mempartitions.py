# Copyright (C) 2013-2014,2017 Arm Limited (or its affiliates). All rights reserved.

from osapi import *
from utils import traverse_list
from utils import getMemberName
from globs import *

class MemPartitions(Table):

    def __init__(self):
        id = "mempartitions"

        fields = [createField(id, "begin_addr", ADDRESS),
                  createField(id, "name", TEXT),
                  createField(id, "freelist", ADDRESS),
                  createField(id, "blksize", DECIMAL),
                  createField(id, "totalblks", DECIMAL),
                  createField(id, "freeblks", DECIMAL),
                  createField(id, "MemID", TEXT)
                 ]
        Table.__init__(self, id, fields)

    def memRecord(self, expression):
        structure = expression.dereferencePointer().getStructureMembers()

        memId = "N/A"
        memIdName = getMemberName( OS_MEM_MEM_ID, structure )
        if memIdName:
            memId = structure[ memIdName ].readAsNumber( )

        cells = [
                 createAddressCell(structure['AddrPtr'].readAsAddress()),
                 createTextCell(structure['NamePtr'].readAsNullTerminatedString()),
                 createAddressCell(structure['FreeListPtr'].readAsAddress()),
                 createNumberCell(structure['BlkSize'].readAsNumber()),
                 createNumberCell(structure['NbrMax'].readAsNumber()),
                 createNumberCell(structure['NbrFree'].readAsNumber()),
                 createTextCell(memId)
                 ]

        return self.createRecord(cells)

    def getRecords(self, debugger):
        if debugger.symbolExists("OSMemDbgListPtr"):
            list_head = debugger.evaluateExpression("OSMemDbgListPtr")
            return traverse_list(list_head, 'DbgNextPtr', self.memRecord)
        return []