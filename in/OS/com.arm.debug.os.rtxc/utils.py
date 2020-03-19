################################################################################
#
# Copyright (C) 2014,2017 Arm Limited (or its affiliates). All rights reserved.
#
# Quadros RTXC
#
#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

from osapi import *

LEVEL_KCLASS        = 0
THREAD_KCLASS       = 1
EVNTSRC_KCLASS      = 2
COUNTER_KCLASS      = 3
ALARM_KCLASS        = 4
PIPE_KCLASS         = 5
EXCPTN_KCLASS       = 6
TASK_KCLASS         = 7
SEMA_KCLASS         = 8
MBOX_KCLASS         = 9
PART_KCLASS         = 10
QUEUE_KCLASS        = 11
MUTX_KCLASS         = 12
SPECIAL_KCLASS      = 13

TSTATE_READY        = 0x0000L
INACTIVE_BLOCK      = 0x0800L
MUTEX_WAIT          = 0x0400L
QUEUE_WAIT          = 0x0200L
PARTITION_WAIT      = 0x0100L
MAILBOX_WAIT        = 0x0080L
ALARM_WAIT          = 0x0040L
SEMAPHORE_WAIT      = 0x0020L
PIPE_WAIT           = 0x0010L
SLEEP_BLOCK         = 0x0008L
ACK_BLOCK           = 0x0004L
ABORT_BLOCK         = 0x0002L
SUSPEND_BLOCK       = 0x0001L

ATTR_STATISTICS         = 0x0008L
ATTR_MULTIPLE_WAITERS   = 0x0010L
ATTR_FIFO_ORDER         = 0x0002L
ATTR_SEMAPHORES         = 0x0004L
ATTR_INVERSION          = 0x0010L

ALARM_INACTIVE      =  0L
ALARM_ACTIVE        =  1L
ALARM_DONE          =  2L
ALARM_EXPIRED       =  4L
ALARM_KILLED        =  8L
ALARM_ABORTED       = 10L
ALARM_CANCELED      = 20L

ALARM_STATES = \
{
    ALARM_INACTIVE: "Inactive",
    ALARM_ACTIVE:   "Active",
    ALARM_DONE:     "Done",
    ALARM_EXPIRED:  "Expired",
    ALARM_KILLED:   "Killed",
    ALARM_ABORTED:  "Aborted",
    ALARM_CANCELED: "Canceled"
}

NORMAL_MSG          = 1L
URGENT_MSG          = 2L

MSG_PRIORITY = \
{
    NORMAL_MSG:     "Normal",
    URGENT_MSG:     "Urgent"
}

ENV_MBOX            = 0L
ENV_READ            = 1L

ENVELOPE_STATE = \
{
    ENV_MBOX: "MBOX",
    ENV_READ: "READ"
}

TASK_STATES = \
{
    TSTATE_READY:   "READY",
    INACTIVE_BLOCK: "INACTIVE BLOCK",
    MUTEX_WAIT:     "MUTEX WAIT",
    QUEUE_WAIT:     "QUEUE WAIT",
    PARTITION_WAIT: "PARTITION WAIT",
    MAILBOX_WAIT:   "MAILBOX WAIT",
    ALARM_WAIT:     "ALARM WAIT",
    SEMAPHORE_WAIT: "SEMAPHORE WAIT",
    PIPE_WAIT:      "PIPE WAIT",
    SLEEP_BLOCK:    "SLEEP BLOCK",
    ACK_BLOCK:      "ACK BLOCK",
    ABORT_BLOCK:    "ABORT BLOCK",
    SUSPEND_BLOCK:  "SUSPEND BLOCK"
}

EXTCONTEXT_UNDEFINED    = 0x00
EXTCONTEXT_ENABLED      = 0x01
EXTCONTEXT_DISABLED     = 0x40

VFP_MODE_TEXT = \
{
    EXTCONTEXT_UNDEFINED:   "UNDEFINED",
    EXTCONTEXT_ENABLED:     "ENABLED",
    EXTCONTEXT_DISABLED:    "DISABLED"
}

