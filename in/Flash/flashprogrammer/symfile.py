from jarray import zeros
from java.io import File, FileInputStream
from com.arm.imagereaders.elf import ElfFileReader
from com.arm.imagereaders.elf import Elf_Sym
from com.arm.imagereaders.elf import Elf_Shdr
from com.arm.imagereaders.elf import Elf_Phdr
from org.python.modules.jarray import zeros

class SymbolFileReader(ElfFileReader):
    '''Extends the ELFFileReader to obtain all of the symbol information from an
    ELF file'''

    def __init__(self, file):
        '''Instantiates a SymbolFileReader that can read symbols from the
        supplied ELF file.'''
        ElfFileReader.__init__(self, file)
        self.__source_filename = file.getAbsolutePath()
        self.__function_info = None
        self.__programHeaders = None

    def getSourceFilename(self):
        '''Returns the name of the file from which the symbol information is
        being read'''
        return self.__source_filename;

    def getSectionTable(self):
        '''Returns a table of all the sections declared in the ELF file

        TODO'''
        return self.__make_header_sectiontable(self.__make_section)
        return buf

    def _make_symbol_subtable(self, type, construct):
        '''make a name->value map of symbols matching type
           construct extracts useful information specific to the type'''
        st = self.__symbol_table()
        syms = self.__extract_symbols(st, lambda s: s.st_type() == type)
        return dict((name.encode('utf-8'), construct(sym)) for (name, sym) in syms.items())

    def __make_func(self, sym):
        '''Creates a dictionary of values applicable to a section representing
        a function'''
        return {
                'address':sym.st_value & 0xFFFFFFFE,
                'thumb':(sym.st_value & 1) != 0,
                'ndx':sym.st_shndx,
                'size':sym.st_size,
               }

    def __symbol_table(self):
        return [h for h in self.readSectionHeaders() if h.sh_type == Elf_Shdr.SHT_SYMTAB][0]

    def __make_header_sectiontable(self, construct):
        '''Returns a name->value map of symbols matching type
           construct extracts useful information specific to the type'''
        headers = self.readSectionHeaders()
        stringtable = self.getSectionHeaderStringTable();
        return [x for x in ((construct(header, stringtable)) for (header) in headers)]

    def __make_section(self, sym, stringtable):
        '''Creates a dictionary detailing the section header for the supplied
        symbol.

        sym - a symbol
        stringtable - a reference to the ELF files string table

        returns a dictionary detailing the supplied symbol
        '''
        return {
                'name':sym.getName(stringtable).encode('utf-8'),
                'type':sym.sh_type,
                'flags':sym.sh_flags,
                'addr':sym.sh_addr,
                'offset':sym.sh_offset,
                'sz':sym.sh_size,
                'lnk':sym.sh_link,
                'inf':sym.sh_info,
                'align':sym.sh_addralign,
                'sz_e':sym.sh_entsize
               }

    def __extract_symbols(self, symbols, predicate=None):
        result = {}
        def callback(sym, stringTable, index):
            if predicate is None or predicate(sym):
                result[sym.getName(stringTable)] = sym
            return True
        self.processSymbolTable(symbols, callback)
        return result

    def readBytes(self, offset, length):
        '''Reads bytes from the ELF file starting at the supplied offset.

        offset - an offset into the file
        length - the number of bytes to be read

        returns the data in a byte array'''
        buf = zeros(length, 'b')
        fis = FileInputStream(self.__source_filename)
        fis.skip(offset)
        fis.read(buf)
        fis.close()
        return buf

    def getFunctionInfo(self):
        '''make a name->value map of function symbols.  The value contains -

        address - address of the function
        thumb - boolean value set to true for thumb mode
        ndx - index into section header table
        size - size of the function in memory

        returns a name->value map of functions
        '''
        if self.__function_info == None:
            self.__function_info = self._make_symbol_subtable(Elf_Sym.STT_FUNC, self.__make_func)

        return self.__function_info

    def loadSectionIntoBuffer(self, section):
        '''Copies the supplied section from the ELF file to a byte buffer.

        section - the section to be read from the ELF file

        returns a byte buffer containing the section'''
        return self.readBytes(section['offset'], section['sz'])

    def getCodeSectionsTable(self):
        '''returns a list of sections containing all functions defined in the ELF file'''
        func_infs = self.getFunctionInfo()
        sections = dict(((func_infs[name])['ndx'], self.getSectionTable()[(func_infs[name])['ndx']]) for name in func_infs)
        return sections

    def getLoadSegments(self):
        '''Reads the ELF program section header table, discarding any with a size
        of zero.

        offset - the offset from the beginning of the file at which the first byte
        of the segment resides
        sz - number of bytes in the memory image of the segment
        addr - physical address at which the first byte of the segment resides in memory

        returns an array of dictionaries detailing all segments in ELF file'''
        if self.__programHeaders is None:
            self.__programHeaders = self.readProgramHeaders()

        return [{'offset':x.p_offset, 'sz':x.p_filesz, 'addr':x.p_paddr, 'flags':x.p_flags} for x in self.__programHeaders if x.p_memsz != 0]


    def getLoadSegmentsAddressRange(self):
        '''returns an array with the upper and lower addresses of the load segments
        in the ELF file'''
        lowerAddr = min(segment['addr'] for segment in self.getLoadSegments())
        upperAddr = max((segment['addr']+segment['sz']) for segment in self.getLoadSegments())
        return (lowerAddr, upperAddr)


    def loadSegmentIntoBuffer(self, segment_data):
        '''Loads a segment from the ELF file into a buffer.

        segment_data - information about the segment, expected keys are -
            offset - offset from the beginning of the file at which the first
            byte of the segment resides
            sz - number of bytes in the memory image of the segment

        returns a buffer containing the data requested'''
        phdr = Elf_Phdr(0, 0, segment_data['offset'], 0, 0, segment_data['sz'], 0, 0)
        phdr.p_offset = segment_data['offset']
        phdr.p_filesz = segment_data['sz']

        segment = self.getSegment(phdr)

        buf = zeros(segment.length(), 'b')
        segment.readFully(buf)
        return buf
