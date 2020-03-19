# Copyright (C) 2017-2018 Arm Limited (or its affiliates). All rights reserved.
"""
USECASE

$Title$ DTSL Trace Stats

$Description$ Usecase Script to analyse a (DSTREAM) trace buffer.

$Options$ options

$Validation$ validate

$Run$ main

$Help$
Usecase script to analyse a (DSTREAM) trace buffer full of TPIU content
(or rather CoreSight Trace Formatter content) and let us know which
trace sources are present in the buffer.
$Help$
"""

from tracedataconsumer import TraceDataConsumer
from statstracesink import StatsTraceSink

from com.arm.debug.dtsl import ConnectionManager
from com.arm.debug.dtsl import DTSLException
from com.arm.debug.dtsl.impl import Deformatter
from com.arm.debug.dtsl.impl import PipelineStageBase
from com.arm.debug.dtsl.impl import SyncStripper
from com.arm.debug.dtsl.interfaces import ITraceCapture

from arm_ds.debugger_v1 import Debugger
from com.arm.rddi import RDDIException
from org.python.core import PyException
from progress import Progress
from DTSLHelper import findDTSLTraceSourceForATBID, formRateString, formTraceSizeString, getDTSLTraceCaptureDevice, showDTSLException, \
                       showDTSLTraceCaptureDevices, showDTSLTraceSourcesForCaptureDevice, showJythonException, showRDDIException

from jarray import zeros
from java.lang import StringBuilder
from java.lang import Thread
from java.lang.System import nanoTime
from java.util import HashMap
import os
import sys


def getDTSLConfiguration(debugger):
    """ Returns the DTSL configuration object
        currently being used by the Arm DebuggerTraceDataProcessor
    Parameters:
        debugger - the Arm Debugger interface
    """
    dtslConnectionConfigurationKey = debugger.getConnectionConfigurationKey()
    dtslConnection = ConnectionManager.openConnection(
        dtslConnectionConfigurationKey)
    return dtslConnection.getConfiguration()


def getDTSL():
    """For an existing Arm DS connection, we return the DTSL connection
    Returns:
        the DTSLConnection instance
    """
    debugger = Debugger()
    dtslConfigurationKey = debugger.getConnectionConfigurationKey()
    dtslConnection = ConnectionManager.openConnection(dtslConfigurationKey)
    return dtslConnection


def buildTraceSourcePipeline(captureDevice, atbRangeStart, atbRangeEnd):
    """ Create a trace processing pipeline which terminates in a
        collection of StatsTraceSink objects - one for each possible
        trace ATBID value.
    Params:
        captureDevice - the trace capture device used to capture the
                        raw trace
    Returns:
        An array of IDataPipelineStage objects (does not include the
        StatsTraceSink objects) and a Map which maps ATBID to the
        StatsTraceSink object
    """
    targetsAndDestinations = HashMap()
    for atbid in range(atbRangeStart, atbRangeEnd):
        statsTraceSync = StatsTraceSink(findDTSLTraceSourceForATBID(captureDevice, atbid))
        targetsAndDestinations.put(atbid, statsTraceSync)
    deformatter = Deformatter(targetsAndDestinations)
    syncStripper = SyncStripper(deformatter)
    pipeline = [syncStripper, deformatter]
    return pipeline, targetsAndDestinations


