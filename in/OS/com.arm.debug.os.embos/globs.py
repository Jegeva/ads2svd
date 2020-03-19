################################################################################
#
# Copyright (C) 2014,2017 Arm Limited (or its affiliates). All rights reserved.
#
# embOS - 3.88c ARM Cortex M / 3.88h ARM Cortex A
#
#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

# Import all!
from osapi import *

# General definitions
OS_EMBOS                            = "embos"

# Global Variables
OS_GLOBAL                           = "OS_Global"
OS_VERSION                          = "OS_Version"
OS_INTMSINC                         = "OS_IntMSInc"
OS_STATUS                           = "OS_Status"
OS_RUNNING                          = "OS_Running"
OS_INITIALSUSPENDCNT                = "OS_InitialSuspendCnt"
OS_ININT                            = "OS_InInt"
OS_TICKSTEP                         = "OS_TickStep"
OS_TICKSTEPTIME                     = "OS_TickStepTime"
OS_TICKSPERMS                       = "OS_TicksPerMS"
OS_INTTICKSINC                      = "OS_IntTicksInc"
OS_TS_EXECSTART                     = "OS_TS_ExecStart"
PROFILINGON                         = "ProfilingOn"
OS_INTIMER                          = "OS_InTimer"
OS_INITCALLED                       = "OS_InitCalled"
OS_POWER_LEVELS                     = "OS_POWER_Levels"
OS_CPU_LOAD                         = "OS_CPU_Load"
OS_IDLECNT                          = "OS_IdleCnt"
OS_PRSEMA                           = "OS_pRSema"
OS_PQHEAD                           = "OS_pQHead"
OS_PMAILBOX                         = "OS_pMailbox"
OS_PCSEMA                           = "OS_pCSema"
OS_PMEMF                            = "OS_pMEMF"
OS_PTICKHOOK                        = "OS_pTickHook"
OS_PTLS                             = "OS_pTLS"
OS_PFONTERMINATE                    = "OS_pfOnTerminate"
OS_SYSSTACKBASEADDR                 = "OS_SysStackBaseAddr"
OS_SYSSTACKSIZE                     = "OS_SysStackSize"
OS_SYSSTACKLIMIT                    = "OS_SysStackLimit"
SYSTEMCORECLOCK                     = "SystemCoreClock"
STACK_MEM                           = "Stack_Mem"
STACK_LIMIT                         = "Stack_Limit"
STACK_SIZE                          = "Stack_Size"
VECTORS                             = "__Vectors"
OS_JLINKMEM_BUFFERSIZE              = "OS_JLINKMEM_BufferSize"
OS_COUNTOFTRACEBUFFER               = "OS_countofTraceBuffer"
OS_PTRACEBUFFER                     = "OS_pTraceBuffer"
OS_COM_OUTBUFFERCNT                 = "OS_COM_OutBufferCnt"
OS_COM_STRINGLEN                    = "OS_COM_StringLen"

# Structure names
OS_COUNTERS                         = "OS_COUNTERS"
OS_PENDING                          = "OS_PENDING"
OS_GLOBALS                          = "OS_GLOBAL"
OS_TASK                             = "OS_TASK"
OS_WAIT_LIST                        = "OS_WAIT_LIST"
OS_WAIT_OBJ                         = "OS_WAIT_OBJ"
OS_WAIT_OBJ_EX                      = "OS_WAIT_OBJ_EX"
OS_EXTEND_TASK_CONTEXT              = "OS_EXTEND_TASK_CONTEXT"
OS_TIMER                            = "OS_TIMER"
OS_TIMER_EX                         = "OS_TIMER_EX"
OS_TICK_HOOK                        = "OS_TICK_HOOK"
OS_ON_TERMINATE_HOOK                = "OS_ON_TERMINATE_HOOK"
OS_RSEMA                            = "OS_RSEMA"
OS_CSEMA                            = "OS_CSEMA"
OS_MAILBOX                          = "OS_MAILBOX"
OS_Q                                = "OS_Q"
OS_MEMF                             = "OS_MEMF"
OS_EVENT                            = "OS_EVENT"
OS_TRACE_ENTRY                      = "OS_TRACE_ENTRY"

