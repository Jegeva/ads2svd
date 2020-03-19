#
# Wrapper around the subprocess module that replaces subprocess's
# input / output coupler threads with our own implementation that:
#  - flushes each buffer after writing it
#  - allows observers to be installed to watch for certain patterns
#

import subprocess
import sys
import java.lang.Thread
import java.lang.System

class Forwarder(java.lang.Thread):
    '''Thread that forwards data from one file object to another

    Allows observer functions to process each line'''

    # Jython 2.5.3 seems to be doing a blocking read so only safe to read 1 char at a time
    BUFFER_SIZE = 1

    def __init__(self, source, sink, observers, name=None):
        java.lang.Thread.__init__(self, name=name)
        self.source = source
        self.sink = sink
        self.observers = observers


    def run(self):
        if self.observers:
            curLine = ""
        while True:
            try:
                # read a block from the source
                bytesRead = self.source.read(Forwarder.BUFFER_SIZE)
                if bytesRead == "":
                    # empty block indicates end of data - exit
                    self.sourceClosed()
                    break

                # write to the sink and flush
                self.sink.write(bytesRead)
                self.sink.flush()

                # only process lines if something is observing them
                if self.observers:
                    curLine += bytesRead
                    lines = curLine.split('\n')
                    for l in lines[:-1]:
                        self.processLine(l)
                    curLine = lines[-1]
            except Exception, e:
                # ignore interrupted exception when shutting down
                if str(e) != 'java.nio.channels.ClosedByInterruptException':
                    java.lang.System.err.println(str(e))
                self.sourceClosed()
                break


    def processLine(self, l):
        '''Pass a line of output to each observer'''
        for observer in self.observers:
            observer(l)


    def sourceClosed(self):
        '''Cleanup the source on exit'''
        pass



class InputForwarder(Forwarder):
    '''Forwarder thread for input to process that closes it on EOF'''
    def __init__(self, source, sink, observers=None, name=None):
        Forwarder.__init__(self, source, sink, observers=observers, name=name)


    def sourceClosed(self):
        '''Close the sink when the source reaches EOF'''
        Forwarder.sourceClosed(self)
        self.sink.close()



class ProcessRunner():
    '''Process runner class that connects process input/output/error to interpreter's input/output/error

    See subprocess.Popen for details

    Starts threads to forward data on input/output/error streams

    stdin: input for the process, None for no input, defaults to interpreter stdin
    cmd: command and arguments to execute
    cwd: working directory for command
    env: environment for command
    outputObservers: observers to install on output stream
    errorObservers: observers to install on error stream
    name: name to include in thread names (useful for debug)
    '''
    def __init__(self, cmd, stdin=sys.stdin, cwd=None, env=None, outputObservers=None, errorObservers=None, name="process"):
        if stdin:
            procStdin = subprocess.PIPE
        else:
            procStdin = None

        # start the process, connecting input/output/error streams to pipes
        self.proc = subprocess.Popen(cmd, stdin=procStdin, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=cwd, env=env)

        # start threads to forward process input/output/error to/from interpreter's I/O
        if stdin:
            self.stdinThread = InputForwarder(stdin, self.proc.stdin, name="%s stdin" % name)
            self.stdinThread.start()
        else:
            self.stdinThread = None

        self.stdoutThread = Forwarder(self.proc.stdout, sys.stdout, observers=outputObservers, name="%s stdout" % name)
        self.stdoutThread.start()

        self.stderrThread = Forwarder(self.proc.stderr, sys.stderr, observers=errorObservers, name="%s stderr" % name)
        self.stderrThread.start()

        self.returncode = None


    @staticmethod
    def call(cmd, *args, **kwargs):
        '''Invoke a process and wait for completion

        Returns result code'''
        runner = ProcessRunner(cmd, *args, **kwargs)
        return runner.wait()


    def poll(self):
        '''Poll for process completion

        Returns immediately with exit code if process has exited or None if still running'''
        if self.proc:
            self.returncode = self.proc.poll()

            if not self.returncode is None:
                self.cleanup()

        return self.returncode


    def wait(self):
        '''Wait for process completion

        Returns with exit code when process exits'''
        if self.proc:
            self.returncode = self.proc.wait()

            if not self.returncode is None:
                self.cleanup()

        return self.returncode


    def terminate(self):
        '''Kill the process

        This is not a graceful shutdown - on windows the process is terminated immediately

        Call wait() or poll() to cleanup and get exit code
        '''
        if self.proc and self.proc._process:
            self.proc._process.destroy()


    def cleanup(self):
        # Jython 2.5.2 doesn't clean up the pipes properly when a process exits and we use poll()
        #  - it only cleans up when using wait()
        if self.proc:
            if self.proc._stdin_thread:
                self.proc._stdin_thread.interrupt()

        # and stop the input/output threads we started
        if self.stdinThread:
            self.stdinThread.interrupt()
            self.stdinThread.join()
            self.stdinThread = None
        if self.stdoutThread:
            self.stdoutThread.join()
            self.stdoutThread = None
        if self.stderrThread:
            self.stderrThread.join()
            self.stderrThread = None

        self.proc = None
