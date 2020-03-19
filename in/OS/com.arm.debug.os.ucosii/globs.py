# Copyright (C) 2013-2014,2017 Arm Limited (or its affiliates). All rights reserved.

# Import all!
from osapi import *

# uCOS-II Global Variables (add all possible variations for the name - this may change with different OS versions!)
OS_VERSION_NBR                  = [ "OSVersionNbr"              ]
OS_CPU_ARM_FP_EN                = [ "OSCPUArmFpEn"              ]       # Not required for V2.92.09 and above
OS_CPU_USAGE                    = [ "OSCPUUsage"                ]
OS_CTX_SW_CTR                   = [ "OSCtxSwCtr"                ]
OS_DEBUG_EN                     = [ "OSDebugEn"                 ]
OS_ENDLIANNESS_TEST             = [ "OSEndiannessTest"          ]
OS_EVENT_EN                     = [ "OSEventEn"                 ]
OS_EVENT_FREE_LIST              = [ "OSEventFreeList"           ]
OS_EVENT_MAX                    = [ "OSEventMax"                ]
OS_EVENT_MULTI_EN               = [ "OSEventMultiEn"            ]
OS_EVENT_NAME_EN                = [ "OSEventNameEn"             ]
OS_EVENT_SIZE                   = [ "OSEventSize"               ]
OS_EVENT_TBL                    = [ "OSEventTbl"                ]
OS_EVENT_TBL_SIZE               = [ "OSEventTblSize"            ]
OS_FLAG_EN                      = [ "OSFlagEn"                  ]
OS_FLAG_FREE_LIST               = [ "OSFlagFreeList"            ]
OS_FLAG_GRP_SIZE                = [ "OSFlagGrpSize"             ]
OS_FLAG_MAX                     = [ "OSFlagMax"                 ]
OS_FLAG_NAME_EN                 = [ "OSFlagNameEn"              ]
OS_FLAG_NODE_SIZE               = [ "OSFlagNodeSize"            ]
OS_FLAG_TBL                     = [ "OSFlagTbl"                 ]
OS_FLAG_WIDTH                   = [ "OSFlagWidth"               ]
OS_IDLE_CTR_MAX                 = [ "OSIdleCtrMax"              ]
OS_IDLE_CTR_RUN                 = [ "OSIdleCtrRun"              ]
OS_INT_NESTING                  = [ "OSIntNesting"              ]
OS_LOCK_NESTING                 = [ "OSLockNesting"             ]
OS_LOWEST_PRIO                  = [ "OSLowestPrio"              ]
OS_MBOX_EN                      = [ "OSMboxEn"                  ]
OS_MEM_EN                       = [ "OSMemEn"                   ]
OS_MEM_FREE_LIST                = [ "OSMemFreeList"             ]
OS_MEM_MAX                      = [ "OSMemMax"                  ]
OS_MEM_NAME_EN                  = [ "OSMemNameEn"               ]
OS_MEM_SIZE                     = [ "OSMemSize"                 ]
OS_MEM_TBL                      = [ "OSMemTbl"                  ]
OS_MEM_TBL_SIZE                 = [ "OSMemTblSize"              ]
OS_MULTI_EN                     = [ "OSMutexEn"                 ]
OS_PRIO_CUR                     = [ "OSPrioCur"                 ]
OS_PRIO_HIGH_RDY                = [ "OSPrioHighRdy"             ]
OS_PTR_SIZE                     = [ "OSPtrSize"                 ]
OS_Q_EN                         = [ "OSQEn"                     ]
OS_Q_FREE_LIST                  = [ "OSQFreeList"               ]
OS_Q_MAX                        = [ "OSQMax"                    ]
OS_Q_SIZE                       = [ "OSQSize"                   ]
OS_RDY_GRP                      = [ "OSRdyGrp"                  ]
OS_RDY_TBL_SIZE                 = [ "OSRdyTblSize"              ]
OS_RUNNING                      = [ "OSRunning"                 ]
OS_SAFETY_CRITIAL_START_FLAG    = [ "OSSafetyCriticalStartFlag" ]
OS_SEM_EN                       = [ "OSSemEn"                   ]
OS_STAT_RDY                     = [ "OSStatRdy"                 ]
OS_STK_WIDTH                    = [ "OSStkWidth"                ]
OS_TASK_CREATE_EN               = [ "OSTaskCreateEn"            ]
OS_TASK_CREATE_EXT_EN           = [ "OSTaskCreateExtEn"         ]
OS_TASK_CTR                     = [ "OSTaskCtr"                 ]
OS_TASK_DEL_EN                  = [ "OSTaskDelEn"               ]
OS_TASK_IDLE_STK_SIZE           = [ "OSTaskIdleStkSize"         ]
OS_TASK_MAX                     = [ "OSTaskMax"                 ]
OS_TASK_NAME_EN                 = [ "OSTaskNameEn"              ]
OS_TASK_PROFILE_EN              = [ "OSTaskProfileEn"           ]
OS_TASK_REG_NEXT_AVAIL_ID       = [ "OSTaskRegNextAvailID"      ]
OS_TASK_STAT_EN                 = [ "OSTaskStatEn"              ]
OS_TASK_STAT_STK_CHK_EN         = [ "OSTaskStatStkChkEn"        ]
OS_TASK_STAT_STK_SIZE           = [ "OSTaskStatStkSize"         ]
OS_TASK_SW_HOOK_EN              = [ "OSTaskSwHookEn"            ]
OS_TCB_CUR                      = [ "OSTCBCur"                  ]
OS_TCB_FREE_LIST                = [ "OSTCBFreeList"             ]
OS_TCB_HIGH_RDY                 = [ "OSTCBHighRdy"              ]
OS_TCB_LIST                     = [ "OSTCBList"                 ]
OS_TCB_PRIO_TBL_MAX             = [ "OSTCBPrioTblMax"           ]
OS_TCB_PRIO_TBL                 = [ "OSTCBPrioTbl"              ]
OS_TCB_SIZE                     = [ "OSTCBSize"                 ]
OS_TICKS_PER_SEC                = [ "OSTicksPerSec"             ]
OS_TICK_STEP_STATE              = [ "OSTickStepState"           ]
OS_TIME                         = [ "OSTime"                    ]
OS_TIME_TICK_HOOK_EN            = [ "OSTimeTickHookEn"          ]
OS_TLS_TBL_SIZE                 = [ "OS_TLS_TblSize"            ]
OS_TMR_CFG_MAX                  = [ "OSTmrCfgMax"               ]
OS_TMR_CFG_NAME_EN              = [ "OSTmrCfgNameEn"            ]
OS_TMR_CFG_TICKS_PER_SEC        = [ "OSTmrCfgTicksPerSec"       ]
OS_TMR_CFG_WHEEL_SIZE           = [ "OSTmrCfgWheelSize"         ]
OS_TMR_EN                       = [ "OSTmrEn"                   ]
OS_TMR_FREE_LIST                = [ "OSTmrFreeList"             ]
OS_TMR_FREE                     = [ "OSTmrFree"                 ]
OS_TMR_SEM                      = [ "OSTmrSem"                  ]
OS_TMR_SEM_SIGNAL               = [ "OSTmrSemSignal"            ]
OS_TMR_SIZE                     = [ "OSTmrSize"                 ]
OS_TMR_TBL                      = [ "OSTmrTbl"                  ]
OS_TMR_TBL_SIZE                 = [ "OSTmrTblSize"              ]
OS_TMR_TIME                     = [ "OSTmrTime"                 ]
OS_TMR_USED                     = [ "OSTmrUsed"                 ]
OS_TMR_WHEEL_SIZE               = [ "OSTmrWheelSize"            ]
OS_TMR_WHEEL_TBL_SIZE           = [ "OSTmrWheelTblSize"         ]

