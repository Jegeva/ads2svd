from arm_ds.debugger_v1 import Debugger
from arm_ds.debugger_v1 import DebugException
import sys
from time import sleep

''' Reads the memory at the supplied address on the AHB and returns its value'''
def getAddrValue(context, addr):
    addr = addr[addr.find('P:')+2:]
    # and make into an AHB address
    addr = "AHB:" + addr
    val = context.getMemoryService().readMemory32(addr)
    return val


def setAddrValue(context, addr, value):
    addr = addr[addr.find('P:')+2:]
    # and make into an AHB address
    addr = "AHB:" + addr
    context.getMemoryService().writeMemory32(addr, value)
    verify = context.getMemoryService().readMemory32(addr)
    count = 0
    while (verify != value):
        sleep(0.20)
        count = count + 1
        if (count >= 10):
            print
            print >> sys.stderr, "Unable to set register value"
            return False
        else:
            verify = context.getMemoryService().readMemory32(addr)
    return True


def checkResetValues(execContext):
    '''Check reset manager HPS2FPGA registers are 0 '''
    try:
        # Set the lwhps2fpga and hps2fpga bits to 0
        brgmodrst = execContext.executeDSCommand('print &$Peripherals::$rstmgr::$rstmgr_brgmodrst')
        value = getAddrValue(execContext, brgmodrst)
        if ((value & 0x3) != 0x0):
            return False
        else:
            return True
    except DebugException, e:
        print "Cannot access hps2fpga register fields, will not attempt to read SYS ID register"
        return False


def expandName(name):
    ''' replace :: with $:: '''
    return name.replace('::', '::$')


def getSysIdResetValueMask(execContext, regs, sysReg):
    val, mask = None, None

    try:
        val = regs.getProperty(sysReg, 'resetValue')
        mask = regs.getProperty(sysReg, 'resetMask')
    except DebugException, e:
        print "SYS ID expected values could not be found. Has a peripheral description file been supplied?"

    return (val, mask)


def displaySysIdReg(execContext, regs, sysReg):
    ''' read sys id register and timestamp register '''
    print "Expected value of %s:" % sysReg
    resetValue, resetMask = getSysIdResetValueMask(execContext, regs, sysReg)
    if not resetValue is None:
        if resetMask is None:
            resetMask = 0xFFFFFFFF
        print "  0x%08x/0x%08x" % (resetValue, resetMask)


''' prints out expected value from TCF/SVD, compares actual values against it'''
def displayAndCheckSysIdReg(execContext, regs, sysReg):
    print "Checking %s" % sysReg
    resetValue, resetMask = getSysIdResetValueMask(execContext, regs, sysReg)
    if resetValue is None:
        print "  Cannot check %s" % (sysReg)
        res = False
    else:
        if resetMask is None:
            resetMask = 0xFFFFFFFF
        val = getSysRegValue(execContext, sysReg)
        if (val & resetMask) != (resetValue & resetMask):
            print
            print >> sys.stderr, "  Value 0x%08x does not match expected value 0x%08x/0x%08x" % (val, resetValue, resetMask)
            res = False
        else:
            print "  Value matches expected value 0x%08x/0x%08x" % (resetValue, resetMask)
            res = True
    print
    return res


''' print out value of register '''
def getSysRegValue(execContext, sysReg):

    expandedName = expandName(sysReg)
    addr = execContext.executeDSCommand('print &$%s' % expandedName)
    val = getAddrValue(execContext, addr)
    return val


''' Get the names of any registers in the correct group '''
def getSysIdNames(regs):
    matches = []
    names = regs.getRegisterNames()
    prefix = "altera_avalon_sysid"
    for name in names:
        if (name.find(prefix) != -1):
            matches.append(name)
    return matches


''' Main '''
debugger = Debugger()
execContext = debugger.getCurrentExecutionContext()
regs = execContext.getRegisterService()

sysIDRegs = getSysIdNames(regs)
if (len(sysIDRegs) < 1):
    print
    print "No SYSID registers could be found. Has a peripheral description file been supplied?"
    print
else:
    # This call to setResetValues may change the state of the target but is necessary for readSysId call to complete. '''
    canAccessFPGA = checkResetValues(execContext)
    if canAccessFPGA:
        print "Checking SYS ID registers"
    else:
        print "Cannot access FPGA to check SYS ID registers, expected values are:"
    for regName in sysIDRegs:
        if canAccessFPGA:
            displayAndCheckSysIdReg(execContext, regs, regName)
        else:
            displaySysIdReg(execContext, regs, regName)

