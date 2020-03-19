When the Freescale Linux CAAM driver is loaded it is not possible to debug the target. 

You cannot connect to the target after the driver is loaded (the debugger gives the error: "Unable to connect to device AHB") and connecting to the target before booting causes the boot to hang when loading the CAAM driver (disconnecting does not resume the boot, the target must be restarted).
 
The solution is to disable the driver, by disabling the following Kernel config options, and rebuilding the kernel:
{{Cryptographic API / Hardware Crypto Devices / Freescale CAAM-Multicore driver backend}}
{{Cryptographic API / Hardware Crypto Devices / CAAM Secure Memory / Keystore API (EXPERIMENTAL)}}
 
This is not a problem in the previous 3.10.31 kernel as the driver is either not present or not enabled by default. 

In 3.10.53 the driver is enabled by default. 
