<?xml version="1.0" encoding="UTF-8"?>
<container xmlns:cr="http://www.arm.com/core_reg" xmlns="http://www.arm.com/core_reg" xmlns:tcf="http://com.arm.targetconfigurationeditor" xmlns:xi="http://www.w3.org/2001/XInclude" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.arm.com/core_reg ../../../Schemas/core_register_definition.xsd">
  
  <cr:register_list name="System">
    <register_group name="ID">
    <gui_name language="en">ID</gui_name>
    <description language="en">ID</description>
  
    <register access="RO" name="CCSIDR" size="4">
      <gui_name language="en">Current Cache Size ID Register</gui_name>
      <description language="en">Provides information about the architecture of the currently selected cache.</description>
      <bitField conditional="false" name="Associativity">
        <gui_name language="en">Associativity</gui_name>
        <description language="en">(Associativity of cache) - 1, therefore a value of 0 indicates an associativity of 1. The associativity does not have to be a power of 2.</description>
        <definition>[23:3]</definition>
      </bitField>
      <bitField conditional="false" name="LineSize">
        <gui_name language="en">LineSize</gui_name>
        <description language="en">(Log2(Number of bytes in cache line)) - 4.</description>
        <definition>[2:0]</definition>
      </bitField>
    </register>
    <register access="RO" name="CCSIDR2" size="4">
      <gui_name language="en">Current Cache Size ID Register</gui_name>
      <description language="en">Provides information about the architecture of the currently selected cache.</description>
      <bitField conditional="false" name="NumSets">
        <gui_name language="en">NumSets</gui_name>
        <description language="en">(Number of sets in cache) - 1, therefore a value of 0 indicates 1 set in the cache. The number of sets does not have to be a power of 2.</description>
        <definition>[23:0]</definition>
      </bitField>
    </register>
    </register_group>
  </cr:register_list>
</container>
