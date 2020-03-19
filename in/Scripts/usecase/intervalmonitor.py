#! /usr/bin/env python
'''
    Copyright (C) 2018 Arm Limited (or its affiliates). All rights reserved.
    
 This script provides an example for a usecase script

 The header block describes the script, containing the following information:
  - Title: this is shown in the scripts view
  - Description: this is the content of the tooltip
  - Help: this text is shown in the lower panel of the scripts view when
          the script is selected
  - Run: this is the python function called to run the script
  - Options: this python function returns the configurable options for the script
  - Validate: this python function checks the users configuration of the script

 Three entry points are defined:
  - main: configures trace source to halt execution when code takes too long
  - clear: restores the trace source configuration and returns control to Arm DS
  - dump: shows information and register state for a trace source
'''

# import the package for usecase scripts
from arm_ds.usecase_script import UseCaseScript


# import the packages required by the script
from arm_ds.debugger_v1 import Debugger
from com.arm.debug.dtsl.configurations import DTSLv1
from com.arm.debug.dtsl import ConnectionManager
from com.arm.debug.dtsl.components import PTMRegisters
from com.arm.debug.dtsl.components import ETMPTMCommonRegisters
from com.arm.debug.dtsl.components import PTMTraceSource
from com.arm.debug.dtsl.components import ETMv3_5TraceSource
from optparse import OptionParser
import sys
import re

def tohex(rVal):
    return "0x%s" % ("00000000%x" % (rVal&0xffffffff))[-8:]

def getDebugger():
    debugger = Debugger()
    if not debugger.isConnected():
        UseCaseScript.error("No debugger connection")
    return debugger

def getDTSLConfiguration(debugger):
    dtslConnectionConfigurationKey = debugger.getConnectionConfigurationKey()
    dtslConnection = ConnectionManager.openConnection(dtslConnectionConfigurationKey)
    return dtslConnection.getConfiguration()

def getDTSLDeviceByName(dtslConfiguration, deviceName):
    deviceList = dtslConfiguration.getDevices()
    for device in deviceList:
        if deviceName == device.getName():
            return device
    return None

def getTraceSourceByName(debugger, deviceName):
    dtslConfiguration = getDTSLConfiguration(debugger)
    ptmDevice = getDTSLDeviceByName(dtslConfiguration, deviceName)
    if ptmDevice == None:
        UseCaseScript.error("No device named %s was found" % (deviceName))
    if not ptmDevice.isConnected():
        UseCaseScript.error("Device %s was found but is not currently connected" % (deviceName))
    return ptmDevice


"""
USECASE

$Title$ Trace source display
$Description$ Display information about and register values of a trace source
$Run$ display
$Options$ displayOptions
$Validation$ displayValidate
$Help$
Shows the properties and register values of the selected trace source
$Help$
"""
def displayOptions():
    return [ UseCaseScript.stringOption('source', 'Trace source',
                                        'The trace source to display',
                                        defaultValue='') ]

def displayValidate(options):
    # TODO: check for known trace source
    if options.getOptionValue('source') == "":
        UseCaseScript.error("Trace source must be specified")

def displayProperties(name, ptm):
    dstr = {False:"does not", True:"does"}
    print "%s is revision %d.%d" % (name, ptm.getMajorVersion(), ptm.getMinorVersion())
    print "%s %s support timestamps" % (name, dstr[ptm.hasTimestamping()])
    print "%s %s support cycle accurate" % (name, dstr[ptm.hasCycleAccurate()])
    print "%s %s support context IDs" % (name, dstr[ptm.hasContextIDs()])
    print "%s %s support virtualization" % (name, dstr[ptm.hasVirtualization()])
    print "%s %s support security extensions" % (name, dstr[ptm.hasSecurityExtensions()])

