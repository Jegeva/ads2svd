# ###############################################################################
#
# Copyright (C) 2014,2017 Arm Limited (or its affiliates). All rights reserved.
#
# FreeRTOS - V7.6.0 / V8.0.0RC ARM Cortex M / A
#
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

# Import all!
from osapi import *

# General definitions
OS_NAME                                 = "freertos"

# defines
TSKKERNEL_VERSION_NUMBER                = "tskKERNEL_VERSION_NUMBER"
TSKIDLE_PRIORITY                        = "tskIDLE_PRIORITY"
TMRCOMMAND_EXECUTE_CALLBACK             = "tmrCOMMAND_EXECUTE_CALLBACK"
TMRCOMMAND_START                        = "tmrCOMMAND_START"
TMRCOMMAND_STOP                         = "tmrCOMMAND_STOP"
TMRCOMMAND_CHANGE_PERIOD                = "tmrCOMMAND_CHANGE_PERIOD"
TMRCOMMAND_DELETE                       = "tmrCOMMAND_DELETE"
PDFALSE                                 = "pdFALSE"
PDTRUE                                  = "pdTRUE"
PDPASS                                  = "pdPASS"
PDFAIL                                  = "pdFAIL"
ERRQUEUE_EMPTY                          = "errQUEUE_EMPTY"
ERRQUEUE_FULL                           = "errQUEUE_FULL"
ERRCOULD_NOT_ALLOCATE_REQUIRED_MEMORY   = "errCOULD_NOT_ALLOCATE_REQUIRED_MEMORY"
ERRQUEUE_BLOCKED                        = "errQUEUE_BLOCKED"
ERRQUEUE_YIELD                          = "errQUEUE_YIELD"
QUEUE_SEND_TO_BACK                      = "queueSEND_TO_BACK"
QUEUE_SEND_TO_FRONT                     = "queueSEND_TO_FRONT"
QUEUE_OVER_WRITE                        = "queueOVERWRITE"
QUEUE_QUEUE_TYPE_BASE                   = "queueQUEUE_TYPE_BASE"
QUEUE_QUEUE_TYPE_SET                    = "queueQUEUE_TYPE_SET"
QUEUE_QUEUE_TYPE_MUTEX                  = "queueQUEUE_TYPE_MUTEX"
QUEUE_QUEUE_TYPE_COUNTING_SEMAPHORE     = "queueQUEUE_TYPE_COUNTING_SEMAPHORE"
QUEUE_QUEUE_TYPE_BINARY_SEMAPHORE       = "queueQUEUE_TYPE_BINARY_SEMAPHORE"
QUEUE_QUEUE_TYPE_RECURSIVE_MUTEX        = "queueQUEUE_TYPE_RECURSIVE_MUTEX"
SEM_BINARY_SEMAPHORE_QUEUE_LENGTH       = "semBINARY_SEMAPHORE_QUEUE_LENGTH"
SEM_SEMAPHORE_QUEUE_ITEM_LENGTH         = "semSEMAPHORE_QUEUE_ITEM_LENGTH"
SEM_GIVE_BLOCK_TIME                     = "semGIVE_BLOCK_TIME"

# Global Variables
PX_CURRENT_TCB                          = "pxCurrentTCB"
UX_TASKS_DELETED                        = "uxTasksDeleted"
UX_CURRENT_NUMBER_OF_TASKS              = "uxCurrentNumberOfTasks"
X_TICK_COUNT                            = "xTickCount"
UX_TOP_READY_PRIORITY                   = "uxTopReadyPriority"
X_SCHEDULER_RUNNING                     = "xSchedulerRunning"
UX_SCHEDULER_SUSPENDED                  = "uxSchedulerSuspended"
UX_PENDED_TICKS                         = "uxPendedTicks"
X_YIELD_PENDING                         = "xYieldPending"
X_NUM_OF_OVERFLOWS                      = "xNumOfOverflows"
UX_TASK_NUMBER                          = "uxTaskNumber"
X_NEXT_TASK_UNBLOCK_TIME                = "xNextTaskUnblockTime"
UL_TASK_SWITCHED_IN_TIME                = "ulTaskSwitchedInTime"
UL_TOTAL_RUN_TIME                       = "ulTotalRunTime"
PX_DELAYED_TASKLIST                     = "pxDelayedTaskList"
PX_OVERFLOW_DELAYED_TASK_LIST           = "pxOverflowDelayedTaskList"
UL_CRITICAL_NESTING                     = "ulCriticalNesting"
UL_PORT_TASK_HAS_FPU_CONTEXT            = "ulPortTaskHasFPUContext"
UL_PORT_YIELD_REQUIRED                  = "ulPortYieldRequired"
UL_PORT_INTERRUPT_NESTING               = "ulPortInterruptNesting"
PX_READY_TASKS_LISTS                    = "pxReadyTasksLists"
X_DELAYED_TASK_LIST1                    = "xDelayedTaskList1"
X_DELAYED_TASK_LIST2                    = "xDelayedTaskList2"
X_PENDING_READY_LIST                    = "xPendingReadyList"
X_TASKS_WAITING_TERMINATION             = "xTasksWaitingTermination"
X_SUSPENDED_TASK_LIST                   = "xSuspendedTaskList"
X_QUEUE_REGISTRY                        = "xQueueRegistry"
PX_CURRENT_TIMER_LIST                   = '"timers.c"::pxCurrentTimerList'
PX_OVERFLOW_TIMER_LIST                  = '"timers.c"::pxOverflowTimerList'

