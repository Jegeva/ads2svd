Note: Bug reported by Freescale support in trace path on M-18ASA00132D001 silicon on 700-28040 REV X4 TWR - LS1021A board
This results in corrupted trace in ETB from both cores.

Tested using 66MHz core clock - achieved by setting SW3[3:4] = '00' instead of default SW3[3:4] = '10' and achieved good trace.

CMSIS-DAP support may need an updated firmware from Freescale, please contact Freescale support for this.

Note: CMSIS-DAP connections do not support reset and will lose connection to the target, likely due to the CMSIS-DAP hardware on the board being reset - disconnect and then reconnect to re-establish connection.
DSTREAM correctly handles reset.

15/01/2015