def processTraceData(captureDevice, traceDataSink, progress, readSize):
    """Reads trace data from a capture device and sends it to a trace
       data sink
    Params:    syncStripper = SyncStripper(statsTraceSync)

        captureDevice - the trace capture device we read from
        traceDataSink - the trace sink to which we send the data (note that
                        this is typically the first stage of a multi-stage
                        data processing pipeline)
        progress - the Progress object we update with our progress
    """
    # We read trace data on the current thread and process the trace data
    # on another thread. This lets us overlap the reading and processing
    # of trace data
    # Get a trace reader which returns us CAPTURED data i.e. any capture
    # device specific formatting has been removed
    traceReader = captureDevice.borrowSourceReader(
        "traceStats", ITraceCapture.CAPTURED_DATA)
    try:
        MAX_READ_SIZE = readSize
        MAX_PROCESS_SIZE = captureDevice.getMaxCaptureSize()
        print("Reading trace in chunks of %s" % formTraceSizeString(MAX_READ_SIZE))
        # Have 2 data blocks - one we fill with data whilst the other is being
        # processed by the processing thread
        dataBlocks = [zeros(MAX_READ_SIZE, 'b'), zeros(MAX_READ_SIZE, 'b')]
        blockID = 0
        captureSize = captureDevice.getCaptureSize()
        processSize = min(captureSize, MAX_PROCESS_SIZE)
        # Create our Runnable trace data processing object
        dataProcessor = TraceDataConsumer(traceDataSink)
        processingThread = None
        # We start reading at a point 'processSize' back from the end of the
        # buffer
        nextPos = zeros(1, 'l')
        nextPos[0] = captureSize-processSize
        traceDataProcessed = 0
        progress.setCurrentOperation("Uploading trace data")
        progress.setRange(0, processSize)
        sourceTotal = 0
        startTime = nanoTime()
        while processSize > 0:
            readSize = min(processSize, MAX_READ_SIZE)
            sourceByteCount = traceReader.read(
                nextPos[0], readSize, dataBlocks[blockID], nextPos)
            sourceTotal += sourceByteCount
            if sourceByteCount > 0:
                # If we have a previous decode thread then we must wait for it
                # to have completed
                if processingThread is not None:
                    processingThread.join()
                # Inform data processor of new data set
                dataProcessor.setDataset(dataBlocks[blockID], sourceByteCount)
                # Get data processor run in a new thread
                processingThread = Thread(dataProcessor)
                processingThread.start()
            # Switch buffer blocks to the 'other one'
            blockID = 1 - blockID
            processSize -= readSize
            traceDataProcessed += readSize
            progress.setProgress(traceDataProcessed)
        # Make sure all data has been processed
        if processingThread is not None and processingThread.isAlive():
            processingThread.join()
        traceDataSink.flush()
        # Lets see how long that all took
        timeDelta = nanoTime() - startTime
        if timeDelta > 0:
            time = timeDelta * 1.0E-9
            progress.setCompleted(
                "Processing complete, took %.2fs at %s" % (
                    time, formRateString(traceDataProcessed, time)))
        else:
            progress.setCompleted("Processing complete")
        print "Read %s from trace buffer" % formTraceSizeString(sourceTotal)
    finally:
        # We must always return the reader to the capture device
        captureDevice.returnSourceReader(traceReader)


def createConnectedDTSL(options):
    """ Creates a connection to DTSL and returns the connection object
    Params:
        options - our processed command line options from which we can get
                  the DTSL connection parameters
    """
    dtslConfigData = options.getDTSLConfigData()
    params = dtslConfigData.getDTSLConnectionParameters()
    print "Connecting to DTSL ...",
    startTime = nanoTime()
    conn = ConnectionManager.openConnection(params)
    conn.connect()
    timeDelta = nanoTime() - startTime
    if timeDelta > 0:
        timeS = timeDelta * 1.0E-9
        print "done, connection took %.2fs" % (timeS)
    else:
        print "done"
    return conn


def setupLogging(logLevel):
    from com.arm.debug.logging import LogFactory
    LogFactory.changeLogLevel(logLevel)  # use DEBUG for lots of logging


def doFullTraceAnalysis(captureDevice, progress, options):
    """ Does a full analysis of the trace capture device content to generate
        a report showing the present ATB IDs and how much trace data is
        presents for each of the ATB IDs. This can take a long time!
    Params:
        captureDevice - the DTSL TraceCapture object we use to access
                        the trace data
        progress - the object we use to report progress
    """
    atbRangeStart = options.getOptionValue("options.traceOptions.atbRangeStart")
    atbRangeEnd = options.getOptionValue("options.traceOptions.atbRangeEnd")
    pipeline, targetsAndDestinations = buildTraceSourcePipeline(captureDevice, atbRangeStart, atbRangeEnd)
    readSize = options.getOptionValue("options.traceOptions.readSize")
    processTraceData(captureDevice, pipeline[0], progress, readSize)
    for pipelineStage in pipeline:
        stageName = pipelineStage.toString().split('@')[0]
        counterValues = pipelineStage.collectCounterValues()
        print "%s received %s" % (
            stageName,
            formTraceSizeString(
                counterValues.get(PipelineStageBase.RECEIVED_DATA)
                ))
    print "Trace Stats Report:"
    print "+------------------+------------------+"
    print "|      ATB ID      |       Size       |"
    print "+------------------+------------------+"
    for atbid in targetsAndDestinations.keySet():
        target = targetsAndDestinations[atbid]
        counterValues = target.collectCounterValues()
        byteCount = counterValues.get(
            PipelineStageBase.RECEIVED_DATA)
        traceSource = target.getDTSLTraceSource()
        if byteCount > 0:
            if traceSource is None:
                sourceName = "%d" % atbid
            else:
                sourceName = "%s[%d]" % (
                    traceSource.getName(), atbid)
            print "| %16s | %16s |" % (
                sourceName.center(16),
                formTraceSizeString(byteCount).center(16))
    print "+------------------+------------------+"


