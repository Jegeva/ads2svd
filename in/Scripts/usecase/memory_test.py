# This script provides an example for a usecase script

# The header block describes the script, containing the following information:
#  - Title: this is shown in the scripts view
#  - Description: this is the content of the tooltip
#  - Help: this text is shown in the lower panel of the scripts view when
#          the script is selected
#  - Run: this is the python function called to run the script
#  - Options: this python function returns the configurable options for the script
#  - Validate: this python function checks the users configuration of the script

# import the package for usecase scripts
from arm_ds.usecase_script import UseCaseScript

# import the packages used in the script
from arm_ds.debugger_v1 import Debugger
import sys
import re
from jarray import array

"""
USECASE

$Title$ Memory test
$Description$ Test memory system by writing and verifying test patterns
$Run$ main
$Options$ options
$Validation$ validate
$Help$
This script performs simple memory testing.  Test patterns are written to memory
and read back, verifying against the values written.</br>
</br>
The script can be configured with the following options:
<ul>
<li>Address range to test</li>
<li>Access size.  The address range must be aligned to the access size</li>
<li>Test pattern to use.  The supported patterns are:
<ul>
<li>Walking ones</li>
<li>Walking zeroes</li>
<li>0xAA</li>
<li>0x55</li>
<li>Alternate 0xAA and 0x55</li>
<li>User specified value</li>
</ul>
<li>Number of times to verify each location</li>
<li>Number of times repeat each pattern</li>
<li>Whether to abort or continue on error</li>
</ul>
$Help$
"""

#
# The function should return a list of options - each option can be one of:
#  - booleanOption:
#    A boolean choice, shown by a checkbox on the configuration dialog
#  - enumOption:
#    A selection from a number of values
#    Shown by a drop-down on the configuration dialog
#  - radioEnumOption:
#    A selection from a number of values
#    Shown by radio buttons on the configuration dialog
#  - integerOption:
#    Input box for integer entry
#  - stringOption:
#    Input box for text entry
# Most options require a default value, given by the defaultValue keyword that
# will be used if the user does not specify any other value
#
# The options list can also contain the following elements for information and
# grouping of options:
#  - infoElement:
#    shows a text label
#  - optionGroup:
#    displays several options in a group
#  - tabSet / tabPage
#    displays groups of options on tabs.
#    The tabSet has a number of tabPages, each showing a group of options
#    container for tabPages
# The options within a group are given by the childOptions keyword
#
def options():
    '''Return the configurable options for the script
    '''
    return [
        # A group of options to enter the address range and access size
        UseCaseScript.optionGroup('range', 'Address range', childOptions=[
           # Address options.  Use strings as addresses can have prefixes
           UseCaseScript.stringOption('start', 'Start address', defaultValue="0x00000000"),
           UseCaseScript.stringOption('end', 'End address', defaultValue="0x00001000"),
           # Choice between access size
           UseCaseScript.enumOption('accessSize', 'Access size', values=[
               ('default', 'Default'), ('byte', 'Byte'),
               ('half', 'Half word (16-bit)'), ('word', 'Word (32-bit)')
           ],
           defaultValue='default'),
           ]),
        # A group of options for the test pattern
        UseCaseScript.optionGroup('pattern', 'Test pattern', childOptions=[
           # Descriptive text
           UseCaseScript.infoElement('', 'The selected test patterns are run in sequence'),
           UseCaseScript.booleanOption('walking_ones', 'Walking ones', description=
               'A walking ones pattern is written into successive memory locations',
               defaultValue=True),
           UseCaseScript.booleanOption('walking_zeros', 'Walking zeros', description=
               'A walking zeros pattern is written into successive memory locations',
               defaultValue=False),
           UseCaseScript.booleanOption('aa', '0xAA',
               description='0xAA is written into each memory location',
               defaultValue=False),
           UseCaseScript.booleanOption('55', '0x55',
               description='0x55 is written into each memory location',
               defaultValue=False),
           UseCaseScript.booleanOption('alt_aa_55', 'Alternate 0xAA, 0x55',
               description='0xAA and 0x55 are written into alternate memory locations',
               defaultValue=False),
           # A boolean with a child option
           UseCaseScript.booleanOption('custom', 'Custom',
               description= 'A user specified value is written into each memory location',
               defaultValue=False,
               childOptions=[
                   # This is only editable if the parent is selected
                   UseCaseScript.integerOption('value', '32-bit value', display=UseCaseScript.HEX, defaultValue=0)
                   ]),
           ]),
        # An integer (decimal)
        UseCaseScript.integerOption('read_count', 'Read count',
            description='The number of times to read and verify each location after each write',
            defaultValue=1,
            minimum=1, maximum=10),
        UseCaseScript.integerOption('repeat_count', 'Repeat count',
            description='The number of times to repeat the test',
            defaultValue=1,
            minimum=1, maximum=10),
        # Radio enum
        UseCaseScript.infoElement('', 'When verification fails:'),
        UseCaseScript.radioEnumOption('error', 'When verification fails:',
            description='Action when value read doesn\'t match value written',
            values=[('abort', 'Abort test'), ('continue', 'Print a warning and continue')],
            defaultValue='abort'
            )
    ]