M_REG_GEN_NAMES = \
[
    [ "FPSXC", "fpscr"  ],
    [ "xPSR",  "psr"    ],
    [ "CPSR",  "psr"    ],
    [   "R0",  "pksnum" ],
    [   "R1",  "r1"     ],
    [   "R2",  "r2"     ],
    [   "R3",  "r3"     ],
    [   "R4",  "r4"     ],
    [   "R5",  "r5"     ],
    [   "R6",  "r6"     ],
    [   "R7",  "r7"     ],
    [   "R8",  "r8"     ],
    [   "R9",  "r9"     ],
    [  "R10",  "r10"    ],
    [  "R11",  "r11"    ],
    [  "R12",  "r12"    ],
    [  "R14",  "r14"    ],
    [   "LR",  "r14"    ],
    [   "PC",  "pc"     ]
]

A_REG_GEN_NAMES = \
[
    [ "FPEXE", "fpexc"  ],
    [ "CPSR",  "cpsr"   ],
    [   "R0",  "pksnum" ],
    [   "R1",  "r1"     ],
    [   "R2",  "r2"     ],
    [   "R3",  "r3"     ],
    [   "R4",  "r4"     ],
    [   "R5",  "r5"     ],
    [   "R6",  "r6"     ],
    [   "R7",  "r7"     ],
    [   "R8",  "r8"     ],
    [   "R9",  "r9"     ],
    [  "R10",  "r10"    ],
    [  "R11",  "r11"    ],
    [  "R12",  "r12"    ],
    [  "R14",  "r14"    ],
    [   "LR",  "r14"    ],
    [   "PC",  "pc"     ]
]

REG_VFP_NAMES = \
[
    [   "D0",  "d0"     ],
    [   "D1",  "d1"     ],
    [   "D2",  "d2"     ],
    [   "D3",  "d3"     ],
    [   "D4",  "d4"     ],
    [   "D5",  "d5"     ],
    [   "D6",  "d6"     ],
    [   "D7",  "d7"     ],
    [   "D8",  "d8"     ],
    [   "D9",  "d9"     ],
    [  "D10",  "d10"    ],
    [  "D11",  "d11"    ],
    [  "D12",  "d12"    ],
    [  "D13",  "d13"    ],
    [  "D14",  "d14"    ],
    [  "D15",  "d15"    ],
    [  "D16",  "d16"    ],
    [  "D17",  "d17"    ],
    [  "D18",  "d18"    ],
    [  "D19",  "d19"    ],
    [  "D20",  "d20"    ],
    [  "D21",  "d21"    ],
    [  "D22",  "d22"    ],
    [  "D23",  "d23"    ],
    [  "D24",  "d24"    ],
    [  "D25",  "d25"    ],
    [  "D26",  "d26"    ],
    [  "D27",  "d27"    ],
    [  "D28",  "d28"    ],
    [  "D29",  "d29"    ],
    [  "D30",  "d30"    ],
    [  "D31",  "d31"    ],
    [   "S0",  "f0"     ],
    [   "S1",  "f1"     ],
    [   "S2",  "f2"     ],
    [   "S3",  "f3"     ],
    [   "S4",  "f4"     ],
    [   "S5",  "f5"     ],
    [   "S6",  "f6"     ],
    [   "S7",  "f7"     ],
    [   "S8",  "f8"     ],
    [   "S9",  "f9"     ],
    [  "S10",  "f10"    ],
    [  "S11",  "f11"    ],
    [  "S12",  "f12"    ],
    [  "S13",  "f13"    ],
    [  "S14",  "f14"    ],
    [  "S15",  "f15"    ],
    [  "S16",  "f16"    ],
    [  "S17",  "f17"    ],
    [  "S18",  "f18"    ],
    [  "S19",  "f19"    ],
    [  "S20",  "f20"    ],
    [  "S21",  "f21"    ],
    [  "S22",  "f22"    ],
    [  "S23",  "f23"    ],
    [  "S24",  "f24"    ],
    [  "S25",  "f25"    ],
    [  "S26",  "f26"    ],
    [  "S27",  "f27"    ],
    [  "S28",  "f28"    ],
    [  "S29",  "f29"    ],
    [  "S30",  "f30"    ],
    [  "S31",  "f31"    ]
]

def ACCESS_pKWS( debugSession ):
    return debugSession.evaluateExpression( "pKWS" )

def getocdt( kclass, debugSession ):
    pkws = ACCESS_pKWS( debugSession )
    return pkws.dereferencePointer( ).getStructureMembers( )[ "KWS_pOCDT" ].getArrayElements( )[ kclass ]

