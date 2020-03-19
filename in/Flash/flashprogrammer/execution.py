from com.arm.rddi import RDDI
from com.arm.rddi import RDDI_ACC_SIZE
from com.arm.rddi import RDDI_EVENT_TYPE
from com.arm.debug.flashprogrammer import FlashProgrammerRuntimeException
from com.arm.debug.dtsl.rddi import IDebugObserver

import caps
from device_memory import writeToTarget, intToBytes

from jarray import zeros, array
import threading
import time

from java.lang import Long

# Map of devices to their register maps
__regMaps = {}
def getRegMap(device):
    '''Get the map of register names to IDs for a device

    Will cache the maps for each device
    '''
    regMap = __regMaps.get(device)
    if not regMap:
        # haven't got this device's register map yet
        regMap = caps.reg_map(device)
        # save for future calls
        __regMaps[device] = regMap
    return regMap


def getRegID(regMap, regName):
    '''Get the ID number for a named register
    '''

    id = regMap.get(regName)
    if id is None:
        raise FlashProgrammerRuntimeException, "Unknown register %s" % regName
    return id


def asInt(v):
    '''Ensure value is int

    Values above 0x80000000 will be treated as longs by Jython, but must be
    passed as int to RDDI register write'''
    if v > 0xFFFFFFFFl:
        raise FlashProgrammerRuntimeException, "Cannot convert 0x%x to integer" % v
    return Long(v & 0xFFFFFFFFl).intValue()


def writeRegs(device, regs):
    '''Write registers to the device

    regs is a list of (name, value) tuples
    '''

    regMap = getRegMap(device)

    ids = []
    vals = []
    for n, v in regs:
       ids.append(getRegID(regMap, n))
       vals.append(asInt(v))

    device.regWriteList(ids, vals)


def readReg(device, regName):
    '''Read a register from the device'''
    regMap = getRegMap(device)
    v = zeros(1, 'i')
    device.regReadList([ getRegID(regMap, regName) ], v)
    return v[0]


def readRegs(device, regNames):
    '''Read a registers from the device'''

    regMap = getRegMap(device)

    ids = []
    for n in regNames:
       ids.append(getRegID(regMap, n))
    vals = zeros(len(ids), 'i')
    device.regReadList(ids, vals)
    return vals


def isV7M(device):
    '''Whether a device is v6M/v7M or other ARM

    Presence of XPSR register is used to determine this

    return True if device is v6M/v7M'''
    regMap = getRegMap(device)
    return 'XPSR' in regMap


def findRegister(device, names):
    regMap = getRegMap(device)
    for n in names:
        if n in regMap:
            return n
    raise FlashProgrammerRuntimeException, "Unknown register %s" % names[0]


def getSP(device):
    return findRegister(device, [ "SP", "R13" ])


def getLR(device):
    return findRegister(device, [ "LR", "R14" ])


def getPC(device):
    return findRegister(device, [ "PC", "R15" ])


class StopWaiter(IDebugObserver):
    '''Device state observer that allows waiting for the device to stop

    Register with the device via addDebugEventObserver() and call waitForStop()
    '''

    def __init__(self):
        # conditional varaible is used to lock & signal event received
        self.lock = threading.Condition()
        self.hasStopped = False

    def processEvent(self, event):
        '''Event handler - will be called by device when event is received'''
        if event.getEventType() == RDDI_EVENT_TYPE.RDDI_PROC_STATE_STOPPED:
            self.lock.acquire()
            try:
                self.hasStopped = True
                self.lock.notify()
            finally:
                self.lock.release()

    def waitForStop(self, timeout = None):
        '''Waits for the device to report a stop event

        Will throw an exception if timeout is reached
        '''
        self.lock.acquire()
        if timeout is not None:
            deadline = time.time() + timeout
        try:
            while not self.hasStopped:
                if timeout is not None:
                    timeLeft = deadline - time.time()
                    if timeLeft < 0:
                        raise FlashProgrammerRuntimeException, "Timeout waiting for stop"
                else:
                    timeLeft = None

                self.lock.wait(timeLeft)
        finally:
            self.lock.release()


def stopDevice(device, timeout=1.0):
    '''Stops a device

    Calls stop and waits for a stop event to be received
    '''
    # register for state events
    stopWaiter= StopWaiter()
    device.addDebugEventObserver(stopWaiter)
    try:
        device.stop()
        stopWaiter.waitForStop(timeout)
    finally:
        device.removeDebugEventObserver(stopWaiter)


def ensureDeviceStopped(device, timeout=1.0):
    '''Ensure a device is stopped
    '''
    # get current core state
    stateBuf = zeros(1, 'i')
    causeBuf = zeros(1, 'i')
    detailBuf = zeros(1, 'l')
    pageBuf = zeros(1, 'l')
    addrBuf = zeros(1, 'l')
    device.getExecStatus(stateBuf, causeBuf, detailBuf, pageBuf, addrBuf)
    state = RDDI_EVENT_TYPE.swigToEnum(stateBuf[0])

    # call stop if not stopped
    if state != RDDI_EVENT_TYPE.RDDI_PROC_STATE_STOPPED:
        stopDevice(device, timeout)


