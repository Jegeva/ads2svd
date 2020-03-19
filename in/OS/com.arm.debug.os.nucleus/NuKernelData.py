################################################################################
#
# Copyright (C) 2014,2017 Arm Limited (or its affiliates). All rights reserved.
#
#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

from osapi import *
from utils import *

class NuKernelData( Table ):

    def __init__( self ):

        cid = "ker"

        fields = [ createField( cid, "item", TEXT ), createField( cid, "value", TEXT ), createField( cid, "desc", TEXT ) ]

        Table.__init__( self, cid, fields )

    def addRecord( self, expr, desc, format, records, debugSession ):

        value = ""

        if debugSession.symbolExists( expr ):
            if format == "number":
                value = str( debugSession.evaluateExpression( expr ).readAsNumber( ) )
            if format == "address":
                value = str( debugSession.evaluateExpression( expr ).readAsAddress( ) )

        if len( value ):
            records.append( self.createRecord( [ createTextCell( expr ), createTextCell( value ), createTextCell( desc ) ] ) )

    def getRecords( self, debugSession ):

        records = [ ]

        self.addRecord( "DMD_Total_Pools", "Number of dynamic memory pools created", "number", records, debugSession )
        self.addRecord( "ERD_Assert_Count", "Number of detected failed assertions", "number", records, debugSession )
        self.addRecord( "ERD_Error_Code", "The system error code detected by the system", "number", records, debugSession )
        self.addRecord( "ESAL_GE_ISR_Executing", "Flag indicating an ISR is in progress", "number", records, debugSession )
        self.addRecord( "ESAL_GE_MEM_ROM_Support_Enabled", "Flag indicating ROM support is enabled", "number", records, debugSession )
        self.addRecord( "ESAL_GE_STK_Exception_SP", "Exception stack pointer address", "address", records, debugSession )
        self.addRecord( "ESAL_GE_STK_System_SP", "System stack pointer address", "address", records, debugSession )
        self.addRecord( "ESAL_GE_STK_Unsol_Switch_Req", "Flag indicating un-solicited task swap has occured", "number", records, debugSession )
        self.addRecord( "ESAL_PR_ISR_Spurious_Count", "Process ISR spurious count", "number", records, debugSession )
        self.addRecord( "EVD_Total_Event_Groups", "Number of event groups created", "number", records, debugSession )
        self.addRecord( "MBD_Total_Mailboxes", "Number of mailboxes created", "number", records, debugSession )
        self.addRecord( "PID_Total_Pipes", "Number of pipes created", "number", records, debugSession )
        self.addRecord( "PMD_Total_Pools", "Number of partition memory pools created", "number", records, debugSession )
        self.addRecord( "QUD_Total_Queues", "Number of queues created", "number", records, debugSession )
        self.addRecord( "RLD_Major_Version", "Nucleus major revision number", "number", records, debugSession )
        self.addRecord( "RLD_Minor_Version", "Nucleus minor revision number", "number", records, debugSession )
        self.addRecord( "SMD_Total_Semaphores", "Number of semaphores created", "number", records, debugSession )
        self.addRecord( "TCD_Highest_Priority", "Highest priority task", "number", records, debugSession )
        self.addRecord( "TCD_Highest_Priority_HISR", "Highest priority HISR", "number", records, debugSession )
        self.addRecord( "TCD_Interrupt_Level", "Current interrupt level", "number", records, debugSession )
        self.addRecord( "TCD_Priority_Groups", "Number of priority groups", "number", records, debugSession )
        self.addRecord( "TCD_Total_App_Tasks", "Number of application tasks", "number", records, debugSession )
        self.addRecord( "TCD_Total_HISRs", "Number of HISRs", "number", records, debugSession )
        self.addRecord( "TCD_Total_Tasks", "Number of tasks", "number", records, debugSession )
        self.addRecord( "TCD_Unhandled_Exception", "Unhandled exception number", "number", records, debugSession )
        self.addRecord( "TCD_Unhandled_Exception_SP", "Unhandled exception stack pointer", "address", records, debugSession )
        self.addRecord( "TCD_Unhandled_Interrupt", "Unhandled interrupt number", "number", records, debugSession )
        self.addRecord( "TMD_Last_Time_Stamp", "The last time stamp value returned to the application", "number", records, debugSession )
        self.addRecord( "TMD_System_Clock", "Number of clock ticks since system started", "number", records, debugSession )
        self.addRecord( "TMD_System_Clock_Offset", "This contains the 64-bit offset clock value", "number", records, debugSession )
        self.addRecord( "TMD_System_Clock_Upper", "System clock overflow count", "number", records, debugSession )

        return records
