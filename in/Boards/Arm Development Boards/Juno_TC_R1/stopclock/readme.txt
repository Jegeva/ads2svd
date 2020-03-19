This is the readme.txt for Juno stop clock support in Arm Development Studio.
The support is in the form of a Jython script (Jython is the scripting
language used by Arm DS) which can be run both within a Arm DS debug session and
stand-alone (as a Jython script from a command prompt/Linux console).

The script has the following functionality;

* can trigger immediate entry into stop clock mode
* can configure entry into stop clock mode on watchdog timeout
* can configure entry into stop clock mode when one of the Cortex-A cores
  enters debug state i.e. when it hits a breakpoint or when is manually
  halted by the debugger
* can scan out the flop chain from either or both the A57 cluster and/or the
  A53 cluster into files compatible with the map_scan_data.pl script

e.g. to force Juno into stop clock mode use:
     > junostopclock -t manual -d TCP:DS-Tony

e.g. to scan out the Cortex-A57 chain use:
     > junostopclock -b -s TCP:DS-Tony
  
e.g. to scan out the Cortex-A53 chain use:
     > junostopclock -l -s TCP:DS-Tony

The script can be used to just do the configuration or just do the scan out or
both in the same run.

One complication is that the configuration of stop clock mode requires a
DSTREAM (or RVI) connected to J25 (or the JTAG connector on the back plate
of the Juno platform housing), whilst the scan out of the flop chain requires
a DSTREAM (or RVI) connected to J76 on the Juno base board. A further
complication is that J76 normally has a jumper fitted between pins 3 & 4 and
this jumper must be removed before the DSTREAM can be attached. Note that this
jumper _must_ be fitted for Juno to boot correctly.

The above leads us to the following;

The script allows use of one or two DSTREAMS. If you are lucky enough to have
two DSTREAMS you can leave them plugged into the two connectors. If you only
have the one DSTREAM, the script will guide you when to swap it from one
connector to the other. If you use two DSTREAMs you dont need to replace the
jumper on J76. When the script completes it will leave the JTAG connector with
nTRST low - which is what the jumper does. You will of course need to put the
jumper back should you unplug the DSTREAM (or power it off) from J76 and 
re-boot Juno.
  
Dependencies
============  
If you wish to run the script in stand alone mode you will need to have Jython 
installed (www.jython.org). It has been tested with Jython 2.5.3 which at the
time of writing (June 2014) is the latest stable release. Since Jython is an
integration of Python and Java you will also need a JVM (install a Java Runtime 
Environment - JRE - either from Oracle or elsewhere). You will need to install
the JRE before installing Jython.

If you wish to run the script within your own Eclipse (but not from within a
Arm DS debug session), you will need to install Jython (see above) and you must
add PyDev to your Eclipse installation (Help->Eclipse Marketplace..., and 
search for PyDev).

If you wish to run the script within a Arm DS debug session you will need Arm DS
installed (obviously, but you wont then need your own Jython, Java or PyDev 
installation since Arm DS has these pre-installed).

You will need access to one or more DSTREAM or RVI boxes.

Installation
============

Stand Alone Mode Only
---------------------
If you only wish to use the script in stand alone mode (outside of Eclipse) you
can unzip the received file to a directory of your choice. You will then need
to modify the runjython.bat or runjython shell script to inform it of the
location of your Jython installation. The junostopclock.bat or junostopclock 
shell script should be run from within the extracted directory. 