def runAndWaitForStop(device, timeout=1.0):
    '''Run the device and wait for it to stop

    An exception will be thrown if it doesn't stop before timeout has elapsed

    If the device doesn't stop, an attempt will be made to stop it
    '''
    # register for state events
    stopWaiter= StopWaiter()
    device.addDebugEventObserver(stopWaiter)
    try:
        # run
        device.go()

        # wait for breakpoint or timeout
        stopWaiter.waitForStop(timeout)
    except FlashProgrammerRuntimeException, e:
        if not stopWaiter.hasStopped:
            # didn't stop: try to force stop
            device.stop()
            # allow 100ms to stop: will throw if still not stopping
            stopWaiter.waitForStop(0.1)
        raise # rethrow to report timeout
    finally:
        device.removeDebugEventObserver(stopWaiter)


def runToBreakpoint(device, addr, bpFlags = RDDI.RDDI_BRUL_STD, timeout=1.0):
    '''Set a breakpoint, run the device and wait for the breakpoint to be hit
    '''
    # set BP on return address
    bp = device.setSWBreak(0, addr, bpFlags)
    try:
        runAndWaitForStop(device, timeout)
    finally:
        # remove break
        device.clearSWBreak(bp)


def setCoreStateRegs(device, regs, addr):
    if isV7M(device):
        # execute in thumb state
        regs.append(("XPSR", 0x01000000))
        regs.append(("CONTROL", 0))
        # raise priority to stop timer interrupts etc interfering
        regs.append(('PRIMASK', 1))
    else:
        # execute in SVC mode, interrupts disabled
        cpsrVal = 0x13 | 0xC0
        if addr & 0x1:
            # thumb mode
            cpsrVal |= 0x20
        regs.append(("CPSR", cpsrVal))


def funcCall(device, addr, args, stack, staticBase=None, timeout=1.0):
    '''Call a function on the target

    The function should be loaded into memory and should follow AAPCS
    (http://infocenter.arm.com/help/topic/com.arm.doc.ihi0042d/IHI0042D_aapcs.pdf)

    Compound types or types > 32bit are not supported
    '''
    # return to top of stack
    returnAddr = stack
    #  place branch to self (thumb encoding) at return address
    writeToTarget(device, returnAddr, intToBytes(0x0000E7FE))
    stack -= 4

    # build sequence of register (name, value) tuples
    regs = []

    # set R0..R3 to first four args
    nRegArgs = min(len(args), 4)
    if nRegArgs > 0:
        regArgVals = args[:nRegArgs]
        regArgRegs = [ "R0", "R1", "R2", "R3" ][:nRegArgs]
        regs += zip(regArgRegs, regArgVals)

    # remaining args are on stack
    stackBuf = []
    for a in args[4:]:
        # stack grows downwards, so prepend to buf
        stackBuf = intToBytes(a) + stackBuf
        stack -= 4
    if len(stackBuf) > 0:
        writeToTarget(device, stack, stackBuf)

    # set core state for execution
    setCoreStateRegs(device, regs, addr)

    # set static base if required
    if not staticBase is None:
        regs.append(("R9", staticBase))

    # set stack pointer
    regs.append((getSP(device), stack))

    # run from addr, returning to returnAddr
    regs.append((getLR(device), returnAddr | 1)) # return to thumb state
    regs.append((getPC(device), addr & 0xFFFFFFFE))

    # bulk write regs to target
    writeRegs(device, regs)

    # run the routine until return address is reached (will throw on timeout)
    runToBreakpoint(device, returnAddr, RDDI.RDDI_BRUL_ALT, timeout)

    # read registers
    pc, r0 = readRegs(device, [ getPC(device), "R0" ])

    # check PC is at expected return address
    if pc != asInt(returnAddr):
        raise FlashProgrammerRuntimeException, "Core did not stop at expected address: expected %x, but was %x" % (returnAddr, pc)

    # return R0
    return r0


