# Copyright (C) 2015,2017-2018 Arm Limited (or its affiliates). All rights reserved.

from utils import *

class Stacks(RtxTable):

    STACK_WATERMARK_PATTERN = 0xCCCCCCCCL

    # RTX places a magic word (by default 0xE25A2EA5) at the bottom of the
    # stack to aid with overflow detection. Extract this value.
    STACK_MAGIC_WORD        = 0xE25A2EA5L

    def __init__(self):
        id = "stacks"

        fields = [createPrimaryField(id, "id", TEXT),
                  createField(id, "name", TEXT),
                  createField(id, "alloc", TEXT),
                  createField(id, "size", HEXADECIMAL),
                  createField(id, "load", PERCENTAGE),
                  createField(id, "watermark", PERCENTAGE),
                  createField(id, "overflow", TEXT)]
        RtxTable.__init__(self, id, fields)

    def createRecordFromControlBlock(self, tcbPtr, debugger):
        members = dereferenceThreadPointer(tcbPtr).getStructureMembers()

        # Get the stack info
        # The 'stack' member only gets updated when the task context switches, so for active
        # tasks it's often wrong. Unfortunately $SP doesn't provide the correct value either
        # as some RTX programs (i.e. the Arm DS Examples) do not update $SP as they use the
        # stack (I don't understand why), and likewise $SP will not be correct if we start
        # executing OS code. For now we will stay with RTX's, out of date, pointer as it
        # always gives a sane value, even if it is not up to date.
        stackBase = getMember(members,"stack_mem").readAsAddress()
        stackPtr  = getMember(members,"sp").readAsAddress()
        stackSize = getStackSize(members, debugger)

        # Populate the cells
        taskIdCell    = makeTaskIdCell(tcbPtr, members)
        taskNameCell  = makeNameCell(members, "thread_addr")
        stackSizeCell = makeStackSizeCell(stackSize)
        if (stackSize > 0): # do not compute those if the stack size somehow ends up being 0 or negative
            stackAllocationCell = makeStackAllocationCell(stackBase, stackSize)
            stackLoadCell = makeStackLoadCell(stackBase, stackSize, stackPtr)
            stackWatermarkCell = makeStackWatermarkCell(debugger, stackBase, stackSize, stackPtr)
            stackOverflowCell = makeStackOverflowCell(debugger, stackBase)
        else:
            stackAllocationCell = createTextCell("")
            stackLoadCell = createTextCell("")
            stackWatermarkCell = createTextCell("")
            stackOverflowCell = createTextCell("")

        cells = [taskIdCell,
                 taskNameCell,
                 stackAllocationCell,
                 stackSizeCell,
                 stackLoadCell,
                 stackWatermarkCell,
                 stackOverflowCell]
        return self.createRecord(cells)

# Reads a 32 bit value from the given address.
def readAddress32(debugger, addr):
    return debugger.evaluateExpression("*((unsigned long*) %d)" % (addr.getLinearAddress())).readAsNumber()

# Reads a 64 bit value from the given address, returned as two 32-bit
# values, the high 32b followed by the low 32b.
def readAddress64(debugger, addr):
    val = debugger.evaluateExpression("*((unsigned long long*) %d)" % (addr.getLinearAddress())).readAsNumber()
    val_low  = (val & 0x00000000FFFFFFFF)
    val_high = (val & 0xFFFFFFFF00000000) >> 32
    return val_high, val_low

