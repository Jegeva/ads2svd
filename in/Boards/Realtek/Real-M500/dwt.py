# Copyright (C) 2017-2018 Arm Limited (or its affiliates). All rights reserved.
from arm_ds.usecase_script import UseCaseScript
from arm_ds.debugger_v1 import Debugger
from arm_ds.debugger_v1 import DebugException
import struct
from jarray import zeros, array
from com.arm.debug.dtsl import ConnectionManager
from com.arm.debug.dtsl.configurations import DTSLv1
from com.arm.debug.dtsl.interfaces import IDevice
from com.arm.debug.dtsl import DTSLException
from com.arm.rddi import RDDI_ACC_SIZE

"""
USECASE

$Title$ Cortex-Mx DWT configuration
$Description$ Sets up the DWT to generate data for the Arm DS Events View
$Help$
<p>
The Cortex-M DWT can generate several types of event data ranging from PC
samples to interrupt counts. This script allows you to select which of these
events you wish the DWT to generate.
</p>
$Help$
$Options$ dwt_Options
$Validation$ dwt_ValidateOptions
$Run$ dwt
"""
ITM_BASE      = 0xE0000000               # @IgnorePep8
ITM_TCR       = ITM_BASE+0xE80
ITM_TCR_TSPRESCALE_POS  = 8
ITM_TCR_TSPRESCALE_MASK = 3 << ITM_TCR_TSPRESCALE_POS
ITM_TCR_DWTENA     = 1 << 3
ITM_TCR_SYNCENA    = 1 << 2
ITM_TCR_TSSENA     = 1 << 1
ITM_TCR_ITMSTIMENA = 1 << 0

DWT_BASE      = 0xE0001000               # @IgnorePep8
DWT_CTRL      = DWT_BASE+0x000           # @IgnorePep8
DWT_CTRL_CYCCNTENA   = 1 << 0            # @IgnorePep8
DWT_CTRL_CYCTAP      = 1 << 9            # @IgnorePep8
DWT_CTRL_PCSAMPLENA  = 1 << 12           # @IgnorePep8
DWT_CTRL_EXCTRCENA   = 1 << 16
DWT_CTRL_CPIEVTENA   = 1 << 17
DWT_CTRL_EXCEVTENA   = 1 << 18
DWT_CTRL_SLEEPEVTENA = 1 << 19
DWT_CTRL_LSUEVTENA   = 1 << 20
DWT_CTRL_FOLDEVTENA  = 1 << 21
DWT_CTRL_CYCEVTENA   = 1 << 22

DWT_CYCCNT    = DWT_BASE+0x004           # @IgnorePep8
DWT_CPICNT    = DWT_BASE+0x008           # @IgnorePep8
DWT_EXCCNT    = DWT_BASE+0x00C           # @IgnorePep8
DWT_SLEEPCNT  = DWT_BASE+0x010           # @IgnorePep8
DWT_LSUCNT    = DWT_BASE+0x014           # @IgnorePep8
DWT_FOLDCNT   = DWT_BASE+0x018           # @IgnorePep8
DWT_PCSR      = DWT_BASE+0x01C           # @IgnorePep8
DWT_COMP0     = DWT_BASE+0x020           # @IgnorePep8
DWT_MASK0     = DWT_BASE+0x024           # @IgnorePep8
DWT_FUNCTION0 = DWT_BASE+0x028           # @IgnorePep8
DWT_COMP1     = DWT_BASE+0x030           # @IgnorePep8
DWT_MASK1     = DWT_BASE+0x034           # @IgnorePep8
DWT_FUNCTION1 = DWT_BASE+0x038           # @IgnorePep8
DWT_COMP2     = DWT_BASE+0x040           # @IgnorePep8
DWT_MASK2     = DWT_BASE+0x044           # @IgnorePep8
DWT_FUNCTION2 = DWT_BASE+0x048           # @IgnorePep8
DWT_COMP3     = DWT_BASE+0x050           # @IgnorePep8
DWT_MASK3     = DWT_BASE+0x054           # @IgnorePep8
DWT_FUNCTION3 = DWT_BASE+0x058           # @IgnorePep8
DWT_PID4      = DWT_BASE+0xFD0           # @IgnorePep8
DWT_PID5      = DWT_BASE+0xFD4           # @IgnorePep8
DWT_PID6      = DWT_BASE+0xFD8           # @IgnorePep8
DWT_PID7      = DWT_BASE+0xFDC           # @IgnorePep8
DWT_PID0      = DWT_BASE+0xFE0           # @IgnorePep8
DWT_PID1      = DWT_BASE+0xFE4           # @IgnorePep8
DWT_PID2      = DWT_BASE+0xFE8           # @IgnorePep8
DWT_PID3      = DWT_BASE+0xFEC           # @IgnorePep8
DWT_CID0      = DWT_BASE+0xFF0           # @IgnorePep8
DWT_CID1      = DWT_BASE+0xFF4           # @IgnorePep8
DWT_CID2      = DWT_BASE+0xFF8           # @IgnorePep8
DWT_CID3      = DWT_BASE+0xFFC           # @IgnorePep8