# Thumb code that calls a routine a number of times with arguments in memory
#  R4 points to a table of arguments & expected return code:
#    [ r0, r1, r2, r3, expRet ]
#    [ r0, r1, r2, r3, expRet ]
#    [ r0, r1, r2, r3, expRet ]
#    ...
#  R5 contains the number of calls to make
#  R6 contains the address of the routine to call (bit 0 set for thumb)
#
REPEATER_CODE = [
0x00, 0xb5, #        0x200001da:    b500        ..      PUSH     {lr}
            #    repeatCallLoop
0x0f, 0xcc, #        0x200001dc:    cc0f        O.      LDM      r4!,{r0-r3}    ; load args
0x70, 0xb4, #        0x200001de:    b470        0.      PUSH     {r4-r6}        ; save R4-R6 in case routine changes them
0xb0, 0x47, #        0x200001e0:    47b0        .G      BLX      r6             ; call the routine
0x70, 0xbc, #        0x200001e2:    bc70        0.      POP      {r4-r6}        ; restore R4-R6
0x02, 0xcc, #        0x200001e4:    cc02        ..      LDM      r4!,{r1}       ; load expected return value
0x88, 0x42, #        0x200001e6:    4288        .B      CMP      r0,r1          ; compare with actual return
0x01, 0xd1, #        0x200001e8:    d101        ..      BNE      repeatCallDone ; stop if different
0x6d, 0x1e, #        0x200001ea:    1e6d        m.      SUBS     r5,r5,#1
0xf6, 0xd1, #        0x200001ec:    d1f6        ..      BNE      repeatCallLoop ; repeat while more calls
            #    repeatCallDone
0x00, 0xbd, #        0x200001ee:    bd00        ..      POP      {pc}           ; return to caller
                  ]

MAX_CALL_REPEATS = 20

def getWorkingRAMRequired(maxRepeats = MAX_CALL_REPEATS):
    '''Get the maximum amount of RAM required for the funcCallV7MRepeat operation

    This requires space for the code to run and the data to pass to the function
    '''
    codeSize = (len(REPEATER_CODE) + 3) & ~3 # word aligned
    dataSize = maxRepeats * 5 * 4 # 5x 32bit regs
    return codeSize + dataSize


def toBytes(buf):
    return ''.join(map(chr, buf))


def __funcCallRepeat(device, funcAddr, argLists, stack, workArea, staticBase=None, timeout=1.0):

    codeSize = (len(REPEATER_CODE) + 3) & ~3 # word aligned
    dataSize = len(argLists) * 5 * 4 # 5x 32bit regs
    dispatchSize = codeSize + dataSize

    # write dispatcher in memory
    writeToTarget(device, workArea, toBytes(REPEATER_CODE))
    codeAddr = workArea
    argAddr = workArea + codeSize

    # write argument lists after dispatcher (32bit aligned)
    argBuf = []
    for args, expR0 in argLists:
        if len(args) > 4:
            # stack args not supported
            raise FlashProgrammerRuntimeException, "Only 4 arguments are supported for repeated calls"

        regVals = (args + [ 0, 0, 0, 0])[:4] # ensure always 4 args
        for r in regVals:
            argBuf += intToBytes(r)
        argBuf += intToBytes(expR0)
    if len(argBuf) > 0:
        writeToTarget(device, argAddr, argBuf)

    # return to top of stack
    returnAddr = stack
    #  place branch to self at return address
    writeToTarget(device, returnAddr, intToBytes(0x0000E7FE))
    stack -= 4

    # build sequence of register (name, value) tuples
    regs = []

    # R4 points to dispatch table, R5 to dispatch count, R6 to function to call
    regs.append(("R4", argAddr))
    regs.append(("R5", len(argLists)))
    regs.append(("R6", funcAddr))

    # set core state for execution (thumb)
    setCoreStateRegs(device, regs, codeAddr | 1)

    # set static base if required
    if not staticBase is None:
        regs.append(("R9", staticBase))

    # set stack pointer
    regs.append((getSP(device), stack))

    # run from addr, returning to returnAddr
    regs.append((getLR(device), returnAddr | 1)) # return to thumb state
    regs.append((getPC(device), codeAddr & 0xFFFFFFFE))

    # bulk write regs to target
    writeRegs(device, regs)

    # run the routine until return address is reached (will throw on timeout)
    runToBreakpoint(device, returnAddr, RDDI.RDDI_BRUL_ALT, timeout)

    # read registers
    pc, r0, r5 = readRegs(device, [ getPC(device), "R0", "R5" ])

    # check PC is at expected return address
    if pc != asInt(returnAddr):
        raise FlashProgrammerRuntimeException, "Core did not stop at expected address: expected %x, but was %x" % (returnAddr, pc)

    # return number of operations executed & last return status
    return (len(argLists) - r5, r0)


def funcCallRepeat(device, funcAddr, argLists, stack, workArea, staticBase=None, maxRepeats=MAX_CALL_REPEATS, timeout=1.0):
    '''Call a function on the target

    The function should be loaded into memory and should follow AAPCS
    (http://infocenter.arm.com/help/topic/com.arm.doc.ihi0042d/IHI0042D_aapcs.pdf)

    Compound types or types > 32bit are not supported.
    Only 4 arguments per-call are supported (i.e. register arguments only)
    '''

    # limit the number of calls in each pass to the amount of arguments/return
    # values that can be stored in the working area
    opsComplete= 0
    for i in range(0, len(argLists), maxRepeats):
        passArgs = argLists[i:i+maxRepeats]
        ops, r0 = __funcCallRepeat(device, funcAddr, passArgs, stack, workArea, staticBase=staticBase, timeout=timeout)
        opsComplete += ops
        if ops < len(passArgs):
            return (opsComplete, r0)
    return (opsComplete, r0)
