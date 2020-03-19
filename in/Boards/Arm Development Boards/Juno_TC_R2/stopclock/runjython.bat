echo OFF
SETLOCAL
echo You must edit runjython.bat to set the correct environment before you
echo can run this script 
goto exit
REM Edit the JYTHON= and DTSL_LIBS= lines below to be correct 
REM for your system then delete the previous 3 lines
REM JYTHON should be set to the location of your Jython installation
set JYTHON=C:\jython2.5.3
set DTSL_LIBS=libs
set JAVA_LIBS=%DTSL_LIBS%\arm\*
set JAVA_LIBS=%JAVA_LIBS%;%DTSL_LIBS%\tpip\*
set JAVA_LIBS=%JAVA_LIBS%;%DTSL_LIBS%\arm\com.arm.rddi.native
set CLASSPATH=%JAVA_LIBS%;%CLASSPATH%
set JYTHONPATH=.\src
set SCRIPT=%1
set COMMAND=%JYTHON%\jython src\%SCRIPT%.py %2 %3 %4 %5 %6 %7 %8 %9
echo ON
%COMMAND%
:exit