# RTX has an optionally enabled feature (default off) where each task's stack
# is filled with a known value when initialised so that it is possible to
# calculate a 'high-water mark' for the stack. This method finds the address
# of the high mark given the task's base stack address and size.
# This is based on the implementation of MQX's similar feature in
# com.arm.debug.os.mqx.tables, MqxStackUsageTable.java.
def calculateHighUsageAddr(debugger, stackBase, stackSize, stackPtr):
    # 1. Look at the value at the stack limit, if not equal to the
    #    magic number, we have maximal stack usage (or, more likely,
    #    overflow). Return the stack limit.
    stackLimit = stackBase.addOffset(4)
    if (readAddress32(debugger, stackLimit) != Stacks.STACK_WATERMARK_PATTERN):
        #print "Found high watermark at stack limit (%08X)" % (stackBase.getLinearAddress())
        return stackBase

    # 2. Look at the value after the current SP, if equal to the magic
    #    number then the current is the highest the stack has been.
    stackPtrNext = stackPtr.addOffset(-4)
    if (readAddress32(debugger, stackPtrNext) == Stacks.STACK_WATERMARK_PATTERN):
        #print "Found high watermark at stackpointer (%08X)" % (stackPtr.getLinearAddress())
        return stackPtr

    # 3. Otherwise do a binary chop to find the highest mark. The
    #    memory we are looking for is something like:
    #
    #    CCCCCCCC CCCCCCCC CCCCCCCC 00000010 00000020 00000030
    #
    #    So find an address that contains CCCCCCCC followed by 4 bytes that are
    #    not CCCCCCCC. For each address we try there are three possibilities
    #
    #      i)   The 8 bytes at that address equal CCCCCCCC CCCCCCCC, in which case
    #           we are in unused space and need to move towards the SP
    #      ii)  The 8 bytes do not contain the magic value, in which case we are
    #           in used space and need to move towards the stack limit
    #      iii) We have found CCCCCCCC followed by 4 bytes that are not CCCCCCCC
    #           and terminate the search
    #    Caveat: The STACK_MAGIC_WORD, if present, will trip us up as it doesn't
    #    match the cases above. Account for this when calculating the search space.
    if (Stacks.STACK_MAGIC_WORD != 0):
        stackLimit = stackLimit.addOffset(4)
    searchSpace = stackPtrNext.getLinearAddress() - stackLimit.getLinearAddress()
    candidate = stackLimit.addOffset((searchSpace // 2) - ((searchSpace // 2) % 4))
    while (searchSpace > 0):
        candidate_hi, candidate_lo = readAddress64(debugger, candidate)

        searchSpace = searchSpace // 2

        if   (candidate_lo == Stacks.STACK_WATERMARK_PATTERN and candidate_hi == Stacks.STACK_WATERMARK_PATTERN):
            #print "  test at %08X (%08X_%08X) misses (too low)" % (candidate.getLinearAddress(), candidate_hi, candidate_lo)
            candidate = candidate.addOffset((searchSpace + 4) - (searchSpace % 4))
        elif (candidate_lo == Stacks.STACK_WATERMARK_PATTERN or  candidate_hi == Stacks.STACK_WATERMARK_PATTERN):
            #print "  test at %08X (%08X_%08X) hits (returning %08X)" % (candidate.getLinearAddress(), candidate_hi, candidate_lo, candidate.addOffset(4).getLinearAddress())
            return candidate.addOffset(4)
        else:
            #print "  test at %08X (%08X_%08X) misses (too high)" % (candidate.getLinearAddress(), candidate_hi, candidate_lo)
            candidate = candidate.addOffset(-searchSpace - (searchSpace % 4))
    raise Exception("Failed to calculate maximum stack usage")

def getStackPositionAsPercentage(stackBase, stackSize, stackPos):
    stackTop  = stackBase.addOffset(stackSize).getLinearAddress()
    stackBase = stackBase.getLinearAddress()
    stackPos  = stackPos.getLinearAddress()

    # Stack has gone wrong
    if stackPos < stackBase or stackPos > stackTop:
        return createTextCell("")
    else:
        return createNumberCell((stackTop - stackPos) * 100 // stackSize)

# Creates the high-water mark cell. If enabled this is expressed as a percentage.
def makeStackWatermarkCell(debugger, stackBase, stackSize, stackPtr):
    # Check if the stack watermark feature is enabled (stored in os_stack_info)
    if (isStackUsageWatermarkEnabled(debugger)):
        highUsageAddr = calculateHighUsageAddr(debugger, stackBase, stackSize, stackPtr)
        return getStackPositionAsPercentage(stackBase, stackSize, highUsageAddr)
    else:
        return createTextCell("")

def makeStackAllocationCell(stackBase, stackSize):
    end = stackBase.addOffset(stackSize)
    return createTextCell(''.join([str(stackBase), " - ", str(end)]))

def makeStackLoadCell(stackBase, stackSize, stackPtr):
    return getStackPositionAsPercentage(stackBase, stackSize, stackPtr)

def makeStackSizeCell(stackSize):
    if (stackSize > 0):
        return createNumberCell(stackSize)
    return createNumberCell(None)

# RTX places a magic word (by default 0xE25A2EA5) at the bottom of the
# stack to aid with overflow detection. Use presence of this value to
# indicate stack overflow.
def makeStackOverflowCell(debugger, stackBase):
    # If the MAGIC_WORD wasn't setup, we can't tell if it has overflowed.
    # Otherwise overflow has occurred if the stack limit is not the MAGIC_WORD
    if (Stacks.STACK_MAGIC_WORD == 0 or readAddress32(debugger, stackBase) == Stacks.STACK_MAGIC_WORD):
        return createTextCell("")
    else:
        return createTextCell("OVERFLOW")
