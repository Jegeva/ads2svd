# Copyright (C) 2017 Arm Limited (or its affiliates). All rights reserved.

from osapi import *

class KernelInfo(Table):

    def __init__(self):
        cid = 'kernel'

        fields = [ createField(cid, 'item', TEXT), createField(cid, 'value', TEXT) ]

        Table.__init__(self, cid, fields)

    def getRecords(self, debugger):
        records = []

        kinfo = debugger.evaluateExpression('"kinfo.c"::kinfo_ptr').dereferencePointer().getStructureMembers()
        romheader_t = debugger.resolveType('P4_romboot_header_t')
        romheader_addr = debugger.evaluateExpression('"kglobal.c"::kglobal.psp->romheader').readAsAddress()
        romheader = debugger.constructPointer(romheader_t, romheader_addr).dereferencePointer()
        build_id = romheader.getStructureMembers()['build_id'].readAsNumber()
        char_t = debugger.resolveType('char')
        rom_build = debugger.constructPointer(char_t, romheader_addr.addOffset(build_id)).readAsNullTerminatedString()
        kernel_build = kinfo['kernel_id'].readAsNullTerminatedString()
        kernel_type = debugger.evaluateExpression('(char*) kernel_build_type').readAsNullTerminatedString()
        asp_id = kinfo['asp_id'].readAsNullTerminatedString()
        psp_id = kinfo['psp_id'].readAsNullTerminatedString()

        records.append(self.createTextRecord('kernel.items.rom', rom_build))
        records.append(self.createTextRecord('kernel.items.kernel_ver', kernel_build))
        records.append(self.createTextRecord('kernel.items.kernel_type', kernel_type))
        records.append(self.createTextRecord('kernel.items.asp_id', asp_id))
        records.append(self.createTextRecord('kernel.items.psp_id', psp_id))

        records.append(self.createSeparator())

        stack_size = kinfo['kernel_stack_size'].readAsNumber()
        if kinfo['dynamic_ticker_mode'].readAsNumber() == 1:
            ticker_mode = 'Dynamic'
        else:
            ticker_mode = 'Periodic'
        sys_tick_res = kinfo['ns_per_tick'].readAsNumber()
        timepart_tick_res = kinfo['ns_per_tp_tick'].readAsNumber()
        freepages = kinfo['freepages'].readAsNumber()
        allpages = kinfo['allpages'].readAsNumber()
        percentage = int(round((100.0/allpages)*freepages))

        records.append(self.createNumericRecord('kernel.items.num_cpu', kinfo['num_cpu']))
        records.append(self.createTextRecord('kernel.items.stack_size', '{0} B'.format(stack_size)))
        records.append(self.createTextRecord('kernel.items.ticker_mode', ticker_mode))
        records.append(self.createTextRecord('kernel.items.sys_tick_res', '{} ns'.format(sys_tick_res)))
        records.append(self.createTextRecord('kernel.items.timepart_tick_res', '{} ns'.format(timepart_tick_res)))
        records.append(self.createTextRecord('kernel.items.free_memory', '{0} ({1:d}%)'.format(freepages, percentage)))

        records.append(self.createSeparator())

        records.append(self.createNumericRecord('kernel.items.num_respart', kinfo['num_respart']))
        records.append(self.createNumericRecord('kernel.items.num_task', kinfo['num_task']))
        records.append(self.createNumericRecord('kernel.items.num_thread', kinfo['num_thread']))
        records.append(self.createNumericRecord('kernel.items.num_timepart', kinfo['num_timepart']))
        records.append(self.createNumericRecord('kernel.items.num_prio', kinfo['num_prio']))

        return records

    def createTextRecord(self, key, value):
        cells = []

        cells.append(createLocalisedTextCell(key))
        cells.append(createTextCell(value))

        return self.createRecord(cells)

    def createNumericRecord(self, key, value):
        cells = []

        cells.append(createLocalisedTextCell(key))
        cells.append(createTextCell(str(value.readAsNumber())))

        return self.createRecord(cells)

    def createSeparator(self):
        return self.createRecord([createTextCell(''),createTextCell('')])
