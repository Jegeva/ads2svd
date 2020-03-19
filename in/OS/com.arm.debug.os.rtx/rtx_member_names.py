# Copyright (C) 2018 Arm Limited (or its affiliates). All rights reserved.

#By default the tables should refer to symbol of RTX5 since RTX4 will not be updated anymore
#This table will map to RTX4 symbol names when debugging RTX4 images
MEMBER_NAME_BY_VERSION = {
    'osRtxConfig.flags'                     : 'os_stackinfo',
    'osRtxConfig.tick_freq'                 : 'os_clockrate',
    'osRtxConfig.robin_timeout'             : 'os_robin.tout',
    'osRtxInfo.thread.run.curr'             : 'os_tsk.run',
    'osRtxInfo.kernel.state'                : 'os_running',
    'osRtxInfo'                             : 'os_active_TCB',      #to check symbols are loaded
    'osRtxInfo.timer.list'                  : 'os_timer_head',
    'osRtxStackMagicWord'                   : 'MAGIC_WORD',

    'id'                                    : 'cb_type',
    'task_id'                               : 'task_id',            #only RTX4'
    'state'                                 : 'state',
    'thread_next'                           : 'p_lnk',
    'thread_prev'                           : 'p_rlnk',
    'delay_next'                            : 'p_dlnk',
    'delay_prev'                            : 'p_blnk',
    'delay'                                 : 'delta_time',
    'interval_time'                         : 'interval_time',
    'priority'                              : 'prio',
    'stack_frame'                           : 'stack_frame',
    'wait_flags'                            : 'waits',
    'thread_flags'                          : 'events',
    'stack_mem'                             : 'stack',
    'stack_size'                            : 'priv_stack',
    'sp'                                    : 'tsk_stack',
    'thread_addr'                           : 'ptask',
    'thread_list'                           : 'p_lnk',
    'owner_thread'                          : 'owner',
    'lock'                                  : 'level',
    'tokens'                                : 'tokens',
    'msg'                                   : 'msg',
    'msg_first'                             : 'first',
    'msg_last'                              : 'last',
    'msg_count'                             : 'count',
    'msg_size'                              : 'size',
    'size'                                  : 'size',
    'next'                                  : 'next'
}
