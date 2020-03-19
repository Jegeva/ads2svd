README for Spansion S6J3110EJAA

Flash programming of both the TCLASH and WORKFLASH is supported using the 'flash load ...' command.

Note that programming of the lower sectors of the TCFLASH can result in the part being 'locked' and connection via Arm DS not possible.
However, support has been added to allow a part to be 'unlocked' by erasing the complete device.

First of all the board must be put into 'Non-User Mode' by setting SW2:1 ON and power cycling.

At an Arm DS command prompt, run:

>csat EraseDeviceLockedPart.csat

and follow the instructions. 

(It is necessary to alter the script to specify the address of the DSTREAM or RealView-ICE before it will run to completion)

Note that after the script has run, around 40 seconds delay is needed before the final read from memory which confirms the erase has completed.
After this set SW2:1 OFF and power cycle - the board will now be connectable using Arm DS.