OPT_AHB_NAME='Cortex-Mx DTSL AHB Name'
OPT_EXCTRCENA_ID='Exception trace'
OPT_EVENTS='Events'
OPT_FOLDEVTENA_ID='Folded instruction counter overflow event'
OPT_LSUEVTENA_ID='LSU counter overflow event'
OPT_SLEEPEVTENA_ID='Sleep counter overflow event'
OPT_EXCEVTENA_ID='Exception overhead counter overflow event'
OPT_CPIEVTENA_ID='CPI counter overflow event'

OPT_POSTCNTEN_ID='Enable cycle count events'
OPT_CYCEVENTTYPE_ID='Event to generate'
OPT_CYCCNTCLOCKDIV_ID='CYCCNT Divisor'

def dwt_Options():
    """ Returns this scripts option (parameter) set so that Arm DS can construct
        a GUI to collect the parameters from the use.
    Returns:
        an array of use case script options. See the help section
        'Defining the options for use case scripts' for details on the set of
        option objects that can be returned.
    """
    return [
        UseCaseScript.stringOption(
            name=OPT_AHB_NAME,
            displayName=OPT_AHB_NAME,
            description='The DTSL name for the AHB used to access the Cortex-Mx',
            defaultValue='AHB_M_0',
        ),
        UseCaseScript.booleanOption(
            name=OPT_EXCTRCENA_ID,
            displayName=OPT_EXCTRCENA_ID,
            description='Enables exception/interrupt trace',
            defaultValue=False,
        ),
        UseCaseScript.booleanOption(
            name=OPT_POSTCNTEN_ID,
            displayName=OPT_POSTCNTEN_ID,
            description='Enables POSTCNT cycle counter events',
            defaultValue=False,
            childOptions=[
                DTSLv1.enumOption(
                    name=OPT_CYCEVENTTYPE_ID,
                    displayName=OPT_CYCEVENTTYPE_ID,
                    defaultValue='PC Samples',
                    values=[
                        ('PC Samples', 'Output PC samples'),
                        ('Event counter', 'Output event counter packet')
                    ]
                ),
                DTSLv1.enumOption(
                    name=OPT_CYCCNTCLOCKDIV_ID,
                    displayName=OPT_CYCCNTCLOCKDIV_ID,
                    defaultValue='1024',
                    values = [
                        ('64','64 CYCTAP=0, POSTCNT=0'),
                        ('128','128 CYCTAP=0, POSTCNT=1'),
                        ('192','192 CYCTAP=0, POSTCNT=2'),
                        ('256','256 CYCTAP=0, POSTCNT=3'),
                        ('320','320 CYCTAP=0, POSTCNT=4'),
                        ('384','384 CYCTAP=0, POSTCNT=5'),
                        ('448','448 CYCTAP=0, POSTCNT=6'),
                        ('512','512 CYCTAP=0, POSTCNT=7'),
                        ('576','576 CYCTAP=0, POSTCNT=8'),
                        ('640','640 CYCTAP=0, POSTCNT=9'),
                        ('704','704 CYCTAP=0, POSTCNT=10'),
                        ('768','768 CYCTAP=0, POSTCNT=11'),
                        ('832','832 CYCTAP=0, POSTCNT=12'),
                        ('896','896 CYCTAP=0, POSTCNT=13'),
                        ('960','960 CYCTAP=0, POSTCNT=14'),
                        ('1024','1024 CYCTAP=1, POSTCNT=0'),
                        ('2048','2048 CYCTAP=1, POSTCNT=1'),
                        ('3072','3072 CYCTAP=1, POSTCNT=2'),
                        ('4096','4096 CYCTAP=1, POSTCNT=3'),
                        ('5120','5120 CYCTAP=1, POSTCNT=4'),
                        ('6144','6144 CYCTAP=1, POSTCNT=5'),
                        ('7168','7168 CYCTAP=1, POSTCNT=6'),
                        ('8192','8192 CYCTAP=1, POSTCNT=7'),
                        ('9216','9216 CYCTAP=1, POSTCNT=8'),
                        ('10240','10240 CYCTAP=1, POSTCNT=9'),
                        ('11264','11264 CYCTAP=1, POSTCNT=10'),
                        ('12288','12288 CYCTAP=1, POSTCNT=11'),
                        ('13312','13312 CYCTAP=1, POSTCNT=12'),
                        ('14336','14336 CYCTAP=1, POSTCNT=13'),
                        ('15360','15360 CYCTAP=1, POSTCNT=14'),
                        ('16384','16384 CYCTAP=1, POSTCNT=15')
                    ]
                ),
            ]
        ),
        DTSLv1.infoElement(
            name=OPT_EVENTS,
            displayName = 'Event selection',
            childOptions=[
                UseCaseScript.booleanOption(
                    name=OPT_FOLDEVTENA_ID,
                    displayName=OPT_FOLDEVTENA_ID,
                    description='Enable folded instruction counter overflow',
                    defaultValue=False
                ),
                UseCaseScript.booleanOption(
                    name=OPT_LSUEVTENA_ID,
                    displayName=OPT_LSUEVTENA_ID,
                    description='Enable LSU counter overflow',
                    defaultValue=False
                ),
                UseCaseScript.booleanOption(
                    name=OPT_SLEEPEVTENA_ID,
                    displayName=OPT_SLEEPEVTENA_ID,
                    description='Enable sleep counter overflow',
                    defaultValue=False
                ),
                UseCaseScript.booleanOption(
                    name=OPT_EXCEVTENA_ID,
                    displayName=OPT_EXCEVTENA_ID,
                    description='Enable overhead counter overflow',
                    defaultValue=False
                ),
                UseCaseScript.booleanOption(
                    name=OPT_CPIEVTENA_ID,
                    displayName=OPT_CPIEVTENA_ID,
                    description='Enable CPI counter overflow',
                    defaultValue=False
                )
            ]
        )
    ]


