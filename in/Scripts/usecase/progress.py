import sys


class Progress(object):
    '''Class to report % progress
     '''
    def __init__(self, quiet):
        # A text description of the current operation
        self.currentOperation = None
        # Holds the current progress value [rangeMin,rangeMax]
        self.curProgress = 0
        # Holds the value to associate with no progress (the 0% value)
        self.rangeMin = 0
        # Holds the value to associate with completed operation (the
        # 100% value)
        self.rangeMax = 100
        self.wasCancelled = False
        self.hadError = False
        # The length of the last output operation description string.
        # This allows us to always make sure we overwrite it with the next one.
        self.lastOperationStringLen = 0
        # Used to move the twirl through its states |/-\
        self.twirlState = 0
        self.outputSupportsCR = True
        self.quiet = quiet

    def setOutputSupportsCR(self, state):
        self.outputSupportsCR = state

    def setRange(self, minValue, maxValue):
        '''Sets the range of the progress bar
        Params:
            minValue the minimum value (usually 0)
            maxValue the maximum value
        '''
        self.rangeMin = minValue
        self.rangeMax = maxValue
        if (self.rangeMax <= self.rangeMin):
            self.rangeMax = self.rangeMin + 1
        self.curProgress = self.rangeMin

    def setProgress(self, curValue):
        '''Sets the current value of the progress bar
        Params:
            curValue the current value
        '''
        if (curValue < self.rangeMin):
            curValue = self.rangeMin
        elif (curValue >= self.rangeMax):
            curValue = self.rangeMax
        self.curProgress = curValue
        self.showProgress()

    def setCurrentOperation(self, curOperation):
        '''Sets the current operation being performed
        Params:
            curOperation text representation of the the current
                         operation
        '''
        # If we have been cancelled we dont allow updates to the
        # current operation text, it is left saying Cancellinsource "/home/tarmitst/work/workspace/DTSLTraceStats/Python/DTSLTraceStats.py"g ...
        if (not self.wasCancelled):
            self.currentOperation = curOperation
            self.showProgress()

    def setCompleted(self, info=None):
        '''Notifies us that the operation is now complete and provides
           some completion/info text for us to show to the user
        Params:
            info - the completion text to show to the user. This
                   can contain several lines \n separated.
        '''
        if (self.wasCancelled):
            # User did a cancel but the threaded client has not picked
            # the cancel request up. Since the client has now completed
            # we can act as if the client had acknowledged the cancel
            # request
            self.cancelled()
        else:
            # Normal client completion along with some info to show to the
            # user
            self.showCompletionInfo(info)

    def showCompletionInfo(self, info):
        '''Adds the completion information to the output
        Params:
            info - text to show for the completion info
        '''
        print
        print (info)
        sys.stdout.flush()

    def error(self, info):
        '''Notifies us that the operation has completed with an error
           and provides some completion/info text for us to show to the user
        Params:
            info the completion text to show to the user. This
                 can contain several lines \n separated.
        '''
        if self.currentOperation is None:
            self.currentOperation = ""
        self.currentOperation += " [FAILED]"
        self.showProgress()
        self.hadError = True
        self.showCompletionInfo(info)

    def warning(self, info):
        '''Notifies us that the operation has encountered a problem but
           it is ok to continue. The info text is for us to show to the user.
        Params:
            info - the warning text to show to the user. This
                   can contain several lines \n separated.
        '''
        print
        print("WARNING: " + info)
        sys.stdout.flush()

    def cancelled(self):
        '''Notifies the progress dialog  that the operation has been cancelled.
           Typically, the user has clicked the cancel button and that fact has
           been picked up by the worker code (by it calling wasCancelled()) and
           so the worker code is now notifying us that it has can cancelled
           the operation and so we can close the progress dialog.
        '''
        self.currentOperation += " [CANCELLED]"
        self.showProgress()
        self.wasCancelled = True

    def wasCancelled(self):
        '''Indicates if the user has cancelled the operation
        Returns:
            True iff has been cancelled by the user
        '''
        return self.wasCancelled

    def calcPercentProgress(self):
        '''Calculates the % complete based on the previously configured
           range and the current progress value.
        Returns:
            % complete [0,100]
        '''
        delta = self.rangeMax - self.rangeMin
        if (delta <= 0):
            return 0
        progress = self.curProgress - self.rangeMin
        return 100 * progress / delta

    def showProgress(self):
        '''Generates out progress display. This looks like:
            <nnn>% [+++++++++               ] <Current operation>
        '''
        if not self.quiet:
            perCent = self.calcPercentProgress()
            outputLine = ["%3d%% [" % (perCent)]
            maxBarLen = 40
            barProgress = maxBarLen * perCent / 100
            for idx in range(maxBarLen):
                # Fill upto current position with +
                if ((idx < barProgress - 1) or (perCent == 100)):
                    outputLine.append("+")
                # For the current position we twirl
                elif (idx < barProgress):
                    tSelect = ["|", "/", "-", "\\"]
                    outputLine.append(tSelect[self.twirlState])
                    self.twirlState += 1
                    if self.twirlState > 3:
                        self.twirlState = 0
                # Past the current position we output ' '
                else:
                    outputLine.append(" ")
            outputLine.append("] ")
            # Show the current operation
            if (self.currentOperation is not None):
                outputLine.append(self.currentOperation)
                # If what we output is shorter than the last output, we must also
                # output sufficient ' 's to wipe out any remaining text
                if (len(self.currentOperation) < self.lastOperationStringLen):
                    padLen = (self.lastOperationStringLen -
                              len(self.currentOperation))
                    outputLine.append(" " * padLen)
                # Remember the length of what we last outout
                self.lastOperationStringLen = len(self.currentOperation)
            if self.outputSupportsCR:
                sys.stdout.write('\r')
                sys.stdout.write("".join(outputLine))
                sys.stdout.flush()
            else:
                print "".join(outputLine)