# Structure member names

# Wait object structure members
OS_WAIT_OBJ_PWAITLIST               = "pWaitList"

# Wait object (extended) structure members
OS_WAIT_OBJ_EX_WAITOBJ              = "WaitObj"

# Wait list structure members
OS_WAIT_LIST_PNEXT                  = "pNext"
OS_WAIT_LIST_PPREV                  = "pPrev"
OS_WAIT_LIST_PWAITOBJ               = "pWaitObj"
OS_WAIT_LIST_PTASK                  = "pTask"

# Extended task context structure members
OS_EXTEND_TASK_CONTEXT_PFSAVE       = "pfSave"
OS_EXTEND_TASK_CONTEXT_PFRESTORE    = "pfRestore"

# Task structure members
OS_TASK_PNEXT                       = "pNext"
OS_TASK_PSTACK                      = "pStack"
OS_TASK_PWAITLIST                   = "pWaitList"
OS_TASK_TIMEOUT                     = "Timeout"
OS_TASK_STAT                        = "Stat"
OS_TASK_PRIORITY                    = "Priority"
OS_TASK_EVENTS                      = "Events"
OS_TASK_EVENT_MASK                  = "EventMask"
OS_TASK_PPREV                       = "pPrev"
OS_TASK_NAME                        = "Name"
OS_TASK_STACKSIZE                   = "StackSize"
OS_TASK_PSTACKBOT                   = "pStackBot"
OS_TASK_NUMACTIVATIONS              = "NumActivations"
OS_TASK_NUMPREEMPTIONS              = "NumPreemptions"
OS_TASK_EXECTOTAL                   = "ExecTotal"
OS_TASK_EXECLAST                    = "ExecLast"
OS_TASK_LOAD                        = "Load"
OS_TASK_TIMESLICEREM                = "TimeSliceRem"
OS_TASK_TIMESLICERELOAD             = "TimeSliceReload"
OS_TASK_PEXTENDCONTEXT              = "pExtendContext"
OS_TASK_PTLS                        = "pTLS"
OS_TASK_ID                          = "Id"

# Timer structure members
OS_TIMER_PNEXT                      = "pNext"
OS_TIMER_HOOK                       = "Hook"
OS_TIMER_TIME                       = "Time"
OS_TIMER_PERIOD                     = "Period"
OS_TIMER_ACTIVE                     = "Active"
OS_TIMER_ID                         = "Id"

# Timer (extended) structure members
OS_TIMER_EX_TIMER                   = "Timer"
OS_TIMER_EX_PFUSER                  = "pfUser"
OS_TIMER_EX_PDATA                   = "pData"

# Task hook structure members
OS_TICK_HOOK_PNEXT                  = "pNext"
OS_TICK_HOOK_PFUSER                 = "pfUser"

# Terminate hook structure members
OS_ON_TERMINATE_HOOK_PNEXT          = "pNext"
OS_ON_TERMINATE_HOOK_PFUSER         = "pfUser"

# Resource semaphore structure members
OS_RSEMA_WAITOBJ                    = "WaitObj"
OS_RSEMA_PTASK                      = "pTask"
OS_RSEMA_USECNT                     = "UseCnt"
OS_RSEMA_PNEXT                      = "pNext"
OS_RSEMA_ID                         = "Id"

# Counting semaphore structure members
OS_CSEMA_WAITOBJ                    = "WaitObj"
OS_CSEMA_CNT                        = "Cnt"
OS_CSEMA_PNEXT                      = "pNext"
OS_CSEMA_ID                         = "Id"

# Mailbox structure members
OS_MAILBOX_WAITOBJ                  = "WaitObj"
OS_MAILBOX_PNEXT                    = "pNext"
OS_MAILBOX_PDATA                    = "pData"
OS_MAILBOX_NOFMSG                   = "nofMsg"
OS_MAILBOX_MAXMSG                   = "maxMsg"
OS_MAILBOX_IRD                      = "iRd"
OS_MAILBOX_SIZEOFMSG                = "sizeofMsg"
OS_MAILBOX_ID                       = "Id"