For use within Eclipse (Your own or Arm DS's)
-------------------------------------------
Within Eclipse, use File->Import... and select General, Existing Projects Into 
Workspace. After clicking the Next button, select Archive File and browse to
the received .zip file.  Select the JunoStopClock project and click Finish to
import this in to your workspace.

The project will get imported, but there will be several errors in the project.
This is to be expected until you have followed the following configuration task.
Within your workspace, right click the JunoStopClock project and select 
Properties... Select 'Pydev - PYTHONPATH' and then select the 'String 
Substitution Variables' tab. Select the DTSL entry and click the Edit... button.
Change the value to be the path to the project, for example, for me this is set
to 'c:/users/tarmitst/workspace4.2/JunoStopClock'. Click OK to dismiss the 
dialog and again to dismiss the properties page. The errors in the JunoStopClock
project should then disappear. 

Running
=======

Stand alone
-----------
When run stand alone (or as a Jython project within Eclispe), the script 
options are as follows:

Usage: JunoStopClock [options] (use --help to see full option list)

Juno Stop clock configure/dump program. Please specify at least one of the -t,
-b or -l options.

Options:
  --version             show program's version number and exit
  -h, --help            show this help message and exit
  -d DEBUGDSTREAM, --debugDSTREAM=DEBUGDSTREAM
                        the DSTREAM connected to J25 JTAG connector. Set this
                        to TCP:<hostname | ipaddress> or USB
  -s SCANDSTREAM, --scanDSTREAM=SCANDSTREAM
                        the DSTREAM connected to J76 JTAG connector. Set this
                        to TCP:<hostname | ipaddress> or USB
  -f A57FILE, --a57File=A57FILE
                        the file used to store raw Cortex-A57 scans. Defaults
                        to a57.bin
  -g A53FILE, --a53File=A53FILE
                        the file used to store raw Cortex-A53 scans. Defaults
                        to a53.bin
  -t CONFIGURESTOPCLOCKTRIGGERS, --configureStopClockTriggers=CONFIGURESTOPCLOCKTRIGGERS
                        requests stop-clock mode be triggered either manually
                        (-t manual), via a watchdog firing (-t watchdog) or
                        via a core entering debug state [-t debug(*<core-spec-
                        list>)]
  -b, --scanA57         requests the Cortex-A57 chains are scanned out into
                        the file specified by the -f option
  -l, --scanA53         requests the Cortex-A53 chains are scanned out into
                        the file specified by the -g option

<core-spec-list> is a comma separated list of cores or core types
e.g. debug(Cortex-A57_0)
     debug(A57_0)
     debug(Cortex-A57_0,Cortex-A57_1)
     debug(A57_0,A57_1)
     debug(A57)
     debug(A53)
     debug(A53_0,A53_2)
     debug(A53_0,A53_2,A57)

If the -d and -s options point to the same DSTREAM box, the script will prompt
you to change between connectors.

From Arm DS
---------
When run from within Arm DS the available options change slightly. The -d option
and the -s option (the ones which specify the DSTREAM to use) can be set to 
'DS:' which indicates that the DSTREAM currently in use by Arm DS should be used.
The -s option can also take the value 'DTSLOPTS:' which means that the scan
DSTREAM connection string should be read from the Arm DS DTSL options values [to
see these, access the DTSL options from Arm DS and select the Stop Clock tab].

There are two easy ways of running the script from within Arm DS. But first you
must have a DSTREAM connection to (any of the DSTREAM Juno debug activities 
will do). Once connected, you can;

1. With the JunoStopClock/src folder open in the Eclipse Project Explorer view, 
   click and drag the JunoStopClock.py file onto the Arm Debugger Command view 
   backdrop (_not_ on the Command: command entry field). This will populate the
   command entry field with the command to run the script. You can then add any
   parameters you require and hit Enter or click the Submit button.
   
2. With the JunoStopClock/src folder open in the Eclipse Project Explorer view, 
   click and drag the JunoStopClock.py file onto the Arm Debugger Scripts view.
   This will add the script to the view. You can then select the script and add
   any parameters you wish by clicking the (...) Script Parameters icon. This
   allows one set of parameters to be remembered per script. You can then just
   double click the script to get it run with the applied parameters.
      
NOTES
=====
If you run the script with the '-t manual' parameter, this will cause Juno to 
enter stop clock mode. At this point the debugger will be unable to communicate
with the target and you are likely to see one or two error messages appear on
the debugger command view. At this point there are only a few sensible things 
you can do;

1. Run the script again to off load the scan data
2. Disconnect the Arm DS debug session
3. Power cycle the Juno platform
