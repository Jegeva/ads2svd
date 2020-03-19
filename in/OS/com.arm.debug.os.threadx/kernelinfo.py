# Copyright (C) 2013,2017 Arm Limited (or its affiliates). All rights reserved.

from utils import *
from osapi import createAddressCell, createTextCell

# Note: When run from Eclipse (as opposed to a standalone Java application), Jython
# cannot find one of module re's dependencies. We use Java String regex instead.
#import re
from java.lang import String

class KernelInfo(Table):
    def __init__(self):
        id = "kernelinfo"
        fields = [createField(id, "name", TEXT),
                  createField(id, "value", TEXT)]
        Table.__init__(self, id, fields)

    def getVersionRecord(self, debugger, records):
        if not debugger.symbolExists("_tx_version_id"):
            return

        # we want everything from (and including) "ThreadX" up until (and excluding) "SN"
        versionString = String(debugger.evaluateExpression('_tx_version_id').readAsNullTerminatedString()).replaceAll(".+(ThreadX.+) SN.+", "$1")
        # Note: When run from Eclipse (as opposed to a standalone Java application), Jython
        # cannot find one of module re's dependencies. We use Java String regex instead.
        #versionString = re.sub(r".+(ThreadX.+) SN.+", r"\1", debugger.evaluateExpression('_tx_version_id').readAsNullTerminatedString())
        records.append(self.createRecord([createTextCell("Version"),
                                          createTextCell(versionString)]))

    def getBuildOptsRecords(self, debugger, records):
        # Decode the build option variable bits
        if not debugger.symbolExists("_tx_build_options"):
            return

        makeRec = lambda n, v: self.createRecord([createTextCell(n), createTextCell(v)])

        val = debugger.evaluateExpression("_tx_build_options").readAsNumber()
        records.append(makeRec("Build Options (_tx_build_options)", hex(int(val))))

        #bitval = lambda v, bit: hex(int((v >> bit)  & 0x1))
        #records.append(makeRec("PORT_SPECIFIC_BUILD_OPTIONS", hex(int(val & 0x7f))))
        #records.append(makeRec("ENABLE_EXECUTION_CHANGE_NOTIFY", bitval(val, 7)))
        #records.append(makeRec("ENABLE_EVENT_TRACE", bitval(val, 8)))
        #records.append(makeRec("TIMER_ENABLE_PERFORMANCE_INFO", bitval(val, 9)))
        #records.append(makeRec("THREAD_ENABLE_PERFORMANCE_INFO", bitval(val, 10)))
        #records.append(makeRec("SEMAPHORE_ENABLE_PERFORMANCE_INFO", bitval(val, 11)))
        #records.append(makeRec("QUEUE_ENABLE_PERFORMANCE_INFO", bitval(val, 12)))
        #records.append(makeRec("MUTEX_ENABLE_PERFORMANCE_INFO", bitval(val, 13)))
        #records.append(makeRec("EVENT_FLAGS_ENABLE_PERFORMANCE_INFO", bitval(val, 14)))
        #records.append(makeRec("BYTE_POOL_ENABLE_PERFORMANCE_INFO", bitval(val, 15)))
        #records.append(makeRec("BLOCK_POOL_ENABLE_PERFORMANCE_INFO", bitval(val, 16)))
        #records.append(makeRec("DISABLE_NOTIFY_CALLBACKS", bitval(val, 17)))
        #records.append(makeRec("DISABLE_REDUNDANT_CLEARING", bitval(val, 18)))
        #records.append(makeRec("DISABLE_PREEMPTION_THRESHOLD", bitval(val, 19)))
        #records.append(makeRec("ENABLE_STACK_CHECKING", bitval(val, 20)))
        #records.append(makeRec("DISABLE_STACK_FILLING", bitval(val, 21)))
        #records.append(makeRec("REACTIVATE_INLINE", bitval(val, 22)))
        #records.append(makeRec("TIMER_PROCESS_IN_ISR", bitval(val, 23)))
        #records.append(makeRec("INLINE_THREAD_RESUME_SUSPEND", bitval(val, 30)))
        #records.append(makeRec("NOT_INTERRUPTABLE", bitval(val, 31)))
        #records.append(makeRec("MAX_PRIORITIES", str(int((val >> 24) & 0x3f) * 32)))

    def getRecords(self, debugger):
        records = []
        self.getVersionRecord(debugger, records)
        self.getBuildOptsRecords(debugger, records)
        return records