<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="2.0"
                xmlns:c="http://www.arm.com/core_definition"
                xmlns:cr="http://www.arm.com/core_reg"
                xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                xmlns:xi="http://www.w3.org/2001/XInclude"
                xmlns:tcf="http://com.arm.targetconfigurationeditor"
                xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
                xmlns:internal="http://internal_functions"
               
                exclude-result-prefixes="c cr xi xsi tcf xsl internal"
                >
  <xsl:output method="xml" indent="yes" encoding="UTF-8"/>
  <xsl:preserve-space elements="*"/>
 
  <xsl:template match="@* | node()"><xsl:copy><xsl:apply-templates select="@* | node()"/></xsl:copy></xsl:template>

  <xsl:variable name="max-byte-width" >
    <xsl:for-each select="//cr:register/@size">
      <xsl:sort select="." data-type="number" order="descending"/>
      <xsl:if test="position() = 1">
        <num>
          <xsl:value-of select="."/>
        </num>
      </xsl:if>
    </xsl:for-each>
  </xsl:variable>
  
  <xsl:variable name="bitperbyte" select="8"/>
  
  <xsl:variable name="hexlookup" select="tokenize('0,1,2,3,4,5,6,7,8,9,A,B,C,D,E,F',',')"/>

  <xsl:function name="internal:strsplit">
    <xsl:param name="text"/>
    <el><xsl:value-of select="substring($text, 1, 1)"/></el>
    <xsl:if test="string-length($text) > 1">
      <xsl:copy-of select="internal:strsplit(substring($text, 2, string-length($text) - 1))"/>
    </xsl:if>    
  </xsl:function>

  <xsl:function name="internal:lookup_position">
    <xsl:param name="lut"/>
    <xsl:param name="val"/>
    <xsl:for-each select="$lut">
      <xsl:if test=".=$val">
        <el><xsl:value-of select="position()-1"/></el>
      </xsl:if>    
    </xsl:for-each>
  </xsl:function>

  <xsl:function name="internal:lo_lookup_value">
    <xsl:param name="lut"/>
    <xsl:param name="val"/>
    <xsl:for-each select="$val">
      <xsl:variable name="locval" select="."/>
      <xsl:for-each select="$lut">
        <xsl:if test="position()-1=$locval">
          
          <el><xsl:copy-of select="."/></el>
        </xsl:if>    
      </xsl:for-each>
    </xsl:for-each>    
  </xsl:function>
  
  <xsl:function name="internal:lo_lookup_position">
    <xsl:param name="lut"/>
    <xsl:param name="val"/>
    <xsl:for-each select="$val">
      <el><xsl:value-of select="internal:lookup_position($lut,.)"/></el>
    </xsl:for-each>
  </xsl:function>

  <xsl:function name="internal:lo_num2base">
    <xsl:param name="val"/>
    <xsl:param name="base"/>
    <el><xsl:value-of select="$val mod $base"/></el>
    <xsl:if test="$val gt $base">
      <xsl:copy-of select="internal:lo_num2base(floor($val div $base),$base)"/>
    </xsl:if>
  </xsl:function>

  <xsl:function name="internal:dec2hex">
    <xsl:param name="val"/>
    <xsl:variable name="lo_hex_mods" select="reverse(internal:lo_num2base($val,16))"/>
    <xsl:variable name="lo_hex" select="string-join(internal:lo_lookup_value($hexlookup,$lo_hex_mods),'')"/>    
    <xsl:copy-of select="string-join(('0x',$lo_hex),'')"/>
  </xsl:function>

  <xsl:function name="internal:addbase">
    <xsl:param name="val"/>
    <xsl:param name="base"/>
    <xsl:value-of select="    
                          if (count($val) eq 0) then
                          0
                          else if (count($val) eq 1) then
                          $val[1]
                          else
                          $val[1] + $base * internal:addbase(subsequence($val, 2),$base)
                          "/>    
  </xsl:function>    
  
  <xsl:function name="internal:hex2dec">
    <xsl:param name="hexorig"/>
    <xsl:variable name="hex" select="reverse(internal:strsplit(upper-case(substring($hexorig,3))))"/>
    <xsl:variable name="res" select="internal:addbase(internal:lo_lookup_position($hexlookup,$hex),16)"/>
    <xsl:value-of select="$res"/>
  </xsl:function>
  
  <xsl:function name="internal:peripheral_base_address">
    <xsl:param name="nodeset"/>
    <xsl:for-each select="$nodeset/@offset">
      <xsl:sort select="lower-case(.)" data-type="text" order="ascending"/>
      <xsl:if test="position() = 1">
        <xsl:value-of select="."/>
      </xsl:if>
    </xsl:for-each>
  </xsl:function>
  
  <xsl:function name="internal:addressbloc_for">
    <xsl:param name="nodeset"/>
    <xsl:param name="adbtype"/>
    <xsl:variable name="searchedba">
      <xsl:if test="$adbtype='registers'">
        <xsl:value-of select="internal:hex2dec(internal:peripheral_base_address($nodeset))"/>
      </xsl:if>
    </xsl:variable>
    <xsl:variable name="ba" select="internal:hex2dec(internal:peripheral_base_address($nodeset))" />
    <offset>
      <xsl:value-of select="internal:dec2hex($searchedba - $ba)"/>
    </offset>
    <size>
      <xsl:value-of select=" internal:dec2hex(8*number(sum($nodeset/@size)))"/>
    </size>
    <usage>  <xsl:value-of select="$adbtype"/></usage>
  </xsl:function>

  <xsl:function name="internal:sort" as="item()*">             
    <xsl:param name="seq" as="item()*"/>
    <xsl:for-each select="$seq">
      <xsl:sort select="."/>
      <xsl:copy-of select="."/>
    </xsl:for-each>

  </xsl:function>

  <xsl:function name="internal:sortint" as="item()*">             
    <xsl:param name="seq"/>
    <xsl:for-each select="$seq">
      <xsl:sort select="." data-type="number"/>
      <xsl:copy-of select="."/>
    </xsl:for-each>

  </xsl:function>

  
  <xsl:function name="internal:definition_for">
    <xsl:param name="node"/>
    <xsl:choose>
      <xsl:when test="contains($node,':')">
        <xsl:variable name="vals" select="internal:sortint(tokenize(substring($node, 2, string-length($node) - 2),':'))" />
        <bitOffset>
          <xsl:value-of select="$vals[1]"/>
        </bitOffset>
        <bitWidth> <xsl:value-of select="number($vals[2]) - number($vals[1])"/></bitWidth>
      </xsl:when>
      <xsl:otherwise>
        <bitOffset>
          <xsl:value-of select="substring($node, 2, string-length($node) - 2)"/>
        </bitOffset>
        <bitWidth>1</bitWidth>
      </xsl:otherwise>
    </xsl:choose>
  </xsl:function>
  
  <xsl:template match="/">
    <device schemaVersion="1.3" xmlns:xs="http://www.w3.org/2001/XMLSchema-instance" xs:noNamespaceSchemaLocation="CMSIS-SVD.xsd" >
      <vendor>ARM Ltd.</vendor>
      <vendorID>ARM</vendorID>
      <name><xsl:value-of select="c:core_definition/c:name"/></name>
      <description><xsl:value-of select="c:core_definition/c:name"/> core descriptions, generated from ARM develloper studio</description>
      <cpu>
        <name><xsl:value-of select="c:core_definition/c:name"/></name>
        <series><xsl:value-of select="c:core_definition/c:series"/></series>
        <revision>r0p0</revision>
        <endian>little</endian>
        <xsl:if test="boolean(//cr:peripheral[@name='MPU'])">
          <mpuPresent>true</mpuPresent>
        </xsl:if>
        <xsl:if test="boolean(//cr:register[@name='FPCCR']) or boolean(//c:peripheral[@name='FPU']) or boolean(//cr:register[@name='MVFR0'])" >
          <fpuPresent>true</fpuPresent>
        </xsl:if>
        <xsl:if test="boolean(//@name='FPDP')" >
          <!-- if MVFR0 is here the DP FPU is potentially here-->
          <fpuDP>true</fpuDP>
        </xsl:if>
        <xsl:if test="boolean(//@name='SIMDSP')" >
          <dspPresent>true</dspPresent>
        </xsl:if>
        <xsl:if test="boolean(//@name[contains(.,'ICACHE')]) or boolean(//c:cache_awareness/@class[contains(.,'ICache')]) ">
          <icachePresent>true</icachePresent>
        </xsl:if>
        <xsl:if test="boolean(//@name[contains(.,'DCACHE')]) or boolean(//c:cache_awareness/@class[contains(.,'DCache')]) ">
          <dcachePresent>true</dcachePresent>
        </xsl:if>
        <xsl:if test="boolean(//cr:register[@name='ITCMR'])">
          <itcmPresent>true</itcmPresent>
        </xsl:if>
        <xsl:if test="boolean(//cr:register[@name='DTCMR'])">
          <dtcmPresent>true</dtcmPresent>
        </xsl:if>
        <xsl:if test="boolean(//cr:register[@name='VTOR'])">
          <vtorPresent>true</vtorPresent>
        </xsl:if>
        <nvicPrioBits>8</nvicPrioBits>
        <vendorSystickConfig>true</vendorSystickConfig>
      </cpu>
      <addressUnitBits>8</addressUnitBits>
      <width>         
        <xsl:variable name="cpu-width" select="$max-byte-width * $bitperbyte" />
        <xsl:value-of select="$cpu-width" />
      </width>
      <peripherals>
        <xsl:for-each select="//cr:peripheral">
          <peripheral>
            <xsl:variable name="pbase" select="internal:peripheral_base_address(node())"/>
            <xsl:variable name="pname" select="./@name"/>
            <name>
              <xsl:value-of select="./@name" />
            </name>        
            <description>
              <xsl:value-of select="./cr:description" />
            </description>
            <xsl:if test="boolean(./cr:groupName)">
              <groupName>
                <xsl:value-of select="./cr:groupName" />
              </groupName>
            </xsl:if>
            <baseaddress>
              <xsl:value-of select="$pbase" />             
            </baseaddress>
            <addressBlock>
              <xsl:copy-of select="internal:addressbloc_for(node(),'registers')" />     
            </addressBlock>           
            <!-- TODO interrupts-->
            <registers>
              <xsl:for-each select="./cr:register">
                <register>
                  <xsl:variable name="rname" select="@name"/>
                  <name><xsl:value-of select="@name"/></name>                  
                  <addressOffset><xsl:value-of select="internal:dec2hex(internal:hex2dec(@offset)-internal:hex2dec($pbase))"/></addressOffset>
                  <!-- prp grp-->
                  <size><xsl:value-of select="internal:dec2hex(@size*$bitperbyte)"/></size>
                  <access>
                    <xsl:choose>
                      <xsl:when test="@access='RW'">
                        <xsl:value-of select="'read-write'"/>
                      </xsl:when>
                      <xsl:when test="@access='RO'">
                        <xsl:value-of select="'read-only'"/>
                      </xsl:when>
                      <xsl:when test="@access='WO'">
                        <xsl:value-of select="'write-only'"/>
                      </xsl:when>
                      <xsl:when test="@access='RMW'">
                        <xsl:value-of select="'read-write'"/>
                      </xsl:when>      
                    </xsl:choose>                   
                  </access>
                  <!-- TODO resetValue-->
                  <!-- TODO resetMask-->
                  <fields>
                    <xsl:for-each select="./cr:bitField">
                      
                      <field>
                        <name><xsl:value-of select="@name"/></name>
                        <description>
                          <xsl:choose>
                            <xsl:when test="./cr:description">
                              <xsl:value-of select="./cr:description"/>
                            </xsl:when>
                            <xsl:otherwise>
                              <xsl:value-of select="@name"/>
                            </xsl:otherwise>
                          </xsl:choose>
                        </description>

                        <xsl:copy-of select="internal:definition_for(./cr:definition)"/>
                        
                      </field>
                      
                    </xsl:for-each>
                  </fields>

                  <!--       <xsl:copy-of select="."/>
                  -->
                </register>
              </xsl:for-each>              
            </registers>                
              </peripheral>
            </xsl:for-each>            
          </peripherals>          
        </device> 
      </xsl:template >      
    </xsl:stylesheet>