# uCOS-II structure names
OS_EVENT                        = "OS_EVENT"
OS_FLAG_GRP                     = "OS_FLAG_GRP"
OS_FLAG_NODE                    = "OS_FLAG_NODE"
OS_MEM                          = "OS_MEM"
OS_Q                            = "OS_Q"
OS_TCB                          = "OS_TCB"
OS_TMR                          = "OS_TMR"

# uCOS-II structure member name (if there are multiple possible names, add each one to the list)
# Note: the first name must match the column heading in messages.properties file

# Event structure members
OS_EVENT_NAME                   = [ "OSEventName" ]
OS_EVENT_TYPE                   = [ "OSEventType" ]
OS_EVENT_PTR                    = [ "OSEventPtr"  ]
OS_EVENT_CNT                    = [ "OSEventCnt"  ]
OS_EVENT_GRP                    = [ "OSEventGrp"  ]
OS_EVENT_TBL                    = [ "OSEventTbl"  ]

# Flag structure members
OS_FLAG_NAME                    = [ "OSFlagName"     ]
OS_FLAG_FLAGS                   = [ "OSFlagFlags"    ]
OS_FLAG_TYPE                    = [ "OSFlagType"     ]
OS_FLAG_WAIT_LIST               = [ "OSFlagWaitList" ]

# Flag node structure members
OS_FLAG_NODE_TCB                = [ "OSFlagNodeTCB"      ]
OS_FLAG_NODE_FLAGS              = [ "OSFlagNodeFlags"    ]
OS_FLAG_NODE_WAIT_TYPE          = [ "OSFlagNodeWaitType" ]
OS_FLAG_NODE_NEXT               = [ "OSFlagNodeNext"     ]
OS_FLAG_NODE_PREV               = [ "OSFlagNodePrev"     ]