def dwt_ValidateOptions(options):
    """ Validates that the user options are acceptable. Note that we cant
        call any Arm Debugger API calls in here since we dont have access
        to any debugger connection. See the help section:
        'Defining the validation method for use case scripts' for details on
        validating user options.
    Parameters:
        options - the set of options we need to check
    """
    ahbName = options.getOptionValue(OPT_AHB_NAME)
    if len(ahbName) == 0:
        UseCaseScript.error(OPT_AHB_NAME + " cannot be empty")


def getDTSLDeviceByName(debugger, deviceName):
    """ Returns a device object referenced by name
    Parameters:
        debugger - the debugger interface object object
        deviceName - the device name e.e. "Cortex-A9_0" or "TPIU"
    NOTE: the device object we return implements the IDevice interface
    """
    dtslConfigurationKey = debugger.getConnectionConfigurationKey()
    dtslConnection = ConnectionManager.openConnection(dtslConfigurationKey)
    dtslConfiguration = dtslConnection.getConfiguration()
    deviceList = dtslConfiguration.getDevices()
    for device in deviceList:
        assert isinstance(device, IDevice)
        if deviceName == device.getName():
            return device
    return None

def apbWrite(debugAPB, address, value):
    byteData = struct.pack('<I', value)
    debugAPB.memWrite(0, address, RDDI_ACC_SIZE.RDDI_ACC_WORD, 0, False, 4, byteData)

