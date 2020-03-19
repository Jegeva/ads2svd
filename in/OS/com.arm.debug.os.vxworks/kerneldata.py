################################################################################
#
# Copyright (C) 2014,2017 Arm Limited (or its affiliates). All rights reserved.
#
#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

from osapi import *
from utils import createYesNoTextCell

class KernelData( Table ):

    def __init__( self ):

        cid = "kerdat"

        fields = [ createField( cid, "item", TEXT ), createField( cid, "value", TEXT ), createField( cid, "desc", TEXT ) ]

        Table.__init__( self, cid, fields )

    def addRecord( self, debugSession, records, descId, format, expr ):

        value = None

        if debugSession.symbolExists( expr ):
            if format == 'number':
                value = createTextCell( str( debugSession.evaluateExpression( expr ).readAsNumber( ) ) )
            elif format == 'address':
                value = createTextCell( str( debugSession.evaluateExpression( expr ).readAsAddress( ) ) )
            elif format == 'boolean':
                value = createYesNoTextCell( debugSession.evaluateExpression( expr ).readAsNumber( ) )

        if value:
            records.append( self.createRecord( [ createTextCell( expr ), value, createLocalisedTextCell( descId ) ] ) )

    def getRecords( self, ds ):

        recs = [ ]

        self.addRecord(ds, recs, 'kerdat.row.tasklibinit',       'number',  '"taskLib.c"::taskLibInstalled')
        self.addRecord(ds, recs, 'kerdat.row.usrstacksz',        'number',  'taskUsrExcStackSize')
        self.addRecord(ds, recs, 'kerdat.row.kerstacksz',        'number',  'taskKerExcStackSize')
        self.addRecord(ds, recs, 'kerdat.row.stackfill',         'number',  'globalNoStackFill')
        self.addRecord(ds, recs, 'kerdat.row.activities',        'number',  'taskActivityCount')
        self.addRecord(ds, recs, 'kerdat.row.curid',             'address', 'taskIdCurrent')
        self.addRecord(ds, recs, 'kerdat.row.timeout',           'number',  'vxCpuEnableTimeout')
        self.addRecord(ds, recs, 'kerdat.row.stackoverflowsz',   'number',  'vxIntStackOverflowSize')
        self.addRecord(ds, recs, 'kerdat.row.stackunderflowsz',  'number',  'vxIntStackUnderflowSize')
        self.addRecord(ds, recs, 'kerdat.row.rootmemstart',      'address', 'pRootMemStart')
        self.addRecord(ds, recs, 'kerdat.row.rootmemsz',         'number',  'rootMemNBytes')
        self.addRecord(ds, recs, 'kerdat.row.roottaskid',        'address', 'rootTaskId')
        self.addRecord(ds, recs, 'kerdat.row.rrobinon',          'number',  'roundRobinOn')
        self.addRecord(ds, recs, 'kerdat.row.rrobinslice',       'number',  'roundRobinSlice')
        self.addRecord(ds, recs, 'kerdat.row.rrobininstalled',   'number',  'roundRobinHookInstalled')
        self.addRecord(ds, recs, 'kerdat.row.rrobinhook',        'address', '_func_kernelRoundRobinHook')
        self.addRecord(ds, recs, 'kerdat.row.intstackend',       'address', 'vxIntStackEnd')
        self.addRecord(ds, recs, 'kerdat.row.intstackbase',      'address', 'vxIntStackBase')
        self.addRecord(ds, recs, 'kerdat.row.condvarlib',        'number',  '"condVarLib.c"::condVarLibInstalled')
        self.addRecord(ds, recs, 'kerdat.row.isrlib',            'number',  '"isrLib.c"::isrLibInstalled)')
        self.addRecord(ds, recs, 'kerdat.row.msqlib',            'number',  'isrLibInstalled')
        self.addRecord(ds, recs, 'kerdat.row.semlib',            'number',  '"semLib.c"::semLibInstalled)')
        self.addRecord(ds, recs, 'kerdat.row.absticks',          'number',  'vxAbsTicks')
        self.addRecord(ds, recs, 'kerdat.row.clkcnt',            'number',  'tickClkCnt')
        self.addRecord(ds, recs, 'kerdat.row.kernelstate',       'number',  'kernelState')
        self.addRecord(ds, recs, 'kerdat.row.kernelidle',        'number',  'kernelIsIdle')
        self.addRecord(ds, recs, 'kerdat.row.smobjpool',         'address', 'smObjPoolMinusOne')
        self.addRecord(ds, recs, 'kerdat.row.localglobaloffset', 'address', 'localToGlobalOffset')

        return recs