def KWS_peframe( debugSession ):
    pkws = ACCESS_pKWS( debugSession )
    return pkws.dereferencePointer( ).getStructureMembers( )[ "KWS_peframe" ]

def KWS_sysprop( debugSession ):
    pkws = ACCESS_pKWS( debugSession )
    return pkws.dereferencePointer( ).getStructureMembers( )[ "KWS_sysprop" ]

def KWS_sysrambase( debugSession ):
    pkws = ACCESS_pKWS( debugSession )
    return pkws.dereferencePointer( ).getStructureMembers( )[ "KWS_sysrambase" ]

def KWS_sysramsize( debugSession ):
    pkws = ACCESS_pKWS( debugSession )
    return pkws.dereferencePointer( ).getStructureMembers( )[ "KWS_sysramsize" ]

def KWS_prtxcstk( debugSession ):
    pkws = ACCESS_pKWS( debugSession )
    return pkws.dereferencePointer( ).getStructureMembers( )[ "KWS_prtxcstk" ]

def KWS_noschedflg( debugSession ):
    pkws = ACCESS_pKWS( debugSession )
    return pkws.dereferencePointer( ).getStructureMembers( )[ "KWS_noschedflg" ]

def GETPTCB( pocdt, debugSession, index=0 ):
    pobjbase = pocdt.dereferencePointer( ).getStructureMembers( )[ "pobjbase" ]
    return debugSession.evaluateExpression( "(TCB*)(" + str( pobjbase.readAsNumber( ) ) + ") + " + str( index ) )

def GETPSH( pocdt, debugSession, index=0 ):
    pobjbase = pocdt.dereferencePointer( ).getStructureMembers( )[ "pobjbase" ]
    return debugSession.evaluateExpression( "(SHEADER*)(" + str( pobjbase.readAsNumber( ) ) + ") + " + str( index ) )

def GETPMH( pocdt, debugSession, index=0 ):
    pobjbase = pocdt.dereferencePointer( ).getStructureMembers( )[ "pobjbase" ]
    return debugSession.evaluateExpression( "(MHEADER*)(" + str( pobjbase.readAsNumber( ) ) + ") + " + str( index ) )

def GETPQH( pocdt, debugSession, index=0 ):
    pobjbase = pocdt.dereferencePointer( ).getStructureMembers( )[ "pobjbase" ]
    return debugSession.evaluateExpression( "(QHEADER*)(" + str( pobjbase.readAsNumber( ) ) + ") + " + str( index ) )

def GETPPH( pocdt, debugSession, index=0 ):
    pobjbase = pocdt.dereferencePointer( ).getStructureMembers( )[ "pobjbase" ]
    return debugSession.evaluateExpression( "(PHEADER*)(" + str( pobjbase.readAsNumber( ) ) + ") + " + str( index ) )

def GETPUH( pocdt, debugSession, index=0 ):
    pobjbase = pocdt.dereferencePointer( ).getStructureMembers( )[ "pobjbase" ]
    return debugSession.evaluateExpression( "(UHEADER*)(" + str( pobjbase.readAsNumber( ) ) + ") + " + str( index ) )

def GETPPCH( pocdt, debugSession, index=0 ):
    pobjbase = pocdt.dereferencePointer( ).getStructureMembers( )[ "pobjbase" ]
    return debugSession.evaluateExpression( "(PCHEADER*)(" + str( pobjbase.readAsNumber( ) ) + ") + " + str( index ) )

def GETPEH( pocdt, debugSession, index=0 ):
    pobjbase = pocdt.dereferencePointer( ).getStructureMembers( )[ "pobjbase" ]
    return debugSession.evaluateExpression( "(EHEADER*)(" + str( pobjbase.readAsNumber( ) ) + ") + " + str( index ) )

def GETPSCH( pocdt, debugSession, index=0 ):
    pobjbase = pocdt.dereferencePointer( ).getStructureMembers( )[ "pobjbase" ]
    return debugSession.evaluateExpression( "(SCHEADER*)(" + str( pobjbase.readAsNumber( ) ) + ") + " + str( index ) )

def GETPCCH( pocdt, debugSession, index=0 ):
    pobjbase = pocdt.dereferencePointer( ).getStructureMembers( )[ "pobjbase" ]
    return debugSession.evaluateExpression( "(CCHEADER*)(" + str( pobjbase.readAsNumber( ) ) + ") + " + str( index ) )