def displayRegisters(name, ptm):
    rVal = ptm.readRegister(PTMRegisters.ETMCR)
    print "%s ETMCR ............. : %s" % (name, tohex(rVal))
    rVal = ptm.readRegister(PTMRegisters.ETMCCR)
    print "%s ETMCCR ............ : %s" % (name, tohex(rVal))
    nComparators = (rVal & 0xF) * 2
    nCounters = (rVal >> 13) & 0x7
    rVal = ptm.readRegister(PTMRegisters.ETMTRIGGER)
    print "%s ETMTRIGGER ........ : %s" % (name, tohex(rVal))
    rVal = ptm.readRegister(PTMRegisters.ETMSR)
    print "%s ETMSR ............. : %s" % (name, tohex(rVal))
    rVal = ptm.readRegister(PTMRegisters.ETMSCR)
    print "%s ETMSCR ............ : %s" % (name, tohex(rVal))
    rVal = ptm.readRegister(PTMRegisters.ETMTSSCR)
    print "%s ETMTSSCR .......... : %s" % (name, tohex(rVal))
    rVal = ptm.readRegister(PTMRegisters.ETMTECR2)
    print "%s ETMTECR2 .......... : %s" % (name, tohex(rVal))
    rVal = ptm.readRegister(PTMRegisters.ETMTEEVR)
    print "%s ETMTEEVR .......... : %s" % (name, tohex(rVal))
    rVal = ptm.readRegister(PTMRegisters.ETMTECR1)
    print "%s ETMTECR1 .......... : %s" % (name, tohex(rVal))
    rVal = ptm.readRegister(PTMRegisters.ETMFFLR)
    print "%s ETMFFLR ........... : %s" % (name, tohex(rVal))
    for idx in range(nComparators):
        rVal = ptm.readRegister(PTMRegisters.ETMACVR_BASE+idx)
        print "%s ETMACVR[%2d] ....... : %s" % (name, idx, tohex(rVal))
    for idx in range(nCounters):
        rVal = ptm.readRegister(PTMRegisters.ETMACTR_BASE+idx)
        print "%s ETMACTR[%2d] ....... : %s" % (name, idx, tohex(rVal))
    for idx in range(nCounters):
        rVal = ptm.readRegister(PTMRegisters.ETMCNTRLDVR_BASE+idx)
        print "%s ETMCNTRLDVR[%2d] ... : %s" % (name, idx, tohex(rVal))
    for idx in range(nCounters):
        rVal = ptm.readRegister(PTMRegisters.ETMCNTENR_BASE+idx)
        print "%s ETMCNTENR[%2d] ..... : %s" % (name, idx, tohex(rVal))
    for idx in range(nCounters):
        rVal = ptm.readRegister(PTMRegisters.ETMCNTRLDEVR_BASE+idx)
        print "%s ETMCNTRLDEVR[%2d] .. : %s" % (name, idx, tohex(rVal))
    for idx in range(nCounters):
        rVal = ptm.readRegister(PTMRegisters.ETMCNTVR_BASE+idx)
        print "%s ETMCNTVR[%2d] ...... : %s" % (name, idx, tohex(rVal))
    for idx in range(PTMRegisters.ETMSQabEVR_COUNT):
        rVal = ptm.readRegister(PTMRegisters.ETMSQabEVR_BASE+idx)
        print "%s ETMSQabEVR[%2d] .... : %s" % (name, idx, tohex(rVal))
    rVal = ptm.readRegister(PTMRegisters.ETMSQR)
    print "%s ETMSQR ............ : %s" % (name, tohex(rVal))
    for idx in range(PTMRegisters.ETMEXTOUTEVR_COUNT):
        rVal = ptm.readRegister(PTMRegisters.ETMEXTOUTEVR_BASE+idx)
        print "%s ETMEXTOUTEVR[%2d] .. : %s" % (name, idx, tohex(rVal))
    for idx in range(PTMRegisters.ETMCIDCVR_COUNT):
        rVal = ptm.readRegister(PTMRegisters.ETMCIDCVR_BASE+idx)
        print "%s ETMCIDCVR[%2d] ..... : %s" % (name, idx, tohex(rVal))
    rVal = ptm.readRegister(PTMRegisters.ETMCIDCMR)
    print "%s ETMCIDCMR ......... : %s" % (name, tohex(rVal))
    rVal = ptm.readRegister(PTMRegisters.ETMSYNCFR)
    print "%s ETMSYNCFR ......... : %s" % (name, tohex(rVal))
    rVal = ptm.readRegister(PTMRegisters.ETMIDR)
    print "%s ETMIDR ............ : %s" % (name, tohex(rVal))
    rVal = ptm.readRegister(PTMRegisters.ETMCCER)
    print "%s ETMCCER ........... : %s" % (name, tohex(rVal))
    rVal = ptm.readRegister(PTMRegisters.ETMEXTINSELR)
    print "%s ETMEXTINSELR ...... : %s" % (name, tohex(rVal))
    rVal = ptm.readRegister(PTMRegisters.ETMTESSEICR)
    print "%s ETMTESSEICR ....... : %s" % (name, tohex(rVal))
    rVal = ptm.readRegister(PTMRegisters.ETMEIBCR)
    print "%s ETMEIBCR .......... : %s" % (name, tohex(rVal))
    rVal = ptm.readRegister(PTMRegisters.ETMTSEVR)
    print "%s ETMTSEVR .......... : %s" % (name, tohex(rVal))
    rVal = ptm.readRegister(PTMRegisters.ETMAUXCR)
    print "%s ETMAUXCR .......... : %s" % (name, tohex(rVal))
    rVal = ptm.readRegister(PTMRegisters.ETMTRACEIDR)
    print "%s ETMTRACEIDR ....... : %s" % (name, tohex(rVal))
    rVal = ptm.readRegister(PTMRegisters.ETMPDSR)
    print "%s ETMPDSR ........... : %s" % (name, tohex(rVal))

