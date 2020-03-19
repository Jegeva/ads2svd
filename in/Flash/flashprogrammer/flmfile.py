from symfile import SymbolFileReader
from com.arm.imagereaders.elf import Elf_Sym
from struct import unpack
from itertools import izip, takewhile

import java.io.File

class FlmFileReader(SymbolFileReader):

    def __init__(self, file):
        # SymbolFileReader requires java File object
        if isinstance(file, str) or isinstance(file, unicode):
            file = java.io.File(file)
        SymbolFileReader.__init__(self, file)
        self.__flashDeviceInfo = {}

    def getFlashDeviceInfo(self):
        '''Reads the flash device information from the symbol file and returns
        the information in a dictionary'''
        if not self.__flashDeviceInfo:
            self.__flashDeviceInfo = self.__readFlashDeviceInfo()

        return self.__flashDeviceInfo

    def formatFlashDeviceInfoEntry(self, name, val):
        '''format an entry in the flash device info for display to the user
        '''

        # map of parameter name to formatter
        # formatter may be string formatting template or function that will format
        # the entry
        fmts = {
                'address': '0x%08x',
                'size': '0x%08x',
                'programPageSize': '0x%x',
                'valEmpty': '0x%x',
                'sectorSizes': lambda s: '(' + ', '.join('(0x%x, 0x%08x)' % i for i in s) + ')'
                }

        if name in fmts:
            # custom formatter available
            formatter = fmts[name]
            if callable(formatter):
                return formatter(val)
            else:
                return formatter % val
        else:
            # fall back to str()
            return str(val)


    def __readFlashDeviceInfo(self):
        '''returns the flash device info read from a keil flash algorithm'''
        objects = self._make_symbol_subtable(Elf_Sym.STT_OBJECT, self.__make_obj)
        flash_device_desc = objects['FlashDevice']
        dev_desc_sec = self.getSectionTable()[flash_device_desc['ndx']]['offset']
        data = self.readBytes(dev_desc_sec, flash_device_desc['size'])
        return self.__unpack_dev_desc(data)

    def getOffsetToNextSector(self, address):
        '''returns the size of the sector that this address is within, if the
        address is part way through the sector then the number of bytes from
        address to end of sector is returned'''
        sectorSize = 0
        nextOffset = self.getFlashDeviceInfo()['size']
        deviceOffset = address - self.getFlashDeviceInfo()['address']

        for size, sectorOffset in self.getFlashDeviceInfo()['sectorSizes']:
            if sectorOffset <= deviceOffset:
                sectorSize = size
            else:
                nextOffset = sectorOffset
                break

        val = min((nextOffset - deviceOffset), sectorSize)
        if val == 0:
            val = sectorSize

        return val


    def __make_obj(self, sym):
        return {
                'ndx':sym.st_shndx,
                'size':sym.st_size,
               }


    def __unpack_dev_desc(self, desc):
        dev = {}
        # TODO - endianness (here '<' = little endian) is in elf header
        raw = unpack('<H128sH4I4B2I1024I', desc)
        return {
                'driverVersion':raw[0],
                'name':raw[1].replace('\0', ''),
                'type':raw[2],
                'address':raw[3],
                'size':raw[4],        # in bytes
                'programPageSize':raw[5],
                'valEmpty':raw[7],
                'programPageTimeout':raw[11],
                'eraseSectorTimeout':raw[12],
                'sectorSizes':self.__decode_sectors(raw[13:]) # size,address
               }


    def __decode_sectors(self, raw):
        'tuple of pairs (szSector, AddrSector)'
        END = (0xFFFFFFFF, 0xFFFFFFFF)
        return tuple(takewhile(lambda x: x != END, self.__pairs(raw)))


    def __pairs(self, seq):
        's -> (s0,s1), (s2,s3),...'
        i = iter(seq)
        return izip(i, i)