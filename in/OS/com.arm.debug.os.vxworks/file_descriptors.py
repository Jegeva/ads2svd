# Copyright (C) 2017 Arm Limited (or its affiliates). All rights reserved.

"""
Implementation of OS support for Wind River VxWorks RTOS
"""

from osapi import *
from utils import *

class FileDescriptors(Table):

    def __init__(self):

        cid = "fd"

        fields = [ createPrimaryField( cid, "id", ADDRESS ) ]

        fields.append( createField( cid, "device", TEXT ) )
        fields.append( createField( cid, "name", TEXT ) )
        fields.append( createField( cid, "refcnt", DECIMAL ) )
        fields.append( createField( cid, "handles", TEXT ) )
        fields.append( createField( cid, "flags", TEXT ) )
        fields.append( createField( cid, "value", ADDRESS ) )

        Table.__init__( self, cid, fields )

    def readRecord(self, debugSession, fdPtr, rtpFdMap):
        fd = fdPtr.dereferencePointer().getStructureMembers()

        fdAddr = fdPtr.readAsAddress()

        # Read device information if available.
        if fd['pDevHdr'].readAsNumber():
            devName = getClassName(fd['pDevHdr'].dereferencePointer())
        else:
            devName = None

        # Read file path (what this means is driver specific).
        path = getClassName(fd['objCore'], defaultName=None)

        # Read the file descriptor properties.
        refcnt = fd['refCnt'].readAsNumber()
        flags = getFlagString(fd['flags'].readAsNumber())
        value = fd['value'].readAsAddress()

        # Build the string describing the open handles per each RTP.
        if fdAddr.getLinearAddress() in rtpFdMap:
            rtpFds = rtpFdMap[fdAddr.getLinearAddress()]
            handles = ', '.join(['%d:%d' % (fd[0], fd[1]) for fd in rtpFds])
        else:
            handles = None

        # Submit the cells.
        cells = []
        cells.append(createAddressCell(fdAddr))
        cells.append(createTextCell(devName))
        cells.append(createTextCell(path))
        cells.append(createNumberCell(refcnt))
        cells.append(createTextCell(handles))
        cells.append(createTextCell(flags))
        cells.append(createAddressCell(value))

        return self.createRecord( cells )

    def getRecords(self, debugSession):
        fdPtrList = readFileDescriptorList(debugSession)
        rtpFdMap = constructRtpFdMap(debugSession)
        return [ self.readRecord(debugSession, fdPtr, rtpFdMap) for fdPtr in fdPtrList ]

def constructRtpFdMap(debugger):
    """
    @brief  Constructs a map of the linear address of each open file descriptor
            object to the tuple of RTP identifier and the file descriptor number
            the file is open with in that RTP.
    @param  debugger   DebugSession to retrieve the RTP list on.
    @return Dictionary mapping linear addresses (longs) to a tuple of RTP ID
            (long) and file descriptor number (long).
    """
    # Get the list of all RTPs
    rtpList = readRTPList(debugger)
    ulType = debugger.resolveType('unsigned long')
    rtpFdMap = {}
    # Process all current RTPs.
    for rtpId, rtp in rtpList:
        # Read the file descriptor table size.
        fdTableSize = rtp['fdTableSize'].readAsNumber()
        # Continue if this is non-zero and the file descriptor table is present.
        if fdTableSize and rtp['fdTable'].readAsNumber():
            # rtp.fdTable is an FD_ENTRY** but stored as a void* - so some
            # juggling is required to cast it to the correct type. This is
            # additionally complicated by the fact that many of the pointed-at
            # pointers will be 0 or ~1, so cannot be dereferenced. Instead we
            # dereference and cast to an unsigned long* which we then read as
            # an array (making use of the fact that an unsigned long has the
            # same size as a pointer).
            fdEntryPtrs = debugger.constructPointer(ulType, rtp['fdTable'].readAsAddress()).getArrayElements(fdTableSize)
            # Iterate through all entries in the file descriptor table.
            for fd in range(len(fdEntryPtrs)):
                fdEntryPtr = fdEntryPtrs[fd].readAsNumber()
                # If the entry is present, add it to that FD's handle-mappings.
                if fdEntryPtr:
                    if fdEntryPtr in rtpFdMap:
                        rtpFdMap[fdEntryPtr].append((rtpId, fd))
                    else:
                        rtpFdMap[fdEntryPtr] = [(rtpId, fd)]
    return rtpFdMap

def getFlagString(flags):
    """
    @brief  Returns a string describing a file's flags.
    @param  flags   The flags integer.
    @return string describing the enabled flags.
    """
    flagList = []
    if flags & 0x2:
        flagList.append('RDWR')
    elif flags & 0x1:
        flagList.append('WRONLY')
    else:
        flagList.append('RDONLY')
    if flags & 0x200:
        flagList.append('CREAT')
    if flags & 0x800:
        flagList.append('EXCL')
    if flags & 0x2000:
        flagList.append('SYNC')
    if flags & 0x10000:
        flagList.append('DSYNC')
    if flags & 0x20000:
        flagList.append('RSYNC')
    if flags & 0x8:
        flagList.append('APPEND')
    if flags & 0x4000:
        flagList.append('NONBLOCK')
    if flags & 0x8000:
        flagList.append('NOCTTY')
    if flags & 0x400:
        flagList.append('TRUNC')
    return ' | '.join(flagList)
