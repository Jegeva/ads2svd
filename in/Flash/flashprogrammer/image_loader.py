
from device_memory import *
from symfile import *

from com.arm.imagereaders.elf.arm import ArmElf_Phdr
from com.arm.imagereaders.elf import Elf_Shdr

def loadCodeSegmentToTarget(core, data, offset, dict):
    '''Loads a code segment to the target

    core - a DTSL Device
    data - a byte array to be written to the target
    offset - an offset applied to the code segments base address
    dict - a python dictionary containing data about the segment
        addr - the base address of the segment
        sz - the size of the segment (in bytes)'''
    writeToTarget(core, offset+dict['addr'], data, dict['sz'])

def loadAllCodeSegmentsFromFileToTarget(core, file, offset=0):
    '''Reads all the code segments from an ELF file and writes them to the target
    using loadCodeSegmentToTarget.

    core - a DTSL device
    file - an ELF file
    offset - optional offset to apply to segment base addresses
    '''
    symbolReader = SymbolFileReader(file)
    return loadAllCodeSegmentsToTarget(core, symbolReader, offset)

def loadAllCodeSegmentsToTarget(core, symbolReader, offset=0):
    '''Gets all the code segments from a SymbolFileReader and writes them to
    the target using loadCodeSegmentToTarget.

    core - a DTSL device
    symbolReader - an instance of SymbolReader
    offset - optional offset to a apply to segment base addresses
    '''
    segments = symbolReader.getLoadSegments();

    for segment in segments:
        buf = symbolReader.loadSegmentIntoBuffer(segment)
        loadCodeSegmentToTarget(core, buf, offset, segment)

def getStaticBase(symbolReader, offset=0):
    '''Get the segment containing the static base

    images with position independent read/write data need R9 set to point to the
    location where the section is located

    return None if no segment contains the static base'''

    segments = symbolReader.getLoadSegments();
    for segment in segments:
        # static base is indicated by PF_ARM_SB and PF_ARM_PI flags in segment header
        flags = segment['flags']
        if ((flags & ArmElf_Phdr.PF_ARM_SB) != 0 and
            (flags & ArmElf_Phdr.PF_ARM_PI)):
            # got the segment containing the static base -
            # there's nothing in the ELF file that says which section in this
            # segment actually is the static base - assume the first writable
            # section is the static base
            for section in symbolReader.getSectionTable():
                sectAddr = section['addr']

                if ((section['flags'] & Elf_Shdr.SHF_WRITE) != 0 and
                    sectAddr >= segment['addr'] and
                    sectAddr < (segment['addr'] + segment['sz'])):
                    return offset + section['addr']

    # None found
    return None