# Structure names
TCB_T                                   = "tskTaskControlBlock"
XLIST                                   = "xLIST"
XLISTI                                  = "xLIST_ITEM"
XMINII                                  = "xMINI_LIST_ITEM"
QUEUE                                   = "QueueDefinition"
QUEUEI                                  = "QUEUE_REGISTRY_ITEM"
TIMER                                   = "tmrTimerControl"

# Structure member names

# Task structure members
TCB_PX_TOP_OF_STACK                     = "pxTopOfStack"
TCB_X_MPU_SETTINGS                      = "xMPUSettings"
TCB_X_GENERIC_LIST_ITEM                 = "xGenericListItem"
TCB_X_EVENT_LIST_ITEM                   = "xEventListItem"
TCB_UX_PRIORITY                         = "uxPriority"
TCB_PX_STACK                            = "pxStack"
TCB_PC_TASK_NAME                        = "pcTaskName"
TCB_PX_END_OF_STACK                     = "pxEndOfStack"
TCB_UX_CRITICAL_NESTING                 = "uxCriticalNesting"
TCB_UX_TCB_NUMBER                       = "uxTCBNumber"
TCB_UX_TASK_NUMBER                      = "uxTaskNumber"
TCB_UX_BASE_PRIORITY                    = "uxBasePriority"
TCB_PX_TASK_TAG                         = "pxTaskTag"
TCB_UL_RUN_TIME_COUNTER                 = "ulRunTimeCounter"
TCB_X_NEWLIB_REENT                      = "xNewLib_reent"

# xList structure members
XLIST_UX_NUMBER_OF_ITEMS                = "uxNumberOfItems"
XLIST_PX_INDEX                          = "pxIndex"
XLIST_X_LIST_END                        = "xListEnd"

# xList item structure members
XLISTI_X_ITEM_VALUE                     = "xItemValue"
XLISTI_PX_NEXT                          = "pxNext"
XLISTI_PX_PREVIOUS                      = "pxPrevious"
XLISTI_PV_OWNER                         = "pvOwner"
XLISTI_PV_CONTAINER                     = "pvContainer"

# xMINI_LIST_ITEM structure members
XMINII_X_ITEM_VALUE                     = "xItemValue"
XMINII_PX_NEXT                          = "pxNext"
XMINII_PX_PREVIOUS                      = "pxPrevious"

# Queue structure members
QUEUE_PC_HEAD                           = "pcHead"
QUEUE_PC_TAIL                           = "pcTail"
QUEUE_PC_WRITE_TO                       = "pcWriteTo"
QUEUE_PC_READ_FROM                      = "pcReadFrom"
QUEUE_UX_RECURSIVE_CALL_COUNT           = "uxRecursiveCallCount"
QUEUE_X_TASKS_WAITING_TO_SEND           = "xTasksWaitingToSend"
QUEUE_X_TASKS_WAITING_TO_RECEIVE        = "xTasksWaitingToReceive"
QUEUE_UX_MESSAGES_WAITING               = "uxMessagesWaiting"
QUEUE_UX_LENGTH                         = "uxLength"
QUEUE_UX_ITEM_SIZE                      = "uxItemSize"
QUEUE_X_RX_LOCK                         = "xRxLock"
QUEUE_X_TX_LOCK                         = "xTxLock"
QUEUE_UX_QUEUE_NUMBER                   = "uxQueueNumber"
QUEUE_UC_QUEUE_TYPE                     = "ucQueueType"
QUEUE_PX_QUEUE_SET_CONTAINER            = "pxQueueSetContainer"

# Queue Item structure members
QUEUE_I_PC_QUEUE_NAME                   = "pcQueueName"
QUEUE_I_X_HANDLE                        = "xHandle"

# Queue type codes
QUEUE_TYPE_BASE                         = 0
QUEUE_TYPE_SET                          = 0
QUEUE_TYPE_MUTEX                        = 1
QUEUE_TYPE_COUNTING_SEMAPHORE           = 2
QUEUE_TYPE_BINARY_SEMAPHORE             = 3
QUEUE_TYPE_RECURSIVE_MUTEX              = 4

# Timer structure
TIMER_PC_TIMER_NAME                     = "pcTimerName"
TIMER_X_TIMER_LIST_ITEM                 = "xTimerListItem"
TIMER_XTIMERPERIODINTICKS               = "xTimerPeriodInTicks"
TIMER_UX_AUTO_RELOAD                    = "uxAutoReload"
TIMER_PV_TIMER_ID                       = "pvTimerID"
TIMER_PX_CALLBACK_FUNCTION              = "pxCallbackFunction"

# General definitions
YES                                     = 1
NO                                      = 0

# Function names
# ....

# Register map names
REG_MAP_V7AVFP                          = "v7AVFP"
REG_MAP_V7ABASIC                        = "v7ABasic"
REG_MAP_V7MVFP                          = "v7MVFP"
REG_MAP_V7MEXT                          = "v7MExt"
REG_MAP_V7MBASIC                        = "v7MBasic"

# Global structure names

# Error codes/text

# Minimum/maximum system error numbers

# Create global reference
def globCreateRef( refs ):
    return '.'.join( refs )
