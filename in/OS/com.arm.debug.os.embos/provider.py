################################################################################
#
# Copyright (C) 2014,2017 Arm Limited (or its affiliates). All rights reserved.
#
# embOS - 3.88c ARM Cortex M / 3.88h ARM Cortex A
#
#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

from osapi          import *
from globs          import *
from contexts       import ContextsProvider
from tasks          import Tasks
from kernel         import KernelData
from timers         import Timers
from csemaphores    import Csemaphores
from rsemaphores    import Rsemaphores
from mailboxes      import Mailboxes
from queues         import Queues
from mempools       import Mempools

def getOSContextProvider( ):
    return ContextsProvider( )

def getDataModel( ):
    return Model( OS_EMBOS, [
                              Tasks( ),
                              KernelData( ),
                              Mailboxes( ),
                              Mempools( ),
                              Queues( ),
                              Csemaphores( ),
                              Rsemaphores( ),
                              Timers( )
                            ] )

def isOSInitialised( debugSession ):
    return debugSession.evaluateExpression( OS_RUNNING ).readAsNumber( ) == 1

def areOSSymbolsLoaded( debugSession ):
    return debugSession.symbolExists( OS_GLOBAL ) and debugSession.symbolExists( OS_RUNNING )