def GETPACH( pocdt, debugSession, index=0 ):
    pobjbase = pocdt.dereferencePointer( ).getStructureMembers( )[ "pobjbase" ]
    return debugSession.evaluateExpression( "(ACHEADER*)(" + str( pobjbase.readAsNumber( ) ) + ") + " + str( index ) )

def getStatics( pocdt, debugSession ):
    return pocdt.dereferencePointer( ).getStructureMembers( )[ "n_statics" ].readAsNumber( )

def getObjects( pocdt, debugSession ):
    return pocdt.dereferencePointer( ).getStructureMembers( )[ "n_objects" ].readAsNumber( )

def gethipritsk( debugSession ):
    pkws = ACCESS_pKWS( debugSession )
    return pkws.dereferencePointer( ).getStructureMembers( )[ "KWS_hipritsk" ]

def GetObjectName( kclass, objnum, debugSession ):
    name = "OBJ" + str( objnum )
    pkws = ACCESS_pKWS( debugSession )
    pocdt = getocdt( kclass, debugSession )
    if kclass == TASK_KCLASS and objnum == 0:
        return "<NullTask>"
    if kclass == COUNTER_KCLASS and objnum == 0:
        return "<TIMEBASE>"
    n_statics = getStatics( pocdt, debugSession )
    n_objects = getObjects( pocdt, debugSession )
    if objnum <= n_statics:
        pstaticnames = pocdt.dereferencePointer( ).getStructureMembers( )[ "pstaticnames" ].readAsNumber( )
        if pstaticnames == 0:
            return "<N/A>"
        else:
            namelen = pocdt.dereferencePointer( ).getStructureMembers( )[ "namelen" ].readAsNumber( )
            expr = "(char*)(" + hex( pstaticnames ) + "+" + hex( ( objnum - 1 ) * ( namelen + 1 ) ) + ")"
            name = debugSession.evaluateExpression( expr ).readAsNullTerminatedString( )
            if len( name ) == 0:
                name = "<Anonymous>"
    else:
        pnamelist = pocdt.dereferencePointer( ).getStructureMembers( )[ "pnamelist" ].readAsNumber( )
        if pnamelist == 0 or objnum > n_objects:
            return "<?$>"
        expr = "(NAMELIST*)(" + hex( pnamelist ) + ") + " + str( objnum - n_statics - 1 )
        pnamelist = debugSession.evaluateExpression( expr )
        inuse = pnamelist.dereferencePointer( ).getStructureMembers( )[ "use" ].readAsNumber( )
        if inuse == 0:
            return "<?$>"
        else:
            u = pnamelist.dereferencePointer( ).getStructureMembers( )[ "u" ]
            pname = u.getStructureMembers( )[ "pname" ].readAsNumber( )
            if pname == 0:
                return "<Anonymous>"
            name = debugSession.evaluateExpression( "(char*)" + str( pname ) ).readAsNullTerminatedString( )

    return name

def isObjectInuse( pocdt, index, debugSession ):
    use = 0
    pnamelist = pocdt.dereferencePointer( ).getStructureMembers( )[ "pnamelist" ].readAsNumber( )
    if pnamelist != 0:
        expr = "(NAMELIST*)(" + hex( pnamelist ) + ") + " + str( index )
        p = debugSession.evaluateExpression( expr )
        use = p.dereferencePointer( ).getStructureMembers( )[ "use" ].readAsNumber( )
    return use

def getTaskStatusText( status ):
    if status != TSTATE_READY and status != INACTIVE_BLOCK and status != MUTEX_WAIT and \
       status != QUEUE_WAIT and status != PARTITION_WAIT and status != MAILBOX_WAIT and \
       status != ALARM_WAIT and status != SEMAPHORE_WAIT and status != PIPE_WAIT and \
       status != SLEEP_BLOCK and status != ACK_BLOCK and status != ABORT_BLOCK and status != SUSPEND_BLOCK:
        return "Unknown"
    return TASK_STATES[ status ]

def getAlarmStatusText( status ):
    if status != ALARM_INACTIVE and status != ALARM_ACTIVE and status != ALARM_DONE and \
       status != ALARM_EXPIRED and status != ALARM_KILLED and status != ALARM_ABORTED and \
       status != ALARM_CANCELED:
        return "Unknown"
    return ALARM_STATES[ status ]

