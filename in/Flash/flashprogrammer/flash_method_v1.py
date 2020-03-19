# Copyright (C) 2018 Arm Limited (or its affiliates). All rights reserved.
from com.arm.debug.flashprogrammer import FlashMethodv1_Base

class FlashMethodv1(FlashMethodv1_Base):
    def __init__(self, methodServices):
        FlashMethodv1_Base.__init__(self, methodServices)

    def getClient(self):
        '''
        Returns the flash client.  The flash programmer uses this interface to
        get data from the client and report status.

        see com.arm.debug.flashprogrammer.IFlashClient
        '''
        return self.super__getClient()

    def getClientServices(self):
        '''
        returns com.arm.debug.flashprogrammer.IFlashClientServices
        '''
        return self.super__getClientServices()

    def getRegions(self):
        '''
        see com.arm.debug.flashprogrammer.IFlashRegion

        returns a list of regions available to the flash method
        '''
        return self.super__getRegions()

    def getRegion(self, idx):
        '''
        This is a convenience method to simplify the extraction of individual
        regions available to the flash method.

        see com.arm.debug.flashprogrammer.IFlashRegion

        returns the region at idx of the list returned by getRegions
        '''
        return self.super__getRegion(idx)

    def getParameters(self):
        '''
        returns a list of parameters (name value pairs) available to the flash
        method
        '''
        return self.super__getParameters()

    def getParameter(self, name):
        '''
        This is a convenience method to simplify the extraction of individual
        parameters for the flash method.

        returns the named parameter from the flash method
        '''
        return self.super__getParameter(name)

    def locateFile(self, path):
        '''
        Resolves the supplied file path.

        returns the absolute path to file
        '''
        return self.super__locateFile(path)

    def getConnection(self):
        '''Get a DTSL connection to the system being programmed

        As not all flash programming methods will require a DTSL connection (e.g.
        when using an external tool), it is not necessary to create a connection
        before starting programming.  Instead, programming methods will call this
        method to obtain the DTSL connection when required.

        Clients may re-use an existing connection to a system if they already
        have one open, otherwise they must open a new connection.

        returns a connection to the system being programmed.
        '''
        return self.super__getConnection();

    def operationStarted(self, message, size):
        '''Informs the client that an operation has started

        Each programming request may comprise several operations (e.g. erase,
        program, verify).

        size indicates the amount of work the operation will perform. No units
        are implied e.g. it may be a byte count or a percentage. Clients
        should use this for progress indicators

        Clients should return an {@link IProgress} object to receive progress
        information.  A client may return null if it does not want to receive
        progress information.  If the client does return null, then a default
        implementation will be provided to the method script - this avoids it
        having to check for the progress object being null

        message - Localised message describing operation
        size - The size of the operation, -1 for indeterminate
        returns client's implementation of IProgressJob to receive progress state'''
        return self.super__operationStarted(message, size)

    def subOperation(self, parent, message, size, parentSize):
        '''Informs the client a sub operation has been started

        The client should return an {@link IProgress} implementation to track
        progress of this sub operation

        parentSize indicates how much of the parent's progress will be consumed
        by the sub operation.  Clients may use scale this value with the completed
        proportion of the sub operation to provide overall progress

        Clients should return an {@link IProgress} object to receive progress
        information.  A client may return null if it does not want to receive
        progress information.  If the client does return null, then a default
        implementation will be provided to the method script - this avoids it
        having to check for the progress object being null

        parent - The progress object that this sub-operation is a child of
        message - Localised message describing operation
        size - The size of the operation, -1 for indeterminate
        parentSize - The amount of progress in the parent this operation will consume

        returns Client's Implementation of IProgressJob to receive progress state'''
        return self.super__subOperation(parent, message, size, parentSize)

    def message(self, level, message):
        '''Message to client

        Called to pass messages to the client to be displayed to the user

        level indicates the severity of the message: debug is not normally to be
        displayed
        info is general information (e.g. which section is
        being loaded); warning is for abnormal event that should be drawn to the
        users attention, but aren't severe enough to be considered an error

        level - The severity of the message
        message - Localised message'''
        self.super__message(level, message)

    def debug(self, message):
        '''Debug message to client

        Called to pass debug information to the client to be displayed to the
        user if the client chooses to do so - debug information is not normally
        to be displayed

        message - Localised message'''
        self.super__debug(message)

    def info(self, message):
        '''Message to client

        Called to pass information to the client to be displayed to the
        user

        message - Localised message'''
        self.super__info(message)

    def warning(self, message):
        '''Warning to client

        Called to pass a warning to the client to be displayed to the
        user

        message - Localised message'''
        self.super__warning(message)

    def isCancelled(self):
        '''Allow method to check for user cancellation

        Flash programming methods will poll this at intervals if they are
        cancellable.  Clients can return true to indicate programming is to be
        cancelled.  The method will stop the current operation at a suitable
        point and return control to the client.  The client should call
        IFlashProgrammer#close() to clean up.

        returns true if flash programming is to be cancelled'''
        return self.super__isCancelled()

    def confirmOperation(self, message):
        '''Callback to confirm an operation with the user

        Some targets may required manual reset/power cycle - this allows the
        programmer to show a prompt to the user to instruct them to do this and
        confirm when complete

        Clients should display a prompt with "OK" & "Cancel" options

        message - Localised prompt message
        returns true if user confirmed operation, false if cancelled'''
        return self.super__confirmOperation(message)

    def getDefaultRegions(self):
        '''Get flash regions for the method

        Flash methods may provide information about flash regions to avoid
        duplication in script files, config xml or algorithm binaries.

        This may be expensive to call, e.g. extracts data from a algorithm binary,
        so callers should not call this more than necessary

        returns list of flash regions
        throws FlashProgrammerException on error'''
        return FlashMethodv1_Base.getDefaultRegions(self)

    def getSectors(self):
        ''' Get device sectors for the method

        returns list of sectors'''
        return FlashMethodv1_Base.getSectors(self)

    def getDefaultParameters(self):
        '''Get default parameter values for the method

        Flash methods may provide default parameters for the method to avoid
        duplication in script files, config xml or algorithm binaries.

        This may be expensive to call, e.g. extracts data from a algorithm binary,
        so callers should not call this more than necessary

        returns List of flash regions
        throws FlashProgrammerException on error'''
        return FlashMethodv1_Base.getDefaultParameters(self)

    def setup(self):
        '''Perform any one time setup required by the method

        throws FlashProgrammerException on error'''
        FlashMethodv1_Base.setup(self)

    def teardown(self):
        '''Cleanup after the method has finished

        returns target status
        throws FlashProgrammerException on error'''
        return FlashMethodv1_Base.teardown(self)

    def program(self, regionIndex, offset, data, allowFullChipErase=True):
        '''Program a block of data into the flash device

        regionIndex  - index of the region to program
        offset - offset into the flash device region
        data - data to program
        allowFullChipErase - if the whole chip is allowed to be erased when programming

        returns target status
        throws FlashProgrammerException on error'''
        return FlashMethodv1_Base.program(self, regionIndex, offset, data, allowFullChipErase)

    def postErase(self):
        '''Called after erasing is complete but before
        programming
        '''
        return self.super__postErase()

    def postProgram(self):
        '''Called after programming is complete but before
        verification
        '''
        return self.super__postProgram()

    def postVerify(self):
        '''Called after verification is complete
        '''
        return self.super__postVerify()
