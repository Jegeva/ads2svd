################################################################################
#
# Copyright (C) 2014,2017 Arm Limited (or its affiliates). All rights reserved.
#
# Quadros RTXC
#
#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

# this script effectively implements com.arm.debug.extension.os.IOSProvider

from osapi import *
from contexts import ContextsProvider
from kernel import Kernel
from ktasks import Tasks
from ktaskstacks import Taskstacks
from ktasksemaphores import Tasksemaphores
from ktasksready import Tasksready
from ksemaphores import Semaphores
from kmailboxes import Mailboxes
from kmailboxsemaphores import Mailboxsemaphores
from kmailboxentries import Mailboxentries
from kqueues import Queues
from kqueuesemaphores import Queuesemaphores
from kqueuentries import Queuentries
from kpartitions import Partitions
from kpartitionsemaphores import Partitionsemaphores
from kpartitionentries import Partitionentries
from kmutexes import Mutexes
from kmutexsemaphores import Mutexsemaphores
from kpipes import Pipes
from kpipefullbufs import Pipefullbufs
from kpipeemptybufs import Pipeemptybufs
from kexceptions import Exceptions
from kexceptbacktrace import Exceptbacktrace
from keventsources import Eventsources
from kcounters import Counters
from kalarms import Alarms

def getOSContextProvider( ):
    return ContextsProvider( )

def getDataModel( ):
    return Model( "rtxc", [ Tasks( ),
                            Taskstacks( ),
                            Tasksemaphores( ),
                            Tasksready( ),
                            Semaphores( ),
                            Mailboxes( ),
                            Mailboxsemaphores( ),
                            Mailboxentries( ),
                            Queues( ),
                            Queuesemaphores( ),
                            Queuentries( ),
                            Partitions( ),
                            Partitionsemaphores( ),
                            Partitionentries( ),
                            Mutexes( ),
                            Mutexsemaphores( ),
                            Pipes( ),
                            Pipefullbufs( ),
                            Pipeemptybufs( ),
                            Exceptions( ),
                            Exceptbacktrace( ),
                            Eventsources( ),
                            Counters( ),
                            Alarms( ),
                            Kernel( ) ] )

def isOSInitialised( debugger ):
    return debugger.evaluateExpression( "kernel_initialized" ).readAsNumber( ) == 1

def areOSSymbolsLoaded( debugger ):
    return debugger.symbolExists( "kernel_initialized" ) and debugger.symbolExists( "pKWS" )