def getBucketSize(targetSize):
    """ Returns valid bucket size for a requested target size.
        The smallest allowed bucket size is 2K and a valid size
        is a power of 2. So we return:
            bucketSize = 2^n > targetSize > 2^(n-1)
    Params:
        targetSize -
    """
    # Min allowed bucket size if 2K
    if targetSize < 2048:
        return 2048
    # Check if already a power of 2
    if (targetSize & (targetSize-1)) == 0:
        return targetSize
    # while not a power of 2 ...
    while (targetSize & (targetSize-1)) != 0:
        # remove lowest set bit
        targetSize = targetSize & (targetSize-1)
    # Left with power of 2 with all lower bits removed,
    # so we need next highest power of 2
    return 2*targetSize


def formSourceMapEntriesString(slots, presenceData):
    """ Forms a single 'line' of ATB ID location within the trace buffer
    Params:
        slots - how many display slots (characters) we should generate
        presenceData - a BitSet each bit set to true if trace data is
                       present for a slot
    Returns:
        a string with slots characters representing presence of trace data
        e.g. "X...XXXXXXXXXXXXX........XXXXXXXXXXXX......................."
    """
    sourceMapEntriesString = StringBuilder(slots)
    for bitPos in range(slots):
        if presenceData.get(bitPos):
            sourceMapEntriesString.append("X")
        else:
            sourceMapEntriesString.append(".")
    return sourceMapEntriesString.toString()


def doQuickTraceAnalysis(captureDevice, progress, options):
    """ Generates a report of ATB IDs present in the trace buffer
        along with a map of where the data resides in the trace buffer
    Params:
        captureDevice - the DTSL TraceCapture object we use to access
                        the trace data
        progress - the object we use to report progress
    """
    captureSize = captureDevice.getCaptureSize()
    if captureSize == 0:
        print "Trace capture device %s is empty" % captureDevice.getName()
        return
    # maxWidth gives the max character width of the ATB ID location map string
    # increasing this effectively zooms in the 'display'
    maxWidth = 128
    # bucketSize is the amount of trace buffer data represented by one bit
    # of returned dataPresence data
    bucketSize = getBucketSize(captureSize / maxWidth)
    # slots is the actual number of display characters we need for a line
    # of ATB ID location data
    slots = (captureSize + bucketSize - 1) / bucketSize
    print "Trace Buffer ATB ID Report:"
    print "+------------------+-%s-+" % ("".rjust(slots, "-"))
    print "|      ATB ID      | %s |" % ("Location within trace buffer content".center(slots, " "))
    print "+------------------+<0%s>+" % (formTraceSizeString(captureSize).rjust(slots-1,"-"))
    # Get the map of ATB IDs to the bit set of 'present in buffer' data
    # each bit of which covers a bucketSize chunk of trace data
    dataPresence = captureDevice.getTraceSearch().getSourceDataPresence(
        0, captureSize, bucketSize)
    # Now process the map one ATB ID one at a time, checking they are in the range requested
    atbRangeStart = options.getOptionValue("options.traceOptions.atbRangeStart")
    atbRangeEnd = options.getOptionValue("options.traceOptions.atbRangeEnd")
    for atbID in dataPresence.keySet():
        if(atbID >= atbRangeStart and atbID <= atbRangeEnd):
            traceSource = findDTSLTraceSourceForATBID(
                captureDevice, atbID)
            if traceSource is None:
                sourceName = "%d" % atbID
            else:
                sourceName = "%s[%d]" % (
                    traceSource.getName(), atbID)
            sourceMapEntries = formSourceMapEntriesString(
                slots, dataPresence.get(atbID))
            print "| %16s | %s |" % (sourceName.center(16), sourceMapEntries)
    print "+------------------+-%s-+" % ("".rjust(slots, "-"))