def display(options):
    source = options.getOptionValue('source')
    ts = getTraceSourceByName(getDebugger(), source)
    displayProperties(source, ts)
    displayRegisters(source, ts)


"""
USECASE

$Title$ Clear trace source
$Description$ Clear trace source configuration and return control to Arm DS
$Run$ clear
$Options$ clearOptions
$Validation$ clearValidate
$Help$
Restores the trace source registers and returns control to Arm DS for normal
trace operation
$Help$
"""

def clearOptions():
    return [ UseCaseScript.stringOption('source', 'Trace source',
                                        'The trace source to display',
                                        defaultValue='') ]

def clearValidate(options):
    # TODO: check for known trace source
    if options.getOptionValue('source') == "":
        UseCaseScript.error("Trace source must be specified")

def clearIntervalMonitor(name, ptm):
    '''
    '''
    reservedComparators = ptm.getReserverdComparatorSet()
    for idx in reservedComparators:
        ptm.writeRegister(PTMRegisters.ETMACVR_BASE+idx, 0)
        ptm.writeRegister(PTMRegisters.ETMACTR_BASE+idx, 1)
        ptm.unreserveComparator(idx)
    print "Programming PTM sequencer"
    ptm.writeRegister(PTMRegisters.ETMSQ12EVR, 0x406F) # Always FALSE
    ptm.writeRegister(PTMRegisters.ETMSQ21EVR, 0x406F) # Always FALSE
    ptm.writeRegister(PTMRegisters.ETMSQ13EVR, 0x406F) # Always FALSE
    ptm.writeRegister(PTMRegisters.ETMSQ31EVR, 0x406F) # Always FALSE
    ptm.writeRegister(PTMRegisters.ETMSQ23EVR, 0x406F) # Always FALSE
    ptm.writeRegister(PTMRegisters.ETMSQ32EVR, 0x406F) # Always FALSE
    print "Programming PTM events"
    ptm.writeRegister(PTMRegisters.ETMCNTENR_BASE+0, 0x2006F) # Counter 1 Always False
    ptm.writeRegister(PTMRegisters.ETMCNTENR_BASE+1, 0x2406F) # Counter 2 Always False
    ptm.writeRegister(PTMRegisters.ETMCNTRLDEVR_BASE+0, 0x2406F) # Counter 1 reload FALSE
    ptm.writeRegister(PTMRegisters.ETMCNTRLDEVR_BASE+1, 0x2406F) # Counter 2 Always FALSE
    ptm.writeRegister(PTMRegisters.ETMTRIGGER, 0x0000406f) # ETM Trigger set to false
    ptm.resumeControl();
    print "Interval monitor clearing complete"

def clear(options):
    source = options.getOptionValue('source')
    ts = getTraceSourceByName(getDebugger(), source)
    clearIntervalMonitor(source, ts)


"""
USECASE

$Title$ Execution monitor
$Description$ Use trace source to monitor execution time
$Run$ interval
$Options$ intervalOptions
$Validation$ intervalValidate
$Help$
This script configures ETMv3 and PTM trace sources to halt the core if a
section of code takes too long to execute.
</br>
The trace source is configured so that a counter is started when the start
address is executed.  The counter decrements on each system clock cycle.  If the
counter reaches 0 before the end address is executed, then the external debug
request is triggered to halt the core.
</br>
The script can be configured with the following options:
<ul>
<li>Address range to monitor</li>
<li>Number of cycles before halting core</li>
</ul>
$Help$
"""

def intervalOptions():
    return [ UseCaseScript.stringOption('source', 'Trace source',
                                        'The trace source to display',
                                        defaultValue=''),
        UseCaseScript.stringOption('eventAAddress', 'Start address',
                                    'The address to start monitoring at',
                                    defaultValue=''),
        UseCaseScript.stringOption('eventBAddress', 'End address',
                                    'The address to end monitoring at',
                                    defaultValue=''),
        UseCaseScript.integerOption('cycles', 'Maximum cycles',
                                    'The number of cycles before halting core',
                                    defaultValue=1000,
                                    minimum=1),
        ]

def intervalValidate(options):
    # TODO: check for known trace source
    if options.getOptionValue('source') == "":
        UseCaseScript.error("Trace source must be specified")
    # TODO: check valid address / symbol


