# This turn the arm develloper studio xml corpus into a cmsis SVD format compliant description of all the ARM cores described in the ASD XML corpus (sw/debugger/configdb/Cores)


* ads2svd.py :
(tries to) resolve the include into ./out/
* ads2svd.xslt:
to apply with an xslt 2.0 processor (tested using saxonhe) on a ads2svd.py result xml to get a core svd
* in : 
the (corrected) infiles from arm develloper studio, this is all @ARM, some includes in the original ARM xml files were broken

CAVEAT EMPTOR:
* This is in devellopment
* As long as the ARM Develloper Studio files are not correct in the source i cannot guarantee the completeness or accuracy of the generated SVDs