# Memory partitions structure members
OS_MEM_NAME                     = [ "OSMemName"     ]
OS_MEM_ADDR                     = [ "OSMemAddr"     ]
OS_MEM_FREELIST                 = [ "OSMemFreeList" ]
OS_MEM_BLKSIZE                  = [ "OSMemBlkSize"  ]
OS_MEM_NBLKS                    = [ "OSMemNBlks"    ]
OS_MEM_NFREE                    = [ "OSMemNFree"    ]

# Queue structure members
OS_Q_PTR                        = [ "OSQPtr"     ]
OS_Q_START                      = [ "OSQStart"   ]
OS_Q_END                        = [ "OSQEnd"     ]
OS_Q_IN                         = [ "OSQIn"      ]
OS_Q_OUT                        = [ "OSQOut"     ]
OS_Q_SIZE                       = [ "OSQSize"    ]
OS_Q_ENTRIES                    = [ "OSQEntries" ]

# Task structure members
OS_TCB_BITX                    = [ "OSTCBBitX"          ]
OS_TCB_BITY                    = [ "OSTCBBitY"          ]
OS_TCB_CTXSWCTR                = [ "OSTCBCtxSwCtr"      ]
OS_TCB_CYCLESSTART             = [ "OSTCBCyclesStart"   ]
OS_TCB_CYCLESTOT               = [ "OSTCBCyclesTot"     ]
OS_TCB_DELREQ                  = [ "OSTCBDelReq"        ]
OS_TCB_DLY                     = [ "OSTCBDly"           ]
OS_TCB_EVENTMULTIPTR           = [ "OSTCBEventMultiPtr" ]
OS_TCB_EVENTPTR                = [ "OSTCBEventPtr"      ]
OS_TCB_EXTPTR                  = [ "OSTCBExtPtr"        ]
OS_TCB_FLAGNODE                = [ "OSTCBFlagNode"      ]
OS_TCB_FLAGSRDY                = [ "OSTCBFlagsRdy"      ]
OS_TCB_ID                      = [ "OSTCBId"            ]
OS_TCB_MSG                     = [ "OSTCBMsg"           ]
OS_TCB_NEXT                    = [ "OSTCBNext"          ]
OS_TCB_OPT                     = [ "OSTCBOpt"           ]
OS_TCB_PREV                    = [ "OSTCBPrev"          ]
OS_TCB_PRIO                    = [ "OSTCBPrio"          ]
OS_TCB_STAT                    = [ "OSTCBStat"          ]
OS_TCB_STATPEND                = [ "OSTCBStatPend"      ]
OS_TCB_STKBASE                 = [ "OSTCBStkBase"       ]
OS_TCB_STKBOTTOM               = [ "OSTCBStkBottom"     ]
OS_TCB_STKPTR                  = [ "OSTCBStkPtr"        ]
OS_TCB_STKSIZE                 = [ "OSTCBStkSize"       ]
OS_TCB_STKUSED                 = [ "OSTCBStkUsed"       ]
OS_TCB_TASKNAME                = [ "OSTCBTaskName"      ]
OS_TCB_TLS                     = [ "OSTCBTLSTbl"        ]
OS_TCB_X                       = [ "OSTCBX"             ]
OS_TCB_Y                       = [ "OSTCBY"             ]

# Timer structure members
OS_TMR_NAME                    = [ "OSTmrName"        ]
OS_TMR_CALLBACK                = [ "OSTmrCallback"    ]
OS_TMR_CALLBACKARG             = [ "OSTmrCallbackArg" ]
OS_TMR_NEXT                    = [ "OSTmrNext"        ]
OS_TMR_PREV                    = [ "OSTmrPrev"        ]
OS_TMR_MATCH                   = [ "OSTmrMatch"       ]
OS_TMR_DLY                     = [ "OSTmrDly"         ]
OS_TMR_PERIOD                  = [ "OSTmrPeriod"      ]
OS_TMR_OPT                     = [ "OSTmrOpt"         ]
OS_TMR_STATE                   = [ "OSTmrState"       ]
OS_TMR_TYPE                    = [ "OSTmrType"        ]

# Function names
OS_CPU_ARM_DREG_CNT_GET        = [ "OS_CPU_ARM_DRegCntGet" ]
OS_CPU_FP_REG_PUSH             = [ "OS_CPU_FP_Reg_Push"    ]

# Get global variable from a list of possible names
def globGetName( glob, debugSession ):
    name = ""   # Default return value
    # Step through all possible names for a given variable
    for g in glob:
        # Check if exists
        if debugSession.symbolExists( g ):
            name = g    # Yes, save
            break       # and stop looking
    return name     # Variable name