# Queue structure members
OS_Q_WAITOBJ                        = "WaitObj"
OS_Q_PNEXT                          = "pNext"
OS_Q_PDATA                          = "pData"
OS_Q_SIZE                           = "Size"
OS_Q_MSGCNT                         = "MsgCnt"
OS_Q_OFFFIRST                       = "offFirst"
OS_Q_OFFLAST                        = "offLast"
OS_Q_INUSE                          = "InUse"
OS_Q_INPROGRESSCNT                  = "InProgressCnt"
OS_Q_ID                             = "Id"

# Fixed memory block structure members
OS_MEMF_WAITOBJ                     = "WaitObj"
OS_MEMF_PNEXT                       = "pNext"
OS_MEMF_PPOOL                       = "pPool"
OS_MEMF_NUMBLOCKS                   = "NumBlocks"
OS_MEMF_BLOCKSIZE                   = "BlockSize"
OS_MEMF_NUMFREEBLOCKS               = "NumFreeBlocks"
OS_MEMF_MAXUSED                     = "MaxUsed"
OS_MEMF_PFREE                       = "pFree"
OS_MEMF_AIPURPOSE                   = "aiPurpose"
OS_MEMF_ID                          = "Id"

# Event structure members
OS_EVENT_WAITOBJ                    = "WaitObj"
OS_EVENT_SIGNALED                   = "Signaled"
OS_EVENT_RESETMODE                  = "ResetMode"
OS_EVENT_ID                         = "Id"

# Trace entry structure members
OS_TRACE_ENTRY_TIME                 = "Time"
OS_TRACE_ENTRY_PCURRENTTASK         = "pCurrentTask"
OS_TRACE_ENTRY_P                    = "p"
OS_TRACE_ENTRY_V                    = "v"
OS_TRACE_ENTRY_IROUT                = "iRout"

# Globals structure members
OS_GLOBALS_COUNTERS                 = "Counters"
OS_GLOBALS_PENDING                  = "Pending"
OS_GLOBALS_PCURRENTTASK             = "pCurrentTask"
OS_GLOBALS_IPL_DI                   = "Ipl_DI"
OS_GLOBALS_IPL_EI                   = "Ipl_EI"
OS_GLOBALS_PTASK                    = "pTask"
OS_GLOBALS_PACTIVETASK              = "pActiveTask"
OS_GLOBALS_PTIMER                   = "pTimer"
OS_GLOBALS_PCURRENTTIMER            = "pCurrentTimer"
OS_GLOBALS_PFCHECKTIMER             = "pfCheckTimer"
OS_GLOBALS_TIME                     = "Time"
OS_GLOBALS_TIMEDEX                  = "TimeDex"
OS_GLOBALS_TIMESLICE                = "TimeSlice"
OS_GLOBALS_TIMESLICEATSTART         = "TimeSliceAtStart"

# Counters structure
OS_COUNTERS_REGION                  = "Region"
OS_COUNTERS_DI                      = "DI"

# Pending structure
OS_PENDING_ROUNDROBIN               = "RoundRobin"
OS_PENDING_TASKSWITCH               = "TaskSwitch"

# Function names
# ....

# Global structure names
OS_VFP_EXTENDCONTEXT                = "OS_VFP_ExtendContext"
OS_NEON_EXTENDCONTEXT               = "OS_NEON_ExtendContext"
OS_SWITCHAFTERISR_ARM               = "OS_SwitchAfterISR_ARM"

