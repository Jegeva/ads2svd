from jarray import zeros
from dap import DAPRegAccess
from java.lang.System import nanoTime


class CortexM3:
    """ Class to control a Cortex-M3
    """
    # Define the address of the Debug Control and Status Register
    DHCSR = 0xE000EDF0
    # Define the fields of the Debug Control and Status Register
    DHCSR_KEY         = 0xA05F0000                                # @IgnorePep8
    DHCSR_C_DEBUGEN   = 0x00000001 << 0                           # @IgnorePep8
    DHCSR_C_HALT      = 0x00000001 << 1                           # @IgnorePep8
    DHCSR_C_STEP      = 0x00000001 << 2                           # @IgnorePep8
    DHCSR_C_MASKINTS  = 0x00000001 << 3                           # @IgnorePep8
    DHCSR_C_SNAPSTALL = 0x00000001 << 5                           # @IgnorePep8
    DHCSR_S_SREGRDY   = 0x00000001 << 16                          # @IgnorePep8
    DHCSR_S_HALT      = 0x00000001 << 17                          # @IgnorePep8
    DHCSR_S_SLEEP     = 0x00000001 << 18                          # @IgnorePep8
    DHCSR_S_LOCKUP    = 0x00000001 << 19                          # @IgnorePep8
    DHCSR_S_RETIRE_ST = 0x00000001 << 24                          # @IgnorePep8
    DHCSR_S_RESET_ST  = 0x00000001 << 25                          # @IgnorePep8

    def __init__(self, dap, ahbIdx):
        """ Construction from a DAP object and the AHB-AP index
        Params:
            dap - an object derived from DAPRegAccess
            ahbIdx - the index of the AHB-AP which connects to the Coretex-M3
                     debug logic
        """
        self.dap = dap
        self.ahbIdx = ahbIdx
        self.__DHSCRCache = 0

    def __updateDHCSRCache(self):
        """Updates our local cached DHCSR register value
        """
        m3DHSCR = self.dap.readAPMemBlock32(
            self.ahbIdx, CortexM3.DHCSR,
            1, DAPRegAccess.AP_REG_CSW_PROT_HPROT1)
        self.__DHSCRCache = m3DHSCR[0]

    def statusIndicatesRunning(self, DHSCRValue):
        if (DHSCRValue & CortexM3.DHCSR_S_HALT) == 0:
            return True
        return False

    def statusIndicatesHalted(self, DHSCRValue):
        if (DHSCRValue & CortexM3.DHCSR_S_HALT) != 0:
            return True
        return False

    def statusIndicatesSleep(self, DHSCRValue):
        if (DHSCRValue & CortexM3.DHCSR_S_SLEEP) != 0:
            return True
        return False

    def statusIndicatesLockup(self, DHSCRValue):
        if (DHSCRValue & CortexM3.DHCSR_S_LOCKUP) != 0:
            return True
        return False

    def isRunning(self):
        """Checks if the core is currently executing
        Returns:
            True if is executing
            False if not
        """
        self.__updateDHCSRCache()
        return self.statusIndicatesRunning(self.__DHSCRCache)

    def isHalted(self):
        """Checks if the core is currently halted
        Returns:
            True if is halted
            False if not
        """
        self.__updateDHCSRCache()
        return self.statusIndicatesHalted(self.__DHSCRCache)

    def halt(self, msTimeout=1000):
        """Halts the core (makes it enter debug state)
        Params:
            msTimeout
                The time interval in ms we wait for the core to enter debug
                state
        Returns:
            the latest DHCSR value. This value can be passed to
            statusIndicatesHalted() to find out of the core is halted.
            It can also be passed to any of the other statusIndicatesXXXXXX()
            methods to check last known status.
        """
        if self.isRunning():
            nsTimeout = msTimeout * 1000000
            data32 = zeros(1, 'l')
            data32[0] = (CortexM3.DHCSR_KEY |
                         CortexM3.DHCSR_C_DEBUGEN |
                         CortexM3.DHCSR_C_HALT)
            self.dap.writeAPMemBlock32(
                self.ahbIdx, CortexM3.DHCSR,
                data32, DAPRegAccess.AP_REG_CSW_PROT_HPROT1)
            startTime = nanoTime()
            timeDelta = nanoTime() - startTime
            while timeDelta <= nsTimeout:
                if self.isHalted():
                    break
                timeDelta = nanoTime() - startTime
        return self.__DHSCRCache

    def start(self):
        """Starts the core running
        Returns:
            the latest DHCSR value. This value can be passed to
            statusIndicatesRunning() to find out of the core is running.
            It can also be passed to any of the other statusIndicatesXXXXXX()
            methods to check last known status.
        """
        if self.isHalted():
            data32 = zeros(1, 'l')
            data32[0] = (CortexM3.DHCSR_KEY |
                         CortexM3.DHCSR_C_DEBUGEN)
            self.dap.writeAPMemBlock32(
                self.ahbIdx, CortexM3.DHCSR,
                data32, DAPRegAccess.AP_REG_CSW_PROT_HPROT1)
            self.__updateDHCSRCache()
        return self.__DHSCRCache