def getMsgPriText( priority ):
    if priority != NORMAL_MSG and priority != URGENT_MSG:
        return "Unknown"
    return MSG_PRIORITY[ priority ]

def getEnvelopText( state ):
    if state != ENV_MBOX and state != ENV_READ:
        return "Unknown"
    return ENVELOPE_STATE[ state ]

def getVfpModeText( mode ):
    if mode != EXTCONTEXT_UNDEFINED and mode != EXTCONTEXT_ENABLED and mode != EXTCONTEXT_DISABLED:
        return "Unknown"
    return VFP_MODE_TEXT[ mode ]

def addressExprsToLong( expr ):
    addr = expr.getLocationAddress()
    return addr.getLinearAddress()

def getStackFrameMemberOffset( frame, member, debugSession ):
    offset = -1
    hipritsk = gethipritsk( debugSession )
    f = hipritsk.dereferencePointer( ).getStructureMembers( )[ frame ]
    members = f.dereferencePointer( ).getStructureMembers( )
    if member in members:
        baseAddr = f.readAsNumber( )
        memberAddr = addressExprsToLong( members[ member ] )
        offset = memberAddr - baseAddr
    return offset

def createRegisterMap( register_map, names, debugSession ):
    j = len( names )
    for i in range( j ):
        register_map[ names[ i ][ 0 ] ] = getStackFrameMemberOffset( "sp", names[ i ][ 1 ], debugSession )

def makeAddressCell( members, name ):
    if name in members:
        return createTextCell( str( members[ name ].readAsAddress( ) ) )
    else:
        return createTextCell( "N/A" )

def makeNumberCell( members, name ):
    if name in members:
        return createTextCell( str( members[ name ].readAsNumber( ) ) )
    else:
        return createTextCell( "N/A" )

def checkAttributes( kclass, attributes, debugSession ):
    pocdt = getocdt( kclass, debugSession )
    attr = pocdt.dereferencePointer( ).getStructureMembers( )[ "attributes" ].readAsNumber( )
    if attr & attributes:
        return True
    return False

def getWaiters( members, debugSession ):
    waiters = "None"
    pwh = members[ "waiters" ]
    while pwh.readAsNumber( ):
        pwhMembers = pwh.dereferencePointer( ).getStructureMembers( )
        ptcb = pwhMembers[ "ptcb" ]
        if ptcb.readAsNumber( ):
            taskMembers = ptcb.dereferencePointer( ).getStructureMembers( )
            task = taskMembers[ "task" ].readAsNumber( )
            taskName = GetObjectName( TASK_KCLASS, task, debugSession )
            pach = taskMembers[ "palarm" ]
            if pach.readAsNumber( ):
                pachMembers = pach.dereferencePointer( ).getStructureMembers( )
                pcch = pachMembers[ "pcch" ]
                pcchMembers = pcch.dereferencePointer( ).getStructureMembers( )
                counter = pcchMembers[ "counter" ].readAsNumber( )
                counterName = GetObjectName( COUNTER_KCLASS, counter, debugSession )
                expiration = pachMembers[ "expiration" ].readAsNumber( )
                accumulator = pcchMembers[ "accumulator" ].readAsNumber( )
                ticksRemaining = expiration - accumulator
                waitingText = taskName + "(" + counterName + "/" + str( ticksRemaining ) + ")"
            else:
                waitingText = taskName
            if waiters == "None":
                waiters = waitingText
            else:
                waiters = waiters + "," + waitingText
        pwh = pwhMembers[ "flink" ]
    return waiters

def getSemaWaiters( taskName, members, debugSession ):
    waiters = "None"
    sp = members[ "sp" ]
    pctrl = debugSession.evaluateExpression( "(TOSCTRL*)(" + str( sp.readAsNumber( ) ) + ")" )
    if pctrl.readAsNumber( ):
        pctrlMembers = pctrl.dereferencePointer( ).getStructureMembers( )
        pctrl_tos = pctrlMembers[ "tos" ].readAsNumber( )
        tosAddr = addressExprsToLong( pctrlMembers[ "tos" ] )
        pwh = debugSession.evaluateExpression( "(WHEADER*)((" + str( tosAddr ) + ") + 4)" )
        while pwh.readAsNumber( ) < pctrl_tos:
            objnum = pwh.dereferencePointer( ).getStructureMembers( )[ "objnum" ]
            name = GetObjectName( SEMA_KCLASS, objnum.readAsNumber( ), debugSession )
            pwh = debugSession.evaluateExpression( "(WHEADER*)(" + str( pwh.readAsNumber( ) ) + ") + 1" )
            if waiters == "None":
                waiters = name
            else:
                waiters = waiters + "," + name

    return waiters