# Error codes/text
ERROR_TEXT = \
[
    "OS_ERR_ISR_INDEX",                      # 100
    "OS_ERR_ISR_VECTOR",                     # 101
    "OS_ERR_ISR_PRIO",                       # 102
    "OS_ERR_WRONG_STACK",                    # 103
    "OS_ERR_ISR_NO_HANDLER",                 # 104
    "OS_ERR_TLS_INIT",                       # 105
    "OS_ERR_MB_BUFFER_SIZE",                 # 106
    "107",                                   # 107
    "108",                                   # 108
    "109",                                   # 109
    "110",                                   # 110
    "111",                                   # 111
    "112",                                   # 112
    "113",                                   # 113
    "114",                                   # 114
    "115",                                   # 115
    "OS_ERR_EXTEND_CONTEXT",                 # 116
    "OS_ERR_TIMESLICE",                      # 117
    "OS_ERR_INTERNAL",                       # 118
    "OS_ERR_IDLE_RETURNS",                   # 119
    "OS_ERR_STACK",                          # 120
    "OS_ERR_CSEMA_OVERFLOW",                 # 121
    "OS_ERR_POWER_OVER",                     # 122
    "OS_ERR_POWER_UNDER",                    # 123
    "OS_ERR_POWER_INDEX",                    # 124
    "OS_ERR_SYS_STACK",                      # 125
    "OS_ERR_INT_STACK",                      # 126
    "127",                                   # 127
    "OS_ERR_INV_TASK",                       # 128
    "OS_ERR_INV_TIMER",                      # 129
    "OS_ERR_INV_MAILBOX",                    # 130
    "129",                                   # 131
    "OS_ERR_INV_CSEMA",                      # 132
    "OS_ERR_INV_RSEMA",                      # 133
    "134",                                   # 134
    "OS_ERR_MAILBOX_NOT1",                   # 135
    "OS_ERR_MAILBOX_DELETE",                 # 136
    "OS_ERR_CSEMA_DELETE",                   # 137
    "OS_ERR_RSEMA_DELETE",                   # 138
    "139",                                   # 139
    "OS_ERR_MAILBOX_NOT_IN_LIST",            # 140
    "141",                                   # 141
    "OS_ERR_TASKLIST_CORRUPT",               # 142
    "OS_ERR_QUEUE_INUSE",                    # 143
    "OS_ERR_QUEUE_NOT_INUSE",                # 144
    "OS_ERR_QUEUE_INVALID",                  # 145
    "OS_ERR_QUEUE_DELETE",                   # 146
    "147",                                   # 147
    "148",                                   # 148
    "149",                                   # 149
    "OS_ERR_UNUSE_BEFORE_USE",               # 150
    "OS_ERR_LEAVEREGION_BEFORE_ENTERREGION", # 151
    "OS_ERR_LEAVEINT",                       # 152
    "OS_ERR_DICNT",                          # 153
    "OS_ERR_INTERRUPT_DISABLED",             # 154
    "OS_ERR_TASK_ENDS_WITHOUT_TERMINATE",    # 155
    "OS_ERR_RESOURCE_OWNER",                 # 156
    "OS_ERR_REGIONCNT",                      # 157
    "158",                                   # 158
    "159",                                   # 159
    "OS_ERR_ILLEGAL_IN_ISR",                 # 160
    "OS_ERR_ILLEGAL_IN_TIMER",               # 161
    "OS_ERR_ILLEGAL_OUT_ISR",                # 162
    "OS_ERR_NOT_IN_ISR",                     # 163
    "OS_ERR_IN_ISR",                         # 164
    "OS_ERR_INIT_NOT_CALLED",                # 165
    "OS_ERR_CPU_STATE_ISR_ILLEGAL",          # 166
    "OS_ERR_CPU_STATE_ILLEGAL",              # 167
    "OS_ERR_CPU_STATE_UNKNOWN",              # 168
    "169",                                   # 169
    "OS_ERR_2USE_TASK",                      # 170
    "OS_ERR_2USE_TIMER",                     # 171
    "OS_ERR_2USE_MAILBOX",                   # 172
    "OS_ERR_2USE_BSEMA",                     # 173
    "OS_ERR_2USE_CSEMA",                     # 174
    "OS_ERR_2USE_RSEMA",                     # 175
    "OS_ERR_2USE_MEMF",                      # 176
    "177",                                   # 177
    "178",                                   # 178
    "179",                                   # 179
    "OS_ERR_NESTED_RX_INT",                  # 180
    "181",                                   # 181
    "182",                                   # 182
    "183",                                   # 183
    "184",                                   # 184
    "185",                                   # 185
    "186",                                   # 186
    "187",                                   # 187
    "188",                                   # 188
    "189",                                   # 189
    "OS_ERR_MEMF_INV",                       # 190
    "OS_ERR_MEMF_INV_PTR",                   # 191
    "OS_ERR_MEMF_PTR_FREE",                  # 192
    "OS_ERR_MEMF_RELEASE",                   # 193
    "OS_ERR_MEMF_POOLADDR",                  # 194
    "OS_ERR_MEMF_BLOCKSIZE",                 # 195
    "196",                                   # 196
    "197",                                   # 197
    "198",                                   # 198
    "199",                                   # 199
    "OS_ERR_SUSPEND_TOO_OFTEN",              # 200
    "OS_ERR_RESUME_BEFORE_SUSPEND",          # 201
    "OS_ERR_TASK_PRIORITY",                  # 202
    "203",                                   # 203
    "204",                                   # 204
    "205",                                   # 205
    "206",                                   # 206
    "207",                                   # 207
    "208",                                   # 208
    "209",                                   # 209
    "OS_ERR_EVENT_INVALID",                  # 210
    "211",                                   # 211
    "OS_ERR_EVENT_DELETE",                   # 212
    "213",                                   # 213
    "214",                                   # 214
    "215",                                   # 215
    "216",                                   # 216
    "217",                                   # 217
    "218",                                   # 218
    "219",                                   # 219
    "OS_ERR_WAITLIST_RING",                  # 220
    "OS_ERR_WAITLIST_PREV",                  # 221
    "OS_ERR_WAITLIST_NEXT",                  # 222
    "OS_ERR_TICKHOOK_INVALID",               # 223
    "OS_ERR_TICKHOOK_FUNC_INVALID",          # 224
    "OS_ERR_NOT_IN_REGION",                  # 225
    "226",                                   # 226
    "227",                                   # 227
    "228",                                   # 228
    "229",                                   # 229
    "OS_ERR_NON_ALIGNED_INVALIDATE",         # 230
    "231",                                   # 231
    "232",                                   # 232
    "233",                                   # 233
    "234",                                   # 234
    "235",                                   # 235
    "236",                                   # 236
    "237",                                   # 237
    "238",                                   # 238
    "239",                                   # 239
    "240",                                   # 240
    "241",                                   # 241
    "242",                                   # 242
    "243",                                   # 243
    "244",                                   # 244
    "245",                                   # 245
    "246",                                   # 246
    "247",                                   # 247
    "248",                                   # 248
    "249",                                   # 249
    "250",                                   # 250
    "251",                                   # 251
    "252",                                   # 252
    "253",                                   # 253
    "OS_ERR_TRIAL_LIMIT"                     # 254
]

# Minimum/maximum system error numbers
OS_ERR_MIN = 100
OS_ERR_MAX = 254

# Register map names
REG_MAP_V7ABASIC                        = "v7ABasic"
REG_MAP_V7MVFP                          = "v7MVFP"
REG_MAP_V7MBASIC                        = "v7MBasic"
REG_MAP_V7ANEONINT                      = "v7ANeonInt"
REG_MAP_V7ANEON                         = "v7ANeon"
REG_MAP_V7AFPU16INT                     = "v7AFPU16Int"
REG_MAP_V7AFPU16                        = "v7AFPU16"
REG_MAP_V7ABASICINT                     = "v7ABasicInt"

# Get error test
def getErrorText( errorNo ):
    if ( errorNo < OS_ERR_MIN ) or ( errorNo > OS_ERR_MAX ):
        return str( errorNo )
    else:
        return ERROR_TEXT[ errorNo - OS_ERR_MIN ] + " (" + str( errorNo ) + ")"

# Create global reference
def globCreateRef( refs ):
    return '.'.join( refs )
