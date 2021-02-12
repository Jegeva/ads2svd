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

#Usage
make will run the transformation for all xml file in the 'in'


## CAVEAT EMPTOR
* This is in devellopment
* As long as the ARM Develloper Studio files are not correct in the source i cannot guarantee the completeness or accuracy of the generated SVDs
* The current schema isn't supporting peripherals without base adresses and registers without offset. you've been warned
* Features not implemented:
..* resets values : the data is abscent from ADS
..* Interrupts : it is debatable that the exceptions (NMI, HARDFAULT, etc...) are or are not interrupts fired by the core

## license
This is released under Apache license : https://www.apache.org/licenses/LICENSE-2.0
BUT
The input file, even though i had to clean them (Apparently ARM have some "creative" understanding of how includes work...)
are copyright ARM