def longToHex( number ):
    return '0x%08X' % number

def getPWH( members, debugSession ):
    sp = members[ "sp" ]
    tosctrl = debugSession.evaluateExpression( "(TOSCTRL*)(" + str( sp.readAsNumber( ) ) + ") + 1" )
    return debugSession.evaluateExpression( "(WHEADER*)(" + str( tosctrl.readAsNumber( ) ) + ")" )

def getWaiter( kclass, members, debugSession ):
    pwh = getPWH( members, debugSession )
    pwhMembers = pwh.dereferencePointer( ).getStructureMembers( )
    objno = pwhMembers[ "objnum" ].readAsNumber( )
    return GetObjectName( kclass, objno, debugSession )

def getTaskWaitingObjects( status, taskName, members, debugSession ):
    objects = ""
    if status & SEMAPHORE_WAIT:
        objects = getSemaWaiters( taskName, members, debugSession )
    if status & PARTITION_WAIT:
        objects = getWaiter( PART_KCLASS, members, debugSession )
    if status & QUEUE_WAIT:
        objects = getWaiter( QUEUE_KCLASS, members, debugSession )
    if status & MUTEX_WAIT:
        objects = getWaiter( MUTX_KCLASS, members, debugSession )
    if status & MAILBOX_WAIT:
        objects = getWaiter( MBOX_KCLASS, members, debugSession )
    if status & ALARM_WAIT:
        objects = getWaiter( ALARM_KCLASS, members, debugSession )
    return objects

def getTickoutInfo( members, debugSession ):
    info = ""
    pach = members[ "palarm" ]
    if pach.readAsNumber( ):
        pachMembers = pach.dereferencePointer( ).getStructureMembers( )
        pcch = pachMembers[ "pcch" ]
        if pcch.readAsNumber( ):
            pcchMembers = pcch.dereferencePointer( ).getStructureMembers( )
            counter = pcchMembers[ "counter" ].readAsNumber( )
            counterName = GetObjectName( COUNTER_KCLASS, counter, debugSession )
            expiration = pachMembers[ "expiration" ].readAsNumber( )
            accumulator = pcchMembers[ "accumulator" ].readAsNumber( )
            ticksRemaining = expiration - accumulator
            info = counterName + "/" + str( ticksRemaining )
    return info

def getAlarmTickoutInfo( members, debugSession ):
    info = ""
    pxh = members[ "pxh" ]
    pach = debugSession.evaluateExpression( "(ACHEADER*)(" + str( pxh.readAsNumber( ) ) + ")" )
    if pach.readAsNumber( ):
        pachMembers = pach.dereferencePointer( ).getStructureMembers( )
        pcch = pachMembers[ "pcch" ]
        if pcch.readAsNumber( ):
            pcchMembers = pcch.dereferencePointer( ).getStructureMembers( )
            counter = pcchMembers[ "counter" ].readAsNumber( )
            counterName = GetObjectName( COUNTER_KCLASS, counter, debugSession )
            expiration = pachMembers[ "expiration" ].readAsNumber( )
            accumulator = pcchMembers[ "accumulator" ].readAsNumber( )
            ticksRemaining = expiration - accumulator
            info = counterName + "/" + str( ticksRemaining )
    return info

def isMember( member, members ):
    if member in members:
        return True
    return False

def getStackFillChar( debugSession ):
    fillChar = 0
    archName = debugSession.getTargetInformation( ).getArchitecture( ).getName( )
    if archName == "ARMv7M" or archName == "ARMv7R" or archName == "ARMv6M":
        fillChar = 0xFFFFFFFF
    return fillChar

def make_reg_list(offset, size, *reg_names):
    result = [("%s" % reg_names[x], long(offset + x*size)) for x in xrange(len(reg_names))]
    return result

def make_reg_range(offset, size, prefix, start, count):
    result = [("%s%d" % (prefix, start+x), long(offset + x*size)) for x in xrange(0, count)]
    return result