def apbRead(debugAPB, address):
    data8Out = zeros(4, 'b')
    debugAPB.memRead(0, address, RDDI_ACC_SIZE.RDDI_ACC_WORD, 0, 4, data8Out)
    return struct.unpack('<I', data8Out)[0]

def dwt(options):
    """ This is the function called when the use case script is run.
    Parameters:
        options - the option set to apply when running the script
    """
    debugger = Debugger()
    if debugger is None:
        raise RuntimeError('Unable to connecto to debugger')
    ahbName = options.getOptionValue(OPT_AHB_NAME)
    debugAHB = getDTSLDeviceByName(debugger, ahbName)
    if debugAHB is None:
        raise RuntimeError(
            'Unable to locate AHB-AP (%s) in the DTSL configuration' %
            (ahbName))
    dwtCtrl = apbRead(debugAHB, DWT_CTRL)
    if options.getOptionValue(OPT_POSTCNTEN_ID):
        choice = options.getOptionValue(OPT_POSTCNTEN_ID+'.'+OPT_CYCEVENTTYPE_ID)
        if choice == 'PC Samples':
            dwtCtrl |= DWT_CTRL_PCSAMPLENA
            dwtCtrl &= ~DWT_CTRL_CYCEVTENA
        elif choice == 'Event counter':
            dwtCtrl |= DWT_CTRL_CYCEVTENA
            dwtCtrl &= ~DWT_CTRL_PCSAMPLENA
        choice = options.getOptionValue(OPT_POSTCNTEN_ID+'.'+OPT_CYCCNTCLOCKDIV_ID)
        divValue = int(choice)
        if divValue >= 1024:
            dwtCtrl |= DWT_CTRL_CYCTAP
            divValue = ((divValue/1024)-1) & 0x0F
        else:
            dwtCtrl &= ~DWT_CTRL_CYCTAP
            divValue = ((divValue/64)-1) & 0x0F
        divValue = (divValue << 1) | (divValue << 5)
        dwtCtrl &= ~((0xF << 1) | (0xF << 5))
        dwtCtrl |= divValue
    else:
        dwtCtrl &= ~DWT_CTRL_CYCEVTENA
        dwtCtrl &= ~DWT_CTRL_PCSAMPLENA
    if options.getOptionValue(OPT_EXCTRCENA_ID):
        dwtCtrl |= DWT_CTRL_EXCTRCENA
    else:
        dwtCtrl &= ~DWT_CTRL_EXCTRCENA
    if options.getOptionValue(OPT_EVENTS+'.'+OPT_FOLDEVTENA_ID):
        dwtCtrl |= DWT_CTRL_FOLDEVTENA
    else:
        dwtCtrl &= ~DWT_CTRL_FOLDEVTENA
    if options.getOptionValue(OPT_EVENTS+'.'+OPT_LSUEVTENA_ID):
        dwtCtrl |= DWT_CTRL_LSUEVTENA
    else:
        dwtCtrl &= ~DWT_CTRL_LSUEVTENA
    if options.getOptionValue(OPT_EVENTS+'.'+OPT_SLEEPEVTENA_ID):
        dwtCtrl |= DWT_CTRL_SLEEPEVTENA
    else:
        dwtCtrl &= ~DWT_CTRL_SLEEPEVTENA
    if options.getOptionValue(OPT_EVENTS+'.'+OPT_EXCEVTENA_ID):
        dwtCtrl |= DWT_CTRL_EXCEVTENA
    else:
        dwtCtrl &= ~DWT_CTRL_EXCEVTENA
    if options.getOptionValue(OPT_EVENTS+'.'+OPT_CPIEVTENA_ID):
        dwtCtrl |= DWT_CTRL_CPIEVTENA
    else:
        dwtCtrl &= ~DWT_CTRL_CPIEVTENA
    dwtCtrl |= DWT_CTRL_CYCCNTENA
    apbWrite(debugAHB, DWT_CTRL, dwtCtrl)
    print "DWT.CTRL written with 0x%08X" % (dwtCtrl)
    itmTCR = apbRead(debugAHB, ITM_TCR)
    itmTCR = itmTCR | (ITM_TCR_DWTENA)
    apbWrite(debugAHB, ITM_TCR, itmTCR)
    print "ITM.TCR  written with 0x%08X" % (itmTCR)
