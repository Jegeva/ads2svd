# Copyright (C) 2013-2014,2017 Arm Limited (or its affiliates). All rights reserved.

from osapi import *

TASK_STATE_NAMES = \
[
    "RDY",                              # 0
    "DLY",                              # 1
    "PEND",                             # 2
    "PEND_TIMEOUT",                     # 3
    "SUSPENDED",                        # 4
    "DLY_SUSPENDED",                    # 5
    "PEND_SUSPENDED",                   # 6
    "PEND_SUSPENDED"                    # 7
]

PENDING_STATE_NAMES = \
[
    "NOTHING",                          # 0
    "FLAG",                             # 1
    "TASK_Q",                           # 2
    "MULTI",                            # 3
    "MUTEX",                            # 4
    "Q",                                # 5
    "SEM",                              # 6
    "T-SEM"                             # 7
]

PENDING_STATUS_NAMES = \
[
    "OK",
    "ABORT",
    "DEL",
    "TIMEOUT"
]

TASK_OPTIONS_NAMES = \
[
    "NONE",
    "STK_CHK",
    "STK_CLR",
    "SAVE_FP",
    "NO_TLS"
]

# use may add the last three options
TASK_FLAG_OPTIONS = \
[
    "FLAG_CLR_ALL",                         # 0
    "FLAG_CLR_ANY",                         # 1
    "FLAG_CLR_AND",                         # 2
    "FLAG_CLR_OR",                          # 3
    "FLAG_SET_ALL",                         # 4
    "FLAG_SET_ANY",                         # 5
    "FLAG_SET_AND",                         # 6
    "FLAG_SET_OR",                          # 7
    "FLAG_CONSUME",                         # 8
    "BLOCKING",                             # 9
    "NON_BLOCKING"                          # 10
]

def getBitOptNames( bitOptNames, stateVal ):
    opts = bitOptNames[ 0 ]
    i = 1
    j = 0
    m = 1
    #print "stateVal=",stateVal
    for opt in bitOptNames:
        if stateVal & m:
            if j == 0:
                opts = ""
            elif j > 0:
                opts = opts + "+"
            #print i
            opts = opts + bitOptNames[ i ]
            j = j + 1
        m = m * 2
        i = i + 1
    return opts

def getStateName(stateNames, stateVal):
    if stateVal < 0 or stateVal > (len(stateNames) -1):
        return str(stateVal)
    else:
        return stateNames[int(stateVal)]

def getOptionalValues(optionName, members, name, exprType, debugSession):
    val = "N/A"
    optionExpr = debugSession.evaluateExpression(optionName)
    optionSetting = optionExpr.readAsNumber()
    if optionSetting == 1:
        # process values
        if exprType == "address":
            val = members[name].readAsAddress().toString()
        elif exprType == "number":
            val = str(members[name].readAsNumber())
        elif exprType == "usage":
            # This field is computed by OS_StatTask() if OS_CFG_TASK_PROFILE_EN is set to 1 in
            # os_cfg.h. .CPUUsage contains the CPU usage of a task in percent (0 to 100%). As of
            # version V3.03.00, .CPUUsage is multiplied by 100. In other words, 10000 represents
            # 100.00%.
            cpuUsage = members[name].readAsNumber()
            if debugSession.evaluateExpression("OSDbg_VersionNbr").readAsNumber()>=30300:
            # need to v3.0.3 calculate CPU usage differently
                cpuUsage = cpuUsage/100
            val = str(cpuUsage) + "%"
        elif exprType == "enum":
            valNum = members[name].readAsNumber()
            val = getBitOptNames(TASK_FLAG_OPTIONS, valNum)
        else:
            pass
    return val


def getMessageValues(expr, exprType, debugSession):
    val = "N/A"
    optionQ = debugSession.evaluateExpression("OSDbg_QEn")
    optionTaskQ = debugSession.evaluateExpression("OSDbg_TaskQEn")
    if optionQ or optionTaskQ:
        if exprType == "address":
            val = expr.readAsAddress().toString()
        elif exprType == "number":
            val = str(expr.readAsNumber())
        else:
            pass
    return val

# safeguard pending values by first check if it is available
def getPendingValues(pendValue, members, debugSession):
    pendVal = "N/A"
    if debugSession.symbolExists(pendValue):
        pendSize = debugger.evaluateExpression("OSDbg_PendListSize").readAsNumber()
        pendTable = debugger.evaluateExpression("OSTaskDbgListPtr->PendDataTblEntries").readAsNumber()
        if (pendSize < pendTable):
            pend = debugSession.evaluateExpression(members[pendValue])
            pendVal = pend.readAsAddress().toString()
    return pendVal

# Base class for task control block structures
class TCBBasedTable(Table):

    def __init__(self, id, fields, functions, tcbTypeName, tcbType):
        Table.__init__(self, id, fields)
        self.functions = functions
        self.tcbTypeName = tcbTypeName
        self.tcbType = tcbType

    def getRecords(self, debugSession):
        activeTCB = debugSession.evaluateExpression("OSRdyList")
        elements = activeTCB.getArrayElements()
        records = []

        for element in elements:
            entry = element.getStructureMembers()
            exist = entry["NbrEntries"].readAsNumber()
            if exist > 0:
                #print "found entry"
                #print entry["NbrEntries"].readAsNumber()
                record = self.readTask(entry["HeadPtr"].dereferencePointer(), debugSession)
                records.append(record)

        return records

def traverse_list(head, next, func=lambda id: id):
    ''' returns a list made from applying 'func' (defaulting to the identity function
    to every element in a linked list pointed to by expression 'head'
    with a member pointing to the next element called 'next'

    Note: Recreating objects cause loops so loop detection has been added
    '''

    result = []
    sample = False
    converge_address = 0
    while head.readAsNumber() != 0:
        result.append(func(head))
        head = head.dereferencePointer().getStructureMembers()[next]

        if sample:
            sample = False
            if head.readAsNumber() == converge_address:
                break
        else:
            sample = True
            converge_address = head.readAsNumber()

    return result

def obj_name(obj_pointer):
    ''' the name of a uCOSIII object pointed to by obj_pointer '''
    structure = obj_pointer.dereferencePointer().getStructureMembers()
    stringptr = structure['NamePtr']
    if stringptr.readAsNumber() != 0:
        return stringptr.readAsNullTerminatedString()
    return "<NULL>"

def pend_name(pend_data):
    ''' the name of a uCOSIII task pointed to by a pend_data object &'pend_data '''

    return obj_name(pend_data.dereferencePointer().getStructureMembers()['TCBPtr'])

# Get member name from list of members
def getMemberName( member, members ):
    name = ""
    for m in member:
        if m in members:
            name = m
            break
    return name