# Usecase options
def options():
    return [
        UseCaseScript.optionGroup(
            name="options",
            displayName="Options",
            childOptions=[
                UseCaseScript.optionGroup(
                name="traceOptions",
                displayName="Trace Options",
                childOptions=[
                    UseCaseScript.stringOption(
                        name="captureDevice",
                        displayName="The trace capture device name",
                        defaultValue="DSTREAM"),
                    UseCaseScript.integerOption(
                        name="atbRangeStart",
                        displayName="Start of range for ATB IDs",
                        defaultValue=0x1,
                        display=UseCaseScript.HEX),
                    UseCaseScript.integerOption(
                        name="atbRangeEnd",
                        displayName="End of range for ATB IDs",
                        defaultValue=0x70,
                        display=UseCaseScript.HEX),
                    UseCaseScript.integerOption(
                        name="readSize",
                        displayName="Maximum read size for a chunk of trace data from the capture device.",
                        defaultValue=0x100000,
                        display=UseCaseScript.HEX),
                ]),
                UseCaseScript.optionGroup(
                name="programOptions",
                displayName="Program Options",
                childOptions=[
                    UseCaseScript.booleanOption(
                        name="fullAnalysis",
                        displayName="Analyse for ATB IDs and quantity",
                        defaultValue=False),
                    UseCaseScript.booleanOption(
                        name="quiet",
                        displayName="Turns off the progress display",
                         defaultValue=False),
                    UseCaseScript.enumOption(
                        name="logging",
                        displayName="Logging level for this script",
                        values=[("INFO", "Default level of logging"), ("DEBUG", "Detailed logging")],
                        defaultValue="INFO"),
                ]),
            ]
        )
    ]

# Validation of the options provided to the usecase
def validate(options):
    # Check the range and definition of ATB IDs is valid
    atbStart = options.getOptionValue("options.traceOptions.atbRangeStart")
    atbEnd   = options.getOptionValue("options.traceOptions.atbRangeEnd")
    if(atbStart >= atbEnd):
        UseCaseScript.error("The start of the ATB ID range must be before the end of the ATB ID range")
    if(atbStart < 0x1):
        UseCaseScript.error("Invalid start of ATB ID range: %X. Start of the range must be >= 0x1" % atbStart)
    if(atbEnd > 0x70):
        UseCaseScript.error("Invalid end of ATB ID range: %X. End of the range must be <= 0x70" % atbEnd)

    # Check the read size is valid
    readSize = options.getOptionValue("options.traceOptions.readSize")
    if(readSize < 1):
        UseCaseScript.error("The trace capture device read size must be greater than 0")
    # Read size must be a power of 2
    if((readSize & (readSize - 1)) != 0):
        UseCaseScript.error("The trace capture device read size must be a power of 2")

# Define the main method/entry point for the usecase
def main(options):
    try:
        dtsl = None
        try:
            dtsl = getDTSL()
            dtslConfiguration = dtsl.getConfiguration()
            showDTSLTraceCaptureDevices(dtslConfiguration)
            showDTSLTraceSourcesForCaptureDevice(dtslConfiguration, options.getOptionValue("options.traceOptions.captureDevice"))
            captureDevice = getDTSLTraceCaptureDevice(dtslConfiguration, options.getOptionValue("options.traceOptions.captureDevice"))
            if captureDevice is not None:
                if captureDevice.isActive():
                    captureDevice.stop()
                progress = Progress(options.getOptionValue("options.programOptions.quiet"))
                progress.setOutputSupportsCR(False)
                setupLogging(options.getOptionValue("options.programOptions.logging"))
                if options.getOptionValue("options.programOptions.fullAnalysis"):
                    doFullTraceAnalysis(captureDevice, progress, options)
                else:
                    doQuickTraceAnalysis(captureDevice, progress, options)
        finally:
            if dtsl is not None:
                    dtsl.disconnect()
    except RDDIException, eRDDI:
        showRDDIException(eRDDI)
    except DTSLException, eDTSL:
        showDTSLException(eDTSL)
    except PyException, e:
        showJythonException(e)
    except RuntimeError, e:
        print >> sys.stderr, e
