# Copyright (C) 2015,2017 Arm Limited (or its affiliates). All rights reserved.

"""
Implementation of OS support for Wind River VxWorks RTOS
"""

from osapi import *
from utils import *

class TaskOpts( Table ):

    def __init__( self ):

        cid = "tskopts"

        fields = [ createPrimaryField( cid, "tid", ADDRESS ) ]

        fields.append( createField( cid, "name", TEXT ) )
        fields.append( createField( cid, "options", TEXT ) )
        fields.append( createField( cid, "super", TEXT ) )
        fields.append( createField( cid, "ubreak", TEXT ) )
        fields.append( createField( cid, "deallocstk", TEXT ) )
        fields.append( createField( cid, "dealloctcb", TEXT ) )
        fields.append( createField( cid, "fp", TEXT ) )
        fields.append( createField( cid, "privum", TEXT ) )
        fields.append( createField( cid, "stdio", TEXT ) )
        fields.append( createField( cid, "privenv", TEXT ) )
        fields.append( createField( cid, "nostkfill", TEXT ) )
        fields.append( createField( cid, "privcwd", TEXT ) )
        fields.append( createField( cid, "nostkprot", TEXT ) )
        fields.append( createField( cid, "deallocexecstk", TEXT ) )

        Table.__init__( self, cid, fields )

    def readRecord( self, taskPtr, debugSession ):

        tcbMembers = taskPtr.dereferencePointer().getStructureMembers()

        taskAddr = taskPtr.readAsAddress()
        name = getClassName(tcbMembers['objCore'])
        options = tcbMembers["options"].readAsNumber()

        cells = []
        cells.append( createAddressCell( taskAddr ) )
        cells.append( createTextCell( name ) )
        cells.append( createTextCell( longToHex( options, 32 ) ) )
        cells.append( createYesNoTextCell( options & VX_SUPERVISOR_MODE ) )
        cells.append( createYesNoTextCell( options & VX_UNBREAKABLE ) )
        cells.append( createYesNoTextCell( options & VX_DEALLOC_STACK ) )
        cells.append( createYesNoTextCell( options & VX_DEALLOC_TCB ) )
        cells.append( createYesNoTextCell( options & VX_FP_TASK ) )
        cells.append( createYesNoTextCell( options & VX_PRIVATE_UMASK ) )
        cells.append( createYesNoTextCell( options & VX_STDIO ) )
        cells.append( createYesNoTextCell( options & VX_PRIVATE_ENV ) )
        cells.append( createYesNoTextCell( options & VX_NO_STACK_FILL ) )
        cells.append( createYesNoTextCell( options & VX_PRIVATE_CWD ) )
        cells.append( createYesNoTextCell( options & VX_NO_STACK_PROTECT ) )
        cells.append( createYesNoTextCell( options & VX_DEALLOC_EXC_STACK ) )

        return self.createRecord( cells )

    def getRecords( self, debugSession ):
        tcbPtrList = readTaskList( debugSession )
        return [ self.readRecord( taskPtr, debugSession ) for taskPtr in tcbPtrList ]

