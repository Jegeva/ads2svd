# Copyright (C) 2018 Arm Limited (or its affiliates). All rights reserved.

"""
Module to process command line options
"""
from optparse import OptionParser
import re


class ProgramOptions(object):
    """
    Parses command line options and provides configuration data to the
    main program
    """

    # When specified as a debug or scan DSTREAM address, this means 'use
    # the DSTREAM Arm DS is currently using'
    DS_DSTREAM = "DS:"
    # When specified as a scan DSTREAM address, or a trigger specification
    # this means 'use the Arm DS DTSL Options value(s)'
    DS_DTSLOPTS = "DTSLOPTS:"
    BAD_OPTIONS = -1

    TRIG_MANUAL = "manual"
    TRIG_MANUAL_DELAY = "manual_delay"
    TRIG_WATCHDOG = "watchdog"
    TRIG_DEBUG = "debug"
    TRIG_CORTEX_A57_0 = "Cortex-A57_0"
    TRIG_CORTEX_A57_1 = "Cortex-A57_1"
    TRIG_CORTEX_A53_0 = "Cortex-A53_0"
    TRIG_CORTEX_A53_1 = "Cortex-A53_1"
    TRIG_CORTEX_A53_2 = "Cortex-A53_2"
    TRIG_CORTEX_A53_3 = "Cortex-A53_3"

    def __init__(self, programName, version, fromDS):
        """
        Constructor
        """
        self.programName = programName
        self.version = version
        self.fromDS = fromDS
        if self.fromDS:
            self.debugDSTREAM = ProgramOptions.DS_DSTREAM
            self.scanDSTREAM = ProgramOptions.DS_DSTREAM
            self.debugDSTREAMHelp = (
                "Set this to %s to use the Arm DS DSTREAM or set it to "
                "TCP:<hostname | ipaddress> or USB. The default is %s" % (
                    ProgramOptions.DS_DSTREAM,
                    ProgramOptions.DS_DSTREAM))
            self.scanDSTREAMHelp = (
                "Set this to %s to use the Arm DS DSTREAM or set it to "
                "%s to use the DSTREAM specified in the Arm DS DTSL options "
                "or set it to TCP:<hostname | ipaddress> or USB. "
                "The default is %s" % (
                    ProgramOptions.DS_DSTREAM,
                    ProgramOptions.DS_DTSLOPTS,
                    ProgramOptions.DS_DSTREAM))
        else:
            self.debugDSTREAM = None
            self.scanDSTREAM = None
            self.debugDSTREAMHelp = (
                "Set this to TCP:<hostname | ipaddress> or USB")
            self.scanDSTREAMHelp = (
                "Set this to TCP:<hostname | ipaddress> or USB")
        self.a53File = None
        self.a57File = None
        self.configureStopClockTriggers = None
        self.scanA53 = False
        self.scanA57 = False
        self.triggerSources = {
            ProgramOptions.TRIG_MANUAL: False,
            ProgramOptions.TRIG_MANUAL_DELAY: 0,
            ProgramOptions.TRIG_WATCHDOG: False,
            ProgramOptions.TRIG_CORTEX_A57_0: False,
            ProgramOptions.TRIG_CORTEX_A57_1: False,
            ProgramOptions.TRIG_CORTEX_A53_0: False,
            ProgramOptions.TRIG_CORTEX_A53_1: False,
            ProgramOptions.TRIG_CORTEX_A53_2: False,
            ProgramOptions.TRIG_CORTEX_A53_3: False
        }
        self.jumper = False
        self.vstream = False

    def decodeManualTriggerSpec(self, spec):
        """Decodes a manual trigger parameter set - which right now is only
           an optional delay setting.
        Params:
            spec - a string which is:
                empty - means a delay value of 0
                (delay)
                   delay = integer in the range [0..65535]
        Returns:
            None if the decode went well or a message which indicates why
            we were unable to decode the spec
        """
        self.triggerSources[ProgramOptions.TRIG_MANUAL] = True
        msg = None
        if len(spec) == 0:
            self.triggerSources[ProgramOptions.TRIG_MANUAL_DELAY] = 0
        elif spec[0] == '(' and spec[-1] == ')':
            delayStr = spec[1:-1]
            try:
                delay = int(delayStr, 0)
                if (0 <= delay) and (delay <= 65535):
                    self.triggerSources[
                        ProgramOptions.TRIG_MANUAL_DELAY] = delay
                else:
                    raise ValueError('delay value is out of range')
            except ValueError, e:
                msg = ("Invalid manual trigger delay definition, "
                       "expecting (<0..65535>), got %s with error: %s" %
                       (spec, str(e)))
        else:
            msg = ("Invalid manual trigger delay definition, "
                   "expecting (delay), got %s" % (spec))
        return msg

    def decodeTriggerCoreSpec(self, coreSpec):
        """Decodes a core-spec string and fills in self.triggerSources from
           what we find in the string.
        Params:
            coreSpec - a string which is:
                empty - which means trigger on all cores
                (*<core>)
                   core = [<Cortex-A | A>]<57[_0 | _1]> |
                                           53[_0 | _1 | _2 | _3]>)
        Returns:
            None if the decode went well and self.triggerSources assigned ok
            A message which indicates why we were unable to decode the
            core-spec
        """
        msg = None
        if len(coreSpec) == 0:
            self.triggerSources[ProgramOptions.TRIG_CORTEX_A57_0] = True
            self.triggerSources[ProgramOptions.TRIG_CORTEX_A57_1] = True
            self.triggerSources[ProgramOptions.TRIG_CORTEX_A53_0] = True
            self.triggerSources[ProgramOptions.TRIG_CORTEX_A53_1] = True
            self.triggerSources[ProgramOptions.TRIG_CORTEX_A53_2] = True
            self.triggerSources[ProgramOptions.TRIG_CORTEX_A53_3] = True
        elif coreSpec[0] == '(' and coreSpec[-1] == ')':
            coreList = coreSpec[1:-1].split(',')
            for core in coreList:
                if msg is not None:
                    break
                coreid = core.lower()
                if coreid[0:8] == "cortex-a":
                    coreid = core[8:]
                elif coreid[0] == "a":
                    coreid = core[1:]
                if coreid == "57":
                    self.triggerSources[
                        ProgramOptions.TRIG_CORTEX_A57_0] = True
                    self.triggerSources[
                        ProgramOptions.TRIG_CORTEX_A57_2] = True
                elif coreid == "53":
                    self.triggerSources[
                        ProgramOptions.TRIG_CORTEX_A53_0] = True
                    self.triggerSources[
                        ProgramOptions.TRIG_CORTEX_A53_1] = True
                    self.triggerSources[
                        ProgramOptions.TRIG_CORTEX_A53_2] = True
                    self.triggerSources[
                        ProgramOptions.TRIG_CORTEX_A53_3] = True
                elif coreid == "57_0":
                    self.triggerSources[
                        ProgramOptions.TRIG_CORTEX_A57_0] = True
                elif coreid == "57_1":
                    self.triggerSources[
                        ProgramOptions.TRIG_CORTEX_A57_1] = True
                elif coreid == "53_0":
                    self.triggerSources[
                        ProgramOptions.TRIG_CORTEX_A53_0] = True
                elif coreid == "53_1":
                    self.triggerSources[
                        ProgramOptions.TRIG_CORTEX_A53_1] = True
                elif coreid == "53_2":
                    self.triggerSources[
                        ProgramOptions.TRIG_CORTEX_A53_2] = True
                elif coreid == "53_3":
                    self.triggerSources[
                        ProgramOptions.TRIG_CORTEX_A53_3] = True
                else:
                    msg = "Invalid stop clock core definition: %s" % (core)
        else:
            msg = "Invalid stop clock core definition: %s" % (coreSpec)
        return msg

    def decodeTriggerStopClock(self):
        """Decodes the trigger specification string. This is of the form:
            <trig-spec>
            trig-spec = *{manual[(delay)] | watchdog | debug[(<core-spec>)]},
            core-spec = (*<core>,)
            core = [<Cortex-A | A>]<57[_0 | _1]> | 53[_0 | _1 | _2 | _3]>)
           e.g. the following are all valid trig-spec
                   manual
                   manual(100)
                   watchdog
                   watchdog,debug
                   watchdog,debug(Cortex-A57_0)
                   debug(A57_0)
                   debug(Cortex-A57_0,Cortex-A57_1)
                   debug(A57_0,A57_1)
                   i.e. you can use Cortex-A or just the A
                   debug(A57)
                   debug(A53)
                   debug(A53_0,A53_2)
                   debug(A53_0,A53_2,A57)
        """
        trigSpecs = re.split(r',\s*(?=[^)]*(?:\(|$))',
                             self.configureStopClockTriggers)
        msg = None
        for spec in trigSpecs:
            if msg is not None:
                break
            if (spec.lower()[0:len(ProgramOptions.TRIG_MANUAL)]
                    == ProgramOptions.TRIG_MANUAL):
                msg = self.decodeManualTriggerSpec(
                    spec[len(ProgramOptions.TRIG_MANUAL):])
            elif spec.lower() == ProgramOptions.TRIG_WATCHDOG:
                self.triggerSources[ProgramOptions.TRIG_WATCHDOG] = True
            elif (spec.lower()[0:len(ProgramOptions.TRIG_DEBUG)]
                    == ProgramOptions.TRIG_DEBUG):
                msg = self.decodeTriggerCoreSpec(
                    spec[len(ProgramOptions.TRIG_DEBUG):])
            else:
                msg = "Invalid stop clock trigger specification: %s" % (spec)
        return msg

    def checkOptions(self):
        rCode = True
        if self.hasTriggerRequests():
            if ((self.getScanDSTREAM() == ProgramOptions.DS_DSTREAM) or
                (self.getScanDSTREAM() == ProgramOptions.DS_DTSLOPTS)):
                if not self.fromDS:
                    print ("The debug DSTREAM can only be specified as %s or "
                           "%s when being run from within Arm DS" %
                           (ProgramOptions.DS_DSTREAM,
                            ProgramOptions.DS_DTSLOPTS))
                    rCode = False
            elif self.getDebugDSTREAM() is None:
                print("You have not specified the debug DSTREAM "
                      "connected to J25")
                rCode = False
        if self.getScanA57() or self.getScanA53():
            if ((self.getScanDSTREAM() == ProgramOptions.DS_DSTREAM) or
                (self.getScanDSTREAM() == ProgramOptions.DS_DTSLOPTS)):
                if not self.fromDS:
                    print ("The scan DSTREAM can only be specified as %s or "
                           "%s when being run from within Arm DS" %
                           (ProgramOptions.DS_DSTREAM,
                            ProgramOptions.DS_DTSLOPTS))
                    rCode = False
            elif self.getScanDSTREAM() is None:
                print("You have not specified the scan DSTREAM "
                      "connected to J76")
                rCode = False
        if (not self.hasTriggerRequests() and
            not self.getScanA57() and
            not self.getScanA53() and
            not self.getScanJumper()):
            print ("This program will not do anything unless you specify one "
                   "of the -t, -b, -l or -j options")
            rCode = False
        return rCode

    def processOptions(self):
        """ Processes command line option """
        # Construct option specifications
        parser = OptionParser(
            usage=("usage: %s [options] (use --help to see full "
                   "option list)") % self.programName,
            version="%s %s" % (self.programName, self.version),
            description="Juno Stop clock configure/dump "
                        "program. Please specify at least one "
                        "of the -t, -b or -l options.")
        parser.add_option("-d", "--debugDSTREAM", action="store",
                          type="string", dest="debugDSTREAM",
                          help="the DSTREAM connected to "
                                "J25 JTAG connector. " +
                                self.scanDSTREAMHelp)
        parser.add_option("-s", "--scanDSTREAM", action="store",
                          type="string", dest="scanDSTREAM",
                          help="the DSTREAM connected to "
                               "J76 JTAG connector. " +
                               self.debugDSTREAMHelp)
        parser.add_option("-f", "--a57File", action="store",
                          type="string", dest="a57File", default="a57.bin",
                          help="the file used to store raw Cortex-A57 scans. "
                               "Defaults to a57.bin")
        parser.add_option("-g", "--a53File", action="store",
                          type="string", dest="a53File", default="a53.bin",
                          help="the file used to store raw Cortex-A53 scans. "
                               "Defaults to a53.bin")
        parser.add_option("-t", "--configureStopClockTriggers", action="store",
                          type="string", dest="configureStopClockTriggers",
                          help="requests stop-clock mode be triggered either "
                               "manually (-t manual[(delay)]), via a watchdog "
                               "firing "
                               "(-t watchdog) or via a core entering debug "
                               "state [-t debug(*<core-spec-list>)]")
        parser.add_option("-b", "--scanA57", action="store_true",
                          dest="scanA57",
                          help="requests the Cortex-A57 chains are "
                               "scanned out into the file specified by the "
                               "-f option")
        parser.add_option("-l", "--scanA53", action="store_true",
                          dest="scanA53",
                          help="requests the Cortex-A53 chains are "
                               "scanned out into the file specified by the "
                               "-g option")
        parser.add_option("-j", "--jumper", action="store_true",
                          dest="jumper",
                          help="Drives nTRST low on the scan DSTREAM "
                               "to mimic the opertion of the jumper fitted to "
                               "J67. Only of use if using two DSTREAM boxes.")
        parser.add_option("-v", "--vstream", action="store_true",
                          dest="vstream",
                          help="Specify this option if you are using the "
                               "program to connect to a RTL emulation via "
                               "VSTREAM. Doing so forces the program to use "
                               "the VSTREAM DAP Templat to configure the stop "
                               "clock trigger  options")
        # Process all supplied options
        options = parser.parse_args()[0]
        # Extract any supplied options into our local values
        if options.debugDSTREAM is not None:
            self.debugDSTREAM = options.debugDSTREAM
        if options.scanDSTREAM is not None:
            self.scanDSTREAM = options.scanDSTREAM
        if options.a53File is not None:
            self.a53File = options.a53File
        if options.a57File is not None:
            self.a57File = options.a57File
        if options.scanA57 is not None:
            self.scanA57 = options.scanA57
        if options.scanA53 is not None:
            self.scanA53 = options.scanA53
        if options.configureStopClockTriggers is not None:
            self.configureStopClockTriggers = (
                options.configureStopClockTriggers)
            errMsg = self.decodeTriggerStopClock()
            if errMsg is not None:
                print errMsg
                return False
        if options.jumper is not None:
            self.jumper = options.jumper
        if options.vstream is not None:
            self.vstream = options.vstream
        return self.checkOptions()

    def getDebugDSTREAM(self):
        return self.debugDSTREAM

    def getScanDSTREAM(self):
        return self.scanDSTREAM

    def getCortexA53File(self):
        return self.a53File

    def getCortexA57File(self):
        return self.a57File

    def getTriggerSources(self):
        return self.triggerSources

    def hasTriggerRequests(self):
        triggers = [
            ProgramOptions.TRIG_MANUAL,
            ProgramOptions.TRIG_WATCHDOG,
            ProgramOptions.TRIG_CORTEX_A57_0,
            ProgramOptions.TRIG_CORTEX_A57_1,
            ProgramOptions.TRIG_CORTEX_A53_0,
            ProgramOptions.TRIG_CORTEX_A53_1,
            ProgramOptions.TRIG_CORTEX_A53_2,
            ProgramOptions.TRIG_CORTEX_A53_3
        ]
        hasTriggers = False
        for trigger in triggers:
            hasTriggers = hasTriggers | self.triggerSources[trigger]
        return hasTriggers

    def getScanA57(self):
        return self.scanA57

    def getScanA53(self):
        return self.scanA53

    def getScanJumper(self):
        return self.jumper

    def getUseVSTREAM(self):
        return self.vstream
