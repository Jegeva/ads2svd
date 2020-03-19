################################################################################
#
# Copyright (C) 2014,2017 Arm Limited (or its affiliates). All rights reserved.
#
#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

from osapi import *
from utils import *

def defRangeEntries(fields, cid, name):
    fields.append(createField(cid, "%s_start" % name, ADDRESS))
    fields.append(createField(cid, "%s_size" % name, DECIMAL))

def addRangeRecords(cells, members, name):
    addIfPresent(cells, members, "%s_start" % name, addrFun)
    addIfPresent(cells, members, "%s_size" % name, intFun)

class NuProcImageInfo(Table):

    def __init__(self):
        cid = "proc_image"
        fields = [createPrimaryField(cid, "addr", ADDRESS)]
        fields.append(createField(cid, "name", TEXT ))
        fields.append(createField(cid, "id", DECIMAL))
        fields.append(createField(cid, "entry_addr", ADDRESS))

        defRangeEntries(fields, cid, "text")
        defRangeEntries(fields, cid, "rodata")
        fields.append(createField(cid, "initdata_start", ADDRESS))
        defRangeEntries(fields, cid, "data")
        defRangeEntries(fields, cid, "bss")
        defRangeEntries(fields, cid, "stack")
        defRangeEntries(fields, cid, "heap")

        fields.append(createField(cid, "symbols", ADDRESS))
        fields.append(createField(cid, "usymbols", ADDRESS))
        fields.append(createField(cid, "ksymbols", ADDRESS))

        fields.append(createField(cid, "kernel_mode", DECIMAL))

        Table.__init__( self, cid, fields )

    def readRecord(self, cbPtr, debugSession):
        cbMembers = cbPtr.dereferencePointer().getStructureMembers()
        #This should always be present
        imageInfoPtr = cbMembers.get("image_info")
        imageInfoMembers = []
        if imageInfoPtr.readAsNumber != 0 :
            dereffed = imageInfoPtr.dereferencePointer()
            imageInfoMembers = dereffed.getStructureMembers()

        cells = [createAddressCell(imageInfoPtr.readAsAddress())]
        addIfPresent(cells, imageInfoMembers, "name", strFun)
        addIfPresent(cells, cbMembers, "id", intFun)

        addIfPresent(cells, imageInfoMembers, "entry_addr", addrFun)
        addRangeRecords(cells, imageInfoMembers, "text")
        addRangeRecords(cells, imageInfoMembers, "rodata")
        addIfPresent(cells, imageInfoMembers, "initdata_start", addrFun)
        addRangeRecords(cells, imageInfoMembers, "data")
        addRangeRecords(cells, imageInfoMembers, "bss")
        addRangeRecords(cells, imageInfoMembers, "stack")
        addRangeRecords(cells, imageInfoMembers, "heap")

        addIfPresent(cells, imageInfoMembers, "symbols", addrFun)
        addIfPresent(cells, imageInfoMembers, "usymbols", addrFun)
        addIfPresent(cells, imageInfoMembers, "ksymbols", addrFun)

        addIfPresent(cells, imageInfoMembers, "kernel_mode", intFun)
        return self.createRecord(cells)

    def getRecords(self, debugSession):
        procIter = listIter(debugSession, getFirstProcess, getNextProcess)
        result = [self.readRecord(procPtr, debugSession) for procPtr in procIter]
        return result;