def setupIntervalMonitor(name, ptm, eventAAddress, eventBAddress, cycles):
    '''
    This creates a PTM real time interval monitor. The monitor
    monitors the time interval between two events, Should the
    interval be greater than a threshold value, the monitor will
    halt trace and halt the core.

    To achieve this we:
       Program a comparator to match against event A, CA
       Program a comparator to match against event B, CB
       Set a counter value and its reload value to the threshold value
       Set the PTM sequencer to state 1
       Program the PTM events so that
          CA will cause the PTM sequencer to move to state 2
          CB will trigger a counter reload event
          CB will cause the PTM sequencer to move to state 1
          PTM sequencer at state 2 will enable the counter
          Counter at 0 will cause a PTM Trigger
    '''
    for idx in range(7):
        ptm.unreserveComparator(idx)
    ptm.relinquishControl()
    availableComparators = ptm.getAvailableComparatorSet()
    if len(availableComparators) < 2:
        UseCaseScript.error("Not enough free comparators in %s - need 2 free" % (name))
    ptmComparator0 = availableComparators[0]
    ptmComparator1 = availableComparators[1]
    print "Using comparators %d and %d" % (ptmComparator0, ptmComparator1)
    if not ptm.reserveComparator(ptmComparator0):
        UseCaseScript.error("Failed to reserve comparator %d" % (ptmComparator0))
    if not ptm.reserveComparator(ptmComparator1):
        UseCaseScript.error("Failed to reserve comparator %d" % (ptmComparator1))
    print "eventA is located at %s" % tohex(eventAAddress)
    ptm.writeRegister(PTMRegisters.ETMACVR_BASE+ptmComparator0, eventAAddress)
    ptm.writeRegister(PTMRegisters.ETMACTR_BASE+ptmComparator0, 1)
    print "eventB is located at %s" % tohex(eventBAddress)
    ptm.writeRegister(PTMRegisters.ETMACVR_BASE+ptmComparator1, eventBAddress)
    ptm.writeRegister(PTMRegisters.ETMACTR_BASE+ptmComparator1, 1)
    ptmCounterThreshold = cycles
    ptmCounter = 0
    print "Setting Counter %d to threshold of %d" % (ptmCounter, ptmCounterThreshold)
    ptm.writeRegister(PTMRegisters.ETMCNTRLDVR_BASE+ptmCounter, ptmCounterThreshold)
    ptm.writeRegister(PTMRegisters.ETMCNTVR_BASE+ptmCounter, ptmCounterThreshold)
    print "Programming sequencer"
    ptm.writeRegister(PTMRegisters.ETMSQ12EVR, ptmComparator0) # 1->2 on comparator 0
    ptm.writeRegister(PTMRegisters.ETMSQ21EVR, ptmComparator1) # 2->1 on comparator 1
    ptm.writeRegister(PTMRegisters.ETMSQ13EVR, 0x406F) # Always FALSE
    ptm.writeRegister(PTMRegisters.ETMSQ31EVR, 0x406F) # Always FALSE
    ptm.writeRegister(PTMRegisters.ETMSQ23EVR, 0x406F) # Always FALSE
    ptm.writeRegister(PTMRegisters.ETMSQ32EVR, 0x406F) # Always FALSE
    print "Programming events"
    ptm.writeRegister(PTMRegisters.ETMCNTENR_BASE+0, 0x20051) # Counter 1 enable when in sequencer state 2
    ptm.writeRegister(PTMRegisters.ETMCNTENR_BASE+1, 0x2406F) # Counter 2 Always False
    ptm.writeRegister(PTMRegisters.ETMCNTRLDEVR_BASE+0, ptmComparator1) # Counter 1 reload on comparator 0
    ptm.writeRegister(PTMRegisters.ETMCNTRLDEVR_BASE+1, 0x2406F) # Counter 2 Always FALSE
    ptm.writeRegister(PTMRegisters.ETMTRIGGER, 0x0040) # ETM Trigger on Counter 1 at 0
    ptm.writeRegister(PTMRegisters.ETMEXTOUTEVR_BASE+0, 0x0040) # EXT OUT 1 on Counter 1 at 0
    ptm.writeRegister(PTMRegisters.ETMEXTOUTEVR_BASE+1, 0x0040) # EXT OUT 2 on Counter 1 at 0
    print "Interval monitor programming complete"

def parseAddress(debugger, addrStr):
    # address are strings that:
    #  - have an optional address space, followed by a ':'
    #  - a hex number address
    addrMatcher = re.compile('(?:(\w+):)?0[xX]([0-9A-Fa-f]+)')
    m = addrMatcher.match(addrStr)
    if not m:
        # pass to debug engine to evaluate
        return long(debugger.getCurrentExecutionContext().executeDSCommand("output &(%s)" % addrStr)[2:12],16)
    space, addr = m.groups()
    return long(addr, 16)


def interval(options):
    source = options.getOptionValue('source')
    debugger = getDebugger()
    ts = getTraceSourceByName(debugger, source)
    eventAAddress = parseAddress(debugger, options.getOptionValue("eventAAddress"))
    eventBAddress = parseAddress(debugger, options.getOptionValue("eventBAddress"))
    cycles = options.getOptionValue('cycles')
    setupIntervalMonitor(source, ts, eventAAddress, eventBAddress, cycles)
