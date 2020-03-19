from __future__ import with_statement

from java.lang import Runnable

import threading


class TraceDataConsumer(Runnable):
    """A class to push a block of data through a processing pipeline - normally
       done within a thread.
    """
    def __init__(self, dataSink):
        """Construction giving us our data sink - i.e. where we send the
           unprocessed trace data
        """
        self.dataSink = dataSink
        self.dataSet = None
        self.byteCount = 0
        self.exception = None
        self.accessLock = threading.Lock()

    def getException(self):
        """Returns any exception thrown within the run() method
        Returns:
            an exception or None if no exception was thrown within run()
        """
        with self.accessLock:
            return self.exception

    def setDataset(self, dataSet, byteCount):
        """Notifies us of the data set which is to processed when we run
        Params:
            dataSet - the data to be passed to the dataSink
            byteCount - the number of bytes in the data set
        """
        self.dataSet = dataSet
        self.byteCount = byteCount

    def run(self):
        """The method which pushes the data through the processing pipeline
        """
        try:
            self.dataSink.push(0, self.byteCount, self.dataSet)
        except Exception, e:
            with self.accessLock:
                self.exception = e
