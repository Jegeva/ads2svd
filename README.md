# ADS2SVD

This turn the arm develloper studio xml corpus into a cmsis SVD format compliant description of all the ARM cores described in the ASD XML corpus (sw/debugger/configdb/Cores).
The main goal of the tool is to have the CORE peripherals and registers in an svd format. 

## Files
* ads2svd.py :
(tries to) resolve the include into ./out/
* ads2svd.xslt:
to apply with an xslt 2.0 processor (tested using saxonhe) on a ads2svd.py result xml to get a core svd
* in : 
the (corrected) infiles from arm develloper studio, this is all @ARM, some includes in the original ARM xml files were broken
* Makefile :
Do not forget to set the  path to saxon HE to a  valid path on your system

## CAVEAT EMPTOR
* This is in devellopment
* As long as the ARM Develloper Studio files are not correct in the source i cannot guarantee the completeness or accuracy of the generated SVDs
* The current schema isn't supporting peripherals without base adresses and registers without offset. you've been warned
* Features not implemented:
..* resets values : the data is abscent from ADS
..* Interrupts : it is debatable that the exceptions (NMI, HARDFAULT, etc...) are or are not interrupt fired by the core

## Output
Will generate architecture specific (AARCH32 or AARCH64 if supported) svds for:
* 88FR101
* 88FR111
* A12_A7_bigLITTLE
* A15_A7_bigLITTLE
* A17_A7_bigLITTLE
* A53_A35_bigLITTLE
* A55_A75
* A57_A35_bigLITTLE
* A57_A53_bigLITTLE
* A72_A35_bigLITTLE
* A72_A53_bigLITTLE
* A73_A53_bigLITTLE
* A75_A55_bigLITTLE
* AEMv8M_FVP
* AEMv8M
* ARM1136JF-S_r0
* ARM1136JF-S
* ARM1156T2F-S
* ARM1176JZF-S
* ARM11MPCore
* ARM7TDMI_r4
* ARM7TDMI-S_r4
* ARM7TDMI
* ARM920T
* ARM922T
* ARM926EJ-S
* ARM946E-S
* ARM966E-S
* ARM968E-S
* ARMAEMv8-R_
* ARMAEMv8_
* Cortex-A12
* Cortex-A15_RTSM
* Cortex-A15
* Cortex-A17
* Cortex-A32
* Cortex-A35
* Cortex-A53
* Cortex-A55
* Cortex-A57
* Cortex-A5_RTSM
* Cortex-A5
* Cortex-A72
* Cortex-A73
* Cortex-A75
* Cortex-A76AE
* Cortex-A76
* Cortex-A7_RTSM
* Cortex-A7
* Cortex-A8_NS
* Cortex-A8
* Cortex-A9_RTSM
* Cortex-A9
* Cortex-M0
* Cortex-M0+
* Cortex-M1
* Cortex-M23_FVP
* Cortex-M23
* Cortex-M33_FVP
* Cortex-M33
* Cortex-M35P_FVP
* Cortex-M35P
* Cortex-M3_RTSM
* Cortex-M3
* Cortex-M4_NFP
* Cortex-M4_RTSM
* Cortex-M4
* Cortex-M7
* Cortex-R4
* Cortex-R52
* Cortex-R5
* Cortex-R7
* Cortex-R8
* gdb_server_pseudo_core_aarch64
* gdb_server_pseudo_core_v5
* gdb_server_pseudo_core
* Generic_V8_1
* Generic_V8_2_CCIDX
* Generic_V8_2
* Generic_V8_3
* Generic_V8M_FVP
* Generic_V8M
* Generic_V8R
* Generic_V8
* Generic_V8_X
* PJ4_NS
* PJ4
* ThunderX-r2
* ThunderX