def parseAddress(addrStr, addrName="Address"):
    '''Validate and split an address into
    - address space (optional, None if not set)
    - hex integer address
    '''
    # address are strings that:
    #  - have an optional address space, followed by a ':'
    #  - a hex number address
    addrMatcher = re.compile('(?:(\w+):)?0[xX]([0-9A-Fa-f]+)')
    m = addrMatcher.match(addrStr)
    if not m:
        UseCaseScript.error("%s '%s' is not a valid address" % (addrName, addrStr))
    space, addr = m.groups()
    return (space, long(addr, 16))

def makeAddr(space, addr):
    if space:
        # create string
        return "%s:0x%08X" % (space, addr)
    else:
        # memory functions will accept long address
        return addr

#
# This function validates the values entered by the user
#
# The options object passed can be used to get the values of the options with:
#     options.getOptionValue(optionName)
# This will return a value of the correct type for the option
#
# Invalid values can be reported by raising an exception or with the
# UseCaseScript.error() function
#
def validate(options):
    '''Validate the option values
    '''

    start = options.getOptionValue('range.start')
    end = options.getOptionValue('range.end')

    startSpace, startAddr = parseAddress(start, "Start address")
    endSpace, endAddr = parseAddress(end, "End address")

    if startSpace != endSpace:
        UseCaseScript.error("Start address '%s' and end address '%s' must be in the same address space" % (start, end))

    # start and end must be in the same space
    size = endAddr - startAddr + 1

    # start address < end address
    if startAddr >= endAddr:
        UseCaseScript.error("Start address must be less than end address")

    # start address is aligned to access size
    # range size is aligned to access size
    accessSize = options.getOptionValue('range.accessSize')
    if accessSize == 'half':
        if startAddr % 2 != 0:
            UseCaseScript.error('Start address is not aligned to 16-bit boundary')
        if size % 2 != 0:
            UseCaseScript.error('range size 0x%X is not aligned to 16-bit boundary' % size)
    elif accessSize == 'word':
        if startAddr % 4 != 0:
            UseCaseScript.error('Start address is not aligned to 32-bit boundary')
        if size % 4 != 0:
            UseCaseScript.error('range size 0x%X is not aligned to 32-bit boundary' % size)

#
# This is the main function of the usecase script
#
# The script can access the debugger connection by calling Debugger()
#
def main(options):
    # Get the debugger connection
    debugger = Debugger()

    # Get the memory service for the current core
    currentContext = debugger.getCurrentExecutionContext()
    ms = currentContext.getMemoryService()

    # process the option values
    start = options.getOptionValue('range.start')
    end = options.getOptionValue('range.end')

    startSpace, startAddr = parseAddress(start, "Start address")
    endSpace, endAddr = parseAddress(end, "End address")

    if startSpace != endSpace:
        UseCaseScript.error("Start address '%s' and end address '%s' must be in the same address space" % (start, end))
    size = endAddr - startAddr + 1

    # map accessSize to accessWidth (bits) used by memory service
    accessSize = options.getOptionValue('range.accessSize')
    if accessSize == 'default':
        # default access has same behaviour as byte access, but allows the
        # debug agent to optimize the access, e.g. using word accesses
        accessWidth = 0
    elif accessSize == 'byte':
        accessWidth = 8
    elif accessSize == 'half':
        accessWidth = 16
    elif accessSize == 'word':
        accessWidth = 32

    # build a list of patterns to test
    # each pattern is a sequence of bytes that will be repeated and written
    # to memory
    testPatterns = []
    if options.getOptionValue('pattern.walking_ones'):
        testPatterns.append([0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80])
    if options.getOptionValue('pattern.walking_zeros'):
        testPatterns.append([0xFE, 0xFD, 0xFB, 0xF7, 0xEF, 0xDF, 0xBF, 0x7F])
    if options.getOptionValue('pattern.aa'):
        testPatterns.append([0xAA])
    if options.getOptionValue('pattern.55'):
        testPatterns.append([0x55])
    if options.getOptionValue('pattern.alt_aa_55'):
        testPatterns.append([0xAA, 0x55])
    if options.getOptionValue('pattern.custom'):
        value = options.getOptionValue('pattern.custom.value')
        testPatterns.append([(value & 0xFF), ((value>>8) & 0xFF),
                          ((value>>16) & 0xFF), ((value>>24) & 0xFF)])

    # get the other parameters
    repeats = options.getOptionValue('repeat_count')
    reads = options.getOptionValue('read_count')
    abortOnError = options.getOptionValue('error') == 'abort'

    # perform the test
    for i in range(repeats):
        do_memory_test(ms, startSpace, startAddr, size, accessWidth, testPatterns, reads, abortOnError)

def to_s8(val):
    return val > 127 and val - 256 or val


def make_buffer(size, pattern):
    '''Create a buffer of size bytes filled with pattern'''
    # calculate how many repeats of pattern, rounding up
    reps = (size+len(pattern)-1)/len(pattern)
    # create reps copies of pattern and crop to size bytes
    buf = (pattern * reps)[:size]
    return map(to_s8, buf)


def do_memory_test(ms, addrSpace, startAddr, size, accessWidth, testPatterns, reads, abortOnError):

    # write in max 4k chunks
    chunkSize = min(0x1000, size)
    for p in testPatterns:
        print 'Testing range %s..+0x%X with pattern %s' % (makeAddr(addrSpace, startAddr), size, map(hex, p))

        # generate data and write to memory
        writeData = make_buffer(chunkSize, p)
        bytesLeft = size
        addr = startAddr
        while bytesLeft > 0:
            thisBlock = min(bytesLeft, chunkSize)
            ms.write(makeAddr(addrSpace, addr), writeData[:thisBlock], accessWidth=accessWidth)
            addr = addr + thisBlock
            bytesLeft -= thisBlock

        # read back and compare to write buffer
        errorFound = False
        for i in range(reads):
            # read back and verify
            bytesLeft = size
            addr = startAddr
            while bytesLeft > 0:
                thisBlock = min(bytesLeft, chunkSize)
                readData = ms.read(makeAddr(addrSpace, addr), size, accessWidth=accessWidth)
                for o in range(thisBlock):
                    if readData[o] != writeData[o]:
                        errorFound = True
                        print >> sys.stderr, "Wrote ", str(writeData[o])
                        print >> sys.stderr, "Read ", str(readData[o])
                        msg = 'Buffers differed at address %X for pattern %s' % (addr + o, p)
                        if abortOnError:
                            raise RuntimeError, msg
                        else:
                            print >> sys.stderr, msg
                addr = addr + thisBlock
                bytesLeft -= thisBlock
        if errorFound:
            print "Failed"
        else:
            print "OK"
