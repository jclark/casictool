

## 1. NMEA Protocol

### 1.1 NMEA Protocol Characteristics

The CASIC receiver is compatible with the international standard NMEA 0183 protocol. It supports NMEA 0183 version 4.1 by default and is compatible with V2.3 and V3.X versions. Through command configuration, it can support the NMEA 0183 V4.0 standard as well as standards prior to V2.3.

Data is transmitted in a serial asynchronous manner. The 1st bit is the start bit, followed by data bits. Data bits follow the rule of Least Significant Bit (LSB) first.

**Data Transmission Mode** 

| Start Bit | D0 | D1 | D2 | D3 | D4 | D5 | D6 | D7 | Stop Bit |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |


**Parameters Used for Data Transmission** 

| Parameter | Description |
| --- | --- |
| **Baud Rate (bps)** | Supports 4800, 9600, 19200, 38400, 57600, 115200 |
| **Data Bits** | 8 bits |
| **Stop Bits** | 1 bit |
| **Parity Bit** | None |

### 1.2 NMEA Protocol Framework

NMEA messages are sent by the GNSS receiver and support the NMEA 0183 protocol.

**Data Format Protocol Framework** 

| NMEA Protocol Framework |  |  |  |  |  | Checksum Calculation Range |  |
| --- | --- | --- | --- | --- | --- | --- | --- |
| **$** | **** | **{,}** | ***** | **** |  |  |  |
| **Start Character** | **Address Field** | **Data Field** | **Checksum Field** | **End Sequence** |  |  |  |
| Every sentence starts with `$` . | Divided into two parts: Talker Identifier and Sentence Type. | Starts with a comma. The length of the following values is variable, though some are fixed length. | The result of an XOR operation on bytes between  `$`and`\*`(excluding these two characters), represented as a hexadecimal number. | Every sentence ends with`\<CR\>\<LF\>\`. |  | Values represented |  |

Detailed NMEA protocol standards can be referenced at [http://www.nmea.org/](http://www.nmea.org/).

Based on the NMEA protocol framework, this receiver specification adds custom sentences used to control the receiver's working mode and query receiver product information. The identifier for custom sentences is "P".

### 1.3 NMEA Identifiers and Field Types

#### 1.3.1 Talker Identifiers

NMEA sentences distinguish different GNSS modes through Talker Identifiers defined as follows:

| Talker | Identifier |
| --- | --- |
| **BeiDou Navigation Satellite System (BDS)** | BD |
| **Global Positioning System (GPS, SBAS, QZSS)** | GP |
| **Global Navigation Satellite System (GLONASS)** | GL |
| **Global Navigation Satellite System (GNSS)** | GN |
| **Custom Information** | P |

1.3.2 Satellite Number Identifiers 

| Satellite System | Satellite ID in NMEA | Satellite PRN No. | Correspondence (ID to PRN) |
| --- | --- | --- | --- |
| **GPS** | 1-32 | 1-32 | 0 + PRN |
| **SBAS** | 33-51 | 120-138 | 87 + PRN |
| **GLONASS** | 65-88 | 1-24 | 64 + PRN |
| **BDS** | 1-37 | 1-37 | 0 + PRN |
| **QZSS** | 33-37 | 193-197 | PRN - 160 |

#### 1.3.3 System Identifiers

The CASIC receiver supports multiple NMEA data protocol formats. Differences between protocols are reflected in the system identifiers, and newer protocol versions add some fields.

| Sentence | NMEA 4.0 and below | NMEA 4.1 |
| --- | --- | --- |
| **GGA** | [1] Identifier | [1] Identifier |
| **ZDA** | [1] Identifier | [1] Identifier |
| **GLL** | [1] Identifier | [1] Identifier |
| **RMC** | [1] Identifier | [1] Identifier |
| **VTG** | [1] Identifier | [1] Identifier |
| **GSA** | [2] Identifier | [1] Identifier, adds extra fields to distinguish different systems |
| **GSV** | [2] Identifier | [2] Identifier |

* 
**[1] Identifier:** If only BD, GPS, GLONASS, or Galileo satellites are used for position solution, the transmitted identifiers are BD, GP, GL, GA, etc. If satellites from multiple systems are used to obtain the position solution, the transmitted identifier is GN.


* 
**[2] Identifier:** GP (GPS satellites), BD (BDS satellites), GL (GLONASS satellites).



Regarding Section 1.1, the CASIC receiver supports three versions of the NMEA 0183 protocol standard. The differences are listed below.

**Differences between NMEA 2.2 and 2.3/4.0:**

1. The Positioning Mode (Mode) item in GLL, RMC, and VTG sentences is not output.


2. In the GGA sentence, for Positioning Quality (FS), both Dead Reckoning and Normal Positioning use 1 (in 2.3, Dead Reckoning is set to 6).



**NMEA 4.1 protocol adds fields based on 4.0:**

1. Adds `systemId` item in the GSA sentence.


2. Adds `signalId` item in the GSV sentence.


3. Adds `navStatus` item in the RMC sentence.



Specific content is detailed in the subsequent NMEA sentence introduction in Section 1.5.

1.3.4 Field Types 

| Field Type | Symbol | Definition |
| --- | --- | --- |
| **Special Format Fields** |  |  |
| **Status** | `A` | Single character field: A=Yes, data valid, alarm flag cleared; V=No, data invalid, alarm flag set. |
| **Latitude** | `ddmm.mmmm` | Fixed/Variable length field. `dd` indicates fixed length of 2 for degrees; `mm` before the decimal point indicates fixed length of 2 for minutes; `mmmm` after the decimal indicates variable length decimal minutes. |
| **Longitude** | `dddmm.mmmm` | Fixed/Variable length field. `ddd` indicates fixed length of 3 for degrees; `mm` before the decimal point indicates fixed length of 2 for minutes; `mmmm` after the decimal indicates variable length decimal minutes. |
| **Time** | `hhmmss.sss` | Fixed length field. `hh` indicates fixed length of 2 for hours; `mm` indicates fixed length of 2 for minutes; `ss` before the decimal indicates fixed length of 2 for seconds; `sss` after the decimal indicates fixed length of 3 for decimal seconds. |
| **Defined Fields** |  | Some fields are defined for predefined constants. |
| **Numeric Fields** |  |  |
| **Variable Number** | `x.x` | Variable length or floating-point number field. |
| **Fixed Hex Field** | `hh` | Fixed length hexadecimal number, MSB on the left. |
| **Variable Hex Field** | `h-h` | Variable length hexadecimal number, MSB on the left. |
| **Information Fields** |  |  |
| **Fixed Alpha Field** | `aa` | Fixed length uppercase or lowercase alphabetic character field. |
| **Fixed Numeric Field** | `xx` | Fixed length numeric character field. |
| **Variable Text** | `c-c` | Variable length valid character field. |

1.4 NMEA Message Overview 

| Page | Message Name | Class/ID | Description |
| --- | --- | --- | --- |
| **NMEA Standard Messages** |  |  | **Standard Messages** |
|  | **GGA** | 0x4E 0x00 | Receiver positioning data |
|  | **GLL** | 0x4E 0x01 | Geographic position - Latitude/Longitude |
|  | **GSA** | 0x4E 0x02 | Dilution of Precision (DOP) and active satellites |
|  | **GSV** | 0x4E 0x03 | Visible satellites |
|  | **RMC** | 0x4E 0x04 | Recommended minimum specific GNSS data |
|  | **VTG** | 0x4E 0x05 | Course over ground and ground speed |
|  | **GST** | 0x4E 0x07 | GNSS Pseudorange Error Statistics |
|  | **ZDA** | 0x4E 0x08 | Time and Date |
|  | **ANT** | 0x4E 0x11 | Antenna status |
|  | **LPS** | 0x4E 0x12 | Satellite system leap second correction information |
|  | **DHV** | 0x4E 0x13 | Receiver velocity information |
|  | **UTC** | 0x4E 0x16 | Receiver status, simplified leap second correction information |
| **NMEA Custom Messages** |  |  | **Custom Messages** |
|  | **CAS00** |  | Save configuration information |
|  | **CAS01** |  | Communication protocol and serial port configuration info |
|  | **CAS02** |  | Set positioning update rate |
|  | **CAS03** |  | Enable or disable output messages and their frequency |
|  | **CAS04** |  | Set initialization system and channel numbers |
|  | **CAS05** |  | Set NMEA sentence talker identifier |
|  | **CAS06** |  | Query module hardware/software information |
|  | **CAS10** |  | Startup mode and aiding information configuration |
|  | **CAS12** |  | Standby mode control |
|  | **CAS20** |  | Online upgrade instruction |

### 1.5 NMEA Standard Messages

1.5.1 GGA 

| Information | GGA |
| --- | --- |
| **Description** | Receiver time, position, and positioning related data |
| **Type** | Output |
| **Format** | `$--GGA, UTCtime, lat, uLat, lon, uLon, FS, numSv, HDOP, msl, uMsl, sep, uSep, diffAge, diffSta*CS<CR><LF>` |
| **Example** | `$GPGGA,235316.000,2959.9925,S,12000.0090,E,1,06,1.21,62.77,M,0.00,M,,*7B` |

**Parameter Description**

| Field | Name | Format | Parameter Description |
| --- | --- | --- | --- |
| 1 | `$--GGA` | String | Message ID, GGA sentence header, `--` is system ID |
| 2 | `UTCtime` | `hhmmss.sss` | UTC time of current position |
| 3 | `lat` | `ddmm.mmmm` | Latitude, first 2 chars are degrees, following are minutes |
| 4 | `uLat` | Character | Latitude direction: N-North, S-South |
| 5 | `lon` | `dddmm.mmmm` | Longitude, first 3 chars are degrees, following are minutes |
| 6 | `uLon` | Character | Longitude direction: E-East, W-West |
| 7 | `FS` | Numeric | Indicates current positioning quality (Remark [1]), this field should not be empty |
| 8 | `numSv` | Numeric | Number of satellites used for positioning, 00~24 |
| 9 | `HDOP` | Numeric | Horizontal Dilution of Precision (HDOP) |
| 10 | `msl` | Numeric | Altitude, height of antenna relative to mean sea level |
| 11 | `uMsl` | Character | Altitude unit, meters, fixed character M |
| 12 | `sep` | Numeric | Distance between reference ellipsoid and mean sea level, "-" indicates mean sea level is below ellipsoid |
| 13 | `uSep` | Character | Height unit, meters, fixed character M |
| 14 | `diffAge` | Numeric | Age of differential correction data, empty if DGPS is not used |
| 15 | `diffSta` | Numeric | ID of differential reference station |
| 16 | `CS` | Hex Numeric | Checksum, XOR result of all characters between `$` and `*` |
| 17 | `<CR><LF>` | Character | Carriage Return and Line Feed |

**Remark [1] Positioning Quality Flags**

| Positioning Quality Flag | Description |
| --- | --- |
| **0** | Positioning unavailable or invalid |
| **1** | SPS positioning mode, positioning valid |
| **6** | Estimated mode (Dead Reckoning), valid only for NMEA 2.3 and above |

1.5.2 GLL 

| Information | GLL |
| --- | --- |
| **Description** | Latitude, longitude, positioning time, and positioning status information. |
| **Type** | Output |
| **Format** | `$--GLL, lat, uLat, lon, uLon, UTCtime, valid, mode*CS<CR><LF>` |
| **Example** | `$GPGLL,2959.9925,S,12000.0090,E,235316.000,A,A*4E` |

**Parameter Description**

| Field | Name | Format | Parameter Description |
| --- | --- | --- | --- |
| 1 | `$--GLL` | String | Message ID, GLL sentence header, `--` is system ID |
| 2 | `lat` | `ddmm.mmmm` | Latitude, first 2 chars are degrees, following are minutes |
| 3 | `uLat` | Character | Latitude direction: N-North, S-South |
| 4 | `lon` | `dddmm.mmmm` | Longitude, first 3 chars are degrees, following are minutes |
| 5 | `uLon` | Character | Longitude direction: E-East, W-West |
| 6 | `UTCtime` | `hhmmss.sss` | UTC time of current position |
| 7 | `valid` | Character | Data validity (Remark [1]) |
| 8 | `mode` | Character | Positioning mode (Remark [2]), valid only for NMEA 2.3 and above |
| 9 | `CS` | Hex Numeric | Checksum |
| 10 | `<CR><LF>` | Character | Carriage Return and Line Feed |

**Remark [1] Data Validity Flags**

| Positioning Quality Flag | Description |
| --- | --- |
| **A** | Data Valid |
| **V** | Data Invalid |

**Remark [2] Positioning Mode Flags**

| Positioning Mode Flag | Description |
| --- | --- |
| **A** | Autonomous mode |
| **E** | Estimated mode (Dead Reckoning) |
| **N** | Data invalid |
| **D** | Differential mode |
| **M** | Not positioned, but external input or historical preserved position exists |

1.5.3 GSA 

| Information | GSA |
| --- | --- |
| **Description** | Satellite IDs used for positioning and DOP information. Output GSA regardless of positioning or available satellites. When in multi-system joint operation, each system outputs one GSA sentence containing PDOP, HDOP, and VDOP based on the combined satellite system. |
| **Type** | Output |
| **Format** | `$--GSA, smode, FS{,SVID}, PDOP, HDOP, VDOP, systemId*CS<CR><LF>` |
| **Example** | `$GPGSA,A,3,05,21,31,12,18,29,,,,,,,2.56,1.21,2.25*01` |

**Parameter Description**

| Field | Name | Format | Parameter Description |
| --- | --- | --- | --- |
| 1 | `$--GSA` | String | Message ID, GSA sentence header, `--` is system ID |
| 2 | `smode` | Character | Mode switch method indicator (Remark [1]) |
| 3 | `FS` | Numeric | Positioning status flag (Remark [2]) |
| 4 | `{,SVID}` | Numeric | IDs of satellites used for positioning. Displays 12 available satellites. If >12, only first 12 are output. If <12, empty fields are padded. |
| 5 | `PDOP` | Numeric | Position Dilution of Precision (PDOP) |
| 6 | `HDOP` | Numeric | Horizontal Dilution of Precision (HDOP) |
| 7 | `VDOP` | Numeric | Vertical Dilution of Precision (VDOP) |
| 8 | `systemId` | Numeric | GNSS System ID defined by NMEA (Remark [3]). Valid only for NMEA 4.1 and above. |
| 9 | `CS` | Hex Numeric | Checksum |
| 10 | `<CR><LF>` | Character | Carriage Return and Line Feed |

**Remark [1] Mode Switch Method Indicator**

| Mode Indicator | Description |
| --- | --- |
| **M** | Manual switch. Forced to 2D or 3D mode. |
| **A** | Automatic switch. Receiver automatically switches 2D/3D mode. |

**Remark [2] Positioning Status Flag**

| Positioning Status | Description |
| --- | --- |
| **1** | Positioning invalid |
| **2** | 2D Positioning |
| **3** | 3D Positioning |

**Remark [3] GNSS System ID**

| System ID | Description |
| --- | --- |
| **1** | GPS System |
| **2** | GLONASS System |
| **4** | BDS System |

1.5.4 GSV 

| Information | GSV |
| --- | --- |
| **Description** | Visible satellite IDs, elevation, azimuth, and C/N0 information. Variable number of {Satellite ID, Elev, Az, C/N0} groups per sentence (0 to 4 groups). |
| **Type** | Output |
| **Format** | `$--GSV, numMsg, msgNo, numSv{, SVID, ele, az, cn0}, signalId*CS<CR><LF>` |
| **Example** | `$GPGSV,3,1,10,25,68,053,47,21,59,306,49,29,56,161,49,31,36,265,49*79` |

**Parameter Description**

| Field | Name | Format | Parameter Description |
| --- | --- | --- | --- |
| 1 | `$--GSV` | String | Message ID, GSV sentence header, `--` is system ID |
| 2 | `numMsg` | Character | Total number of sentences. Each GSV outputs max 4 sats. If >4 sats, multiple sentences are needed. |
| 3 | `msgNo` | Numeric | Current sentence number. |
| 4 | `numSv` | Numeric | Total number of visible satellites. |
| 5 | `{,SVID, ele, az, cn0}` | Numeric | Sequentially: Satellite ID; Elevation (0-90 deg); Azimuth (0-359 deg); C/N0 (0-99 dB-Hz, empty if not tracked). |
| 6 | `signalId` | Numeric | GNSS Signal ID defined by NMEA (0 represents all signals). Valid only for NMEA 4.1 and above. |
| 7 | `CS` | Hex Numeric | Checksum |
| 8 | `<CR><LF>` | Character | Carriage Return and Line Feed |

1.5.5 RMC 

| Information | RMC |
| --- | --- |
| **Description** | Recommended Minimum Specific GNSS Data |
| **Type** | Output |
| **Format** | `$--RMC, UTCtime, status, lat, uLat, lon, uLon, spd, cog, date, mv, mvE, mode, navStatus*CS<CR><LF>` |
| **Example** | `$GPRMC,235316.000,A,2959.9925,S,12000.0090,E,0.009,75.020,020711,,,A*45` |

**Parameter Description**

| Field | Name | Format | Parameter Description |
| --- | --- | --- | --- |
| 1 | `$--RMC` | String | Message ID, RMC sentence header, `--` is system ID |
| 2 | `UTCtime` | `hhmmss.sss` | UTC time of current position |
| 3 | `status` | Character | Position valid flag. V=Receiver Warning, Data Invalid; A=Data Valid |
| 4 | `lat` | `ddmm.mmmm` | Latitude |
| 5 | `uLat` | Character | Latitude direction: N-North, S-South |
| 6 | `lon` | `dddmm.mmmm` | Longitude |
| 7 | `uLon` | Character | Longitude direction: E-East, W-West |
| 8 | `spd` | Numeric | Speed over ground, knots |
| 9 | `cog` | Numeric | Course over ground (True), degrees |
| 10 | `date` | `ddmmyy` | Date (dd=day, mm=month, yy=year) |
| 11 | `mv` | Numeric | Magnetic variation, degrees. Fixed as empty. |
| 12 | `mvE` | Character | Magnetic variation direction. Fixed as empty. |
| 13 | `mode` | Character | Positioning mode flag (Remark [1]). Valid only for NMEA 2.3 and above. |
| 14 | `navStatus` | Character | Navigation status identifier (V indicates system does not output nav status). Valid only for NMEA 4.1 and above. |
| 15 | `CS` | Hex Numeric | Checksum |
| 16 | `<CR><LF>` | Character | Carriage Return and Line Feed |

**Remark [1] Positioning Mode Flags**

| Positioning Mode Flag | Description |
| --- | --- |
| **A** | Autonomous mode |
| **E** | Estimated mode (Dead Reckoning) |
| **N** | Data invalid |
| **D** | Differential mode |
| **M** | Not positioned, but external input or historical position exists |

1.5.6 VTG 

| Information | VTG |
| --- | --- |
| **Description** | Course over ground and ground speed information |
| **Type** | Output |
| **Format** | `$--VTG, cogt, T, cogm, M, sog, N, kph, K, mode*CS<CR><LF>` |
| **Example** | `$GPVTG,75.20,T,,M,0.009,N,0.017,K,A*02` |

**Parameter Description**

| Field | Name | Format | Parameter Description |
| --- | --- | --- | --- |
| 1 | `$--VTG` | String | Message ID, VTG header, `--` is system ID |
| 2 | `cogt` | Numeric | Course over ground (True), degrees |
| 3 | `T` | Character | True North indicator, fixed as T |
| 4 | `cogm` | Numeric | Course over ground (Magnetic), degrees |
| 5 | `M` | Character | Magnetic North indicator, fixed as M |
| 6 | `sog` | Numeric | Speed over ground, knots |
| 7 | `N` | Character | Speed unit knots, fixed as N |
| 8 | `kph` | Numeric | Speed over ground, km/h |
| 9 | `K` | Character | Speed unit km/h, fixed as K |
| 10 | `mode` | Character | Positioning mode flag (Refer to RMC Remark [1]). Valid for NMEA 2.3 and above. |
| 11 | `CS` | Hex Numeric | Checksum |
| 12 | `<CR><LF>` | Character | Carriage Return and Line Feed |

1.5.7 ZDA 

| Information | ZDA |
| --- | --- |
| **Description** | Time and date information |
| **Type** | Output |
| **Format** | `$--ZDA, UTCtime, day, month, year, ltzh, ltzn*CS<CR><LF>` |
| **Example** | `$GPZDA,235316.000,02,07,2011,00,00*51` |

**Parameter Description**

| Field | Name | Format | Parameter Description |
| --- | --- | --- | --- |
| 1 | `$--ZDA` | String | Message ID, ZDA header, `--` is system ID |
| 2 | `UTCtime` | `hhmmss.sss` | UTC time of position |
| 3 | `day` | Numeric | Day, fixed two digits (01-31) |
| 4 | `month` | Numeric | Month, fixed two digits (01-12) |
| 5 | `year` | Numeric | Year, fixed four digits |
| 6 | `ltzh` | Numeric | Local time zone hours, not supported, fixed as 00 |
| 7 | `ltzn` | Numeric | Local time zone minutes, not supported, fixed as 00 |
| 8 | `CS` | Hex Numeric | Checksum |
| 9 | `<CR><LF>` | Character | Carriage Return and Line Feed |

1.5.8 TXT 

**Product Information**

| Information | TXT |
| --- | --- |
| **Description** | Product Information |
| **Type** | Output, output once at startup |
| **Format** | `$GPTXT, xx, yy, zz, info*hh<CR><LF>` |
| **Examples** | `$GPTXT,01,01,02,MA=CASIC*27` (Manufacturer Name) <br> <br> `$GPTXT,01,01,02,IC=ATGB03+ATGR201*71` (Chip model) <br> <br> `$GPTXT,01,01,02,SW=URANUS2,V2.2.1.0*1D` (Software name/version) <br> <br> `$GPTXT,01,01,02,TB=2013-06-20,13:02:49*43` (Compile time) <br> <br> `$GPTXT,01,01,02,MO=GB*77` (Startup mode, GB=GPS+BDS) <br> <br> `$GPTXT,01,01,02,CI=00000000*7A` (Customer ID) |
**Parameter Description**

| Field | Name | Format | Parameter Description |
| --- | --- | --- | --- |
| 1 | `$GPTXT` | String | Message ID |
| 2 | `xx` | Numeric | Total number of sentences for current message (01-99) |
| 3 | `yy` | Numeric | Sentence number (01-99) |
| 4 | `zz` | Numeric | Identifier: 00=Error, 01=Warning, 02=Notification, 07=User Info |
| 5 | `info` | Text | Text information |
| 6 | `CS` | Hex Numeric | Checksum |
| 7 | `<CR><LF>` | Character | Carriage Return and Line Feed |

1.5.9 ANT 

| Information | ANT |
| --- | --- |
| **Description** | Antenna Status |
| **Type** | Output |
| **Format** | `$GPTXT, xx, yy, zz, info*hh<CR><LF>` |
| **Example** | `$GPTXT,01,01,01,ANTENNA OPEN*25` (Open) <br> <br> `$GPTXT,01,01,01,ANTENNA OK*35` (Good) <br> <br> `$GPTXT,01,01,01,ANTENNA SHORT*63` (Short) |
**Parameter Description**

| Field | Name | Format | Parameter Description |
| --- | --- | --- | --- |
| 1 | `$GPTXT` | String | Message ID |
| 2 | `xx` | Numeric | Total sentences, fixed 01 |
| 3 | `yy` | Numeric | Sentence number, fixed 01 |
| 4 | `zz` | Numeric | Text identifier, fixed 01 |
| 5 | `info` | Text | `ANTENNA OPEN`, `ANTENNA OK`, or `ANTENNA SHORT` |
| 6 | `CS` | Hex Numeric | Checksum |
| 7 | `<CR><LF>` | Character | Carriage Return and Line Feed |

1.5.10 DHV 

| Information | DHV |
| --- | --- |
| **Description** | Detailed receiver velocity information |
| **Type** | Output |
| **Format** | `$--DHV, UTCtime, speed3D, spdX, spdY, spdZ, gdspd*CS<CR><LF>` |
| **Example** | `$GNDHV,021150.000,0.03,0.006,-0.042,-0.026,0.06*65` |

**Parameter Description**

| Field | Name | Format | Parameter Description |
| --- | --- | --- | --- |
| 1 | `$--DHV` | String | Message ID |
| 2 | `UTCtime` | `hhmmss.sss` | UTC time of current moment |
| 3 | `speed3D` | Numeric | 3D velocity (m/s) |
| 4 | `spdX` | Numeric | ECEF-X velocity (m/s) |
| 5 | `spdY` | Numeric | ECEF-Y velocity (m/s) |
| 6 | `spdZ` | Numeric | ECEF-Z velocity (m/s) |
| 7 | `gdspd` | Numeric | Horizontal ground speed (m/s) |
| 8 | `CS` | Hex Numeric | Checksum |
| 9 | `<CR><LF>` | Character | Carriage Return and Line Feed |

1.5.11 LPS (Supported by 5T only) 

| Information | LPS |
| --- | --- |
| **Description** | Leap Second Information |
| **Type** | Output |
| **Format** | `$GPTXT, xx, yy, zz, LS=system, valid, utcLS, utcLSF, utcTOW, utcWNT, utcDN, utcWNF, utcA0, utcA1, leapDt, dateLsf, lsfExp, wnExp, wnExpNum*hh<CR><LF>` |
| **Example** | (See document for detailed examples involving GPS and BDS leap second status) |

**Parameter Description**

| Field | Name | Format | Parameter Description |
| --- | --- | --- | --- |
| 1 | `$GPTXT` | String | Message ID |
| 2 | `xx` | Numeric | Total sentences, fixed 01 |
| 3 | `yy` | Numeric | Sentence number, fixed 01 |
| 4 | `zz` | Numeric | Text identifier, fixed 02 |
| 5 | `LS=` | String | Leap second message identifier, fixed |
| 6 | `system` | Character | System: 0=GPS, 1=BDS |
| 7 | `valid` | Character | Leap second valid flag. 0=Invalid; 1=Valid but not used for timing; 2=Invalid but used for timing; 3=Valid and used for timing. |
| 8 | `utcLS` | Numeric | Current leap second (seconds). |
| 9 | `utcLSF` | Numeric | Predicted leap second after event (seconds). |
| 10 | `utcTOW` | Numeric | Reference time for UTC correction (Week within time, units of 4096s). |
| 11 | `utcWNT` | Numeric | Reference time week number (Modulo 256). |
| 12 | `utcDN` | Numeric | Day of week for leap second. GPS: 1-7; BDS: 1-6. |
| 13 | `utcWNF` | Numeric | Week number for leap second (Modulo 256). |
| 14 | `utcA0` | Numeric | Time error between UTC and satellite time (Scale ). |
| 15 | `utcA1` | Numeric | Time error change rate (Scale ). |
| 16 | `leapDt` | Numeric | Time interval until leap second event. Output if valid and change exists. |
| 17 | `dateLsf` | `ddmmyy` | Date of predicted leap second. Output if valid and change exists. |
| 18 | `lsfExp` | Hex Numeric | Leap second correction time anomaly alarm (32-bit hex mask for 32 sats). 1=Anomaly. |
| 19 | `wnExp` | Hex Numeric | Week number anomaly alarm (Week rollover alarm) (32-bit hex mask). 1=Anomaly. |
| 20 | `wnExpNum` | Numeric | Magnitude of week number jump. Negative=Jump forward. |
| 21 | `CS` | Hex Numeric | Checksum |
| 22 | `<CR><LF>` | Character | Carriage Return and Line Feed |

1.5.12 UTC (Supported by 5T only) 

| Information | UTC |
| --- | --- |
| **Description** | Receiver status, simplified leap second correction information |
| **Type** | Output |
| **Format** | `$--UTC, UTCtime, lat, uLat, lon, uLon, FS, numSv, HDOP, hgt, uMsl, date, antSta, timeSrc, leapValid, dtLs, dtLsf, leapTime*CS<CR><LF>` |

**Parameter Description**

| Field | Name | Format | Parameter Description |
| --- | --- | --- | --- |
| 1 | `$--UTC` | String | Message ID |
| 2 | `UTCtime` | `hhmmss` | UTC time (hh/mm/ss) |
| 3 | `lat` | `ddmm.mmmm` | Latitude |
| 4 | `uLat` | Character | N/S |
| 5 | `lon` | `dddmm.mmmm` | Longitude |
| 6 | `uLon` | Character | E/W |
| 7 | `FS` | Numeric | Positioning Quality (0=Invalid, 1=Standard, 6=Estimated) |
| 8 | `numSv` | Numeric | Number of satellites |
| 9 | `HDOP` | Numeric | HDOP |
| 10 | `hgt` | Numeric | Altitude |
| 11 | `uMsl` | Character | Fixed 'M' |
| 12 | `date` | `ddmmyy` | Date |
| 13 | `antSta` | Numeric | Antenna status (0=Open, 2=Normal, 3=Short) |
| 14 | `timeSrc` | Numeric | Timing Source (0=GPS, 1=BDS) |
| 15 | `leapValid` | Numeric | Leap second valid flag (0=Invalid, 1=Valid) |
| 16 | `dtLs` | Numeric | Current leap second correction value |
| 17 | `dtLsf` | Numeric | Predicted new leap second correction value (Empty if no forecast) |
| 18 | `leapTime` | `mmyy` | Predicted leap second occurrence time (Empty if no forecast) |
| 19 | `CS` | Hex Numeric | Checksum |
| 20 | `<CR><LF>` | Character | Carriage Return and Line Feed |

1.5.13 GST 

| Information | GST |
| --- | --- |
| **Description** | Receiver pseudorange measurement accuracy detail |
| **Type** | Output |
| **Format** | `$--GST, UTCtime, RMS, stdDevMaj, stdDevMin, orientation, stdLat, stdLon, stdAlt*CS<CR><LF>` |
| **Example** | `$BDGST,081409.000,0.5,,,,0.2,0.1,0.4*5E` |

**Parameter Description**

| Field | Name | Format | Parameter Description |
| --- | --- | --- | --- |
| 1 | `$--GST` | String | Message ID |
| 2 | `UTCtime` | `hhmmss.sss` | UTC Time |
| 3 | `RMS` | Numeric | RMS value of pseudorange error (meters) |
| 4 | `stdDevMaj` | Numeric | Standard deviation of semi-major axis (Not supported) |
| 5 | `stdDevMin` | Numeric | Standard deviation of semi-minor axis (Not supported) |
| 6 | `orientation` | Numeric | Orientation of semi-major axis (Not supported) |
| 7 | `stdLat` | Numeric | Standard deviation of latitude error (meters) |
| 8 | `stdLon` | Numeric | Standard deviation of longitude error (meters) |
| 9 | `stdAlt` | Numeric | Standard deviation of altitude error (meters) |
| 10 | `CS` | Hex Numeric | Checksum |
| 11 | `<CR><LF>` | Character | Carriage Return and Line Feed |

1.5.14 INS (Supported by 5S series only) 

| Information | INS |
| --- | --- |
| **Description** | Inertial Navigation System (INS) Information |
| **Type** | Output |
| **Format** | `$GPTXT, xx, yy, zz, INS_INF=sensorID, attMode, status, sensorOK, RAM, ramStart*hh<CR><LF>` |

**Parameter Description**

| Field | Name | Format | Parameter Description |
| --- | --- | --- | --- |
| 1 | `$GPTXT` | String | Message ID |
| 2 | `xx` | Numeric | Total sentences, fixed 01 |
| 3 | `yy` | Numeric | Sentence number, fixed 01 |
| 4 | `zz` | Numeric | Text identifier |
| 5 | `INS_INF` | String | Fixed "INS_INF" |
| 6 | `sensorID` | Numeric | Sensor type: 1 or 2 |
| 7 | `attMode` | Numeric | Installation attitude mode (0=Front, 1=Right, 2=Back, 3=Left, 9=Adaptive) |
| 8 | `fs` | Numeric | Sample count for RXM_SENSOR message output (0, 1, 2, 5, 10, 25, 50). 0=Off. |
| 9 | `status` | Numeric | Filter convergence status (2=Converged) |
| 10 | `sensorOK` | Numeric | Sensor Status |
| 11 | `RAM` | String | Fixed "RAM" |
| 12 | `ramStart` | Numeric | Dead reckoning on startup with backup power (1=On, 0=Off) |
| 13 | `CS` | Hex Numeric | Checksum |
| 14 | `<CR><LF>` | Character | Carriage Return and Line Feed |

### 1.6 NMEA Custom Messages

1.6.1 CAS00 

| Information | CAS00 |
| --- | --- |
| **Description** | Saves current configuration to FLASH. Configuration is retained even after power loss. |
| **Type** | Input |
| **Format** | `$PCAS00*CS<CR><LF>` |
| **Example** | `$PCAS00*01` |

**Parameter Description**

| Field | Name | Format | Parameter Description |
| --- | --- | --- | --- |
| 1 | `$PCAS00` | String | Message ID |
| 2 | `CS` | Hex Numeric | Checksum |
| 3 | `<CR><LF>` | Character | Carriage Return and Line Feed |

1.6.2 CAS01 

| Information | CAS01 |
| --- | --- |
| **Description** | Set serial communication baud rate |
| **Type** | Input |
| **Format** | `$PCAS01, br*CS<CR><LF>` |
| **Example** | `$PCAS01,1*1D` |

**Parameter Description**

| Field | Name | Format | Parameter Description |
| --- | --- | --- | --- |
| 1 | `$PCAS01` | String | Message ID |
| 2 | `br` | Numeric | Baud rate configuration: <br> <br> 0=4800, 1=9600, 2=19200, 3=38400, 4=57600, 5=115200 |
| 3 | `CS` | Hex Numeric | Checksum |
| 4 | `<CR><LF>` | Character | Carriage Return and Line Feed |

1.6.3 CAS02 

| Information | CAS02 |
| --- | --- |
| **Description** | Set positioning update rate |
| **Type** | Input |
| **Format** | `$PCAS02, fixInt*CS<CR><LF>` |
| **Example** | `$PCAS02,1000*2E` |

**Parameter Description**

| Field | Name | Format | Parameter Description |
| --- | --- | --- | --- |
| 1 | `$PCAS02` | String | Message ID |
| 2 | `fixInt` | Numeric | Update interval in ms.<br>1000=1Hz<br>500=2Hz<br>250=4Hz<br>200=5Hz<br>100=10Hz |
| 3 | `CS` | Hex Numeric | Checksum |
| 4 | `<CR><LF>` | Character | Carriage Return and Line Feed |

1.6.4 CAS03 

| Information | CAS03 |
| --- | --- |
| **Description** | Set desired NMEA output sentences. |
| **Type** | Input |
| **Format** | `$PCAS03, nGGA, nGLL, nGSA, nGSV, nRMC, nVTG, nZDA, nANT, nDHV, nLPS, res1, res2, nUTC, nGST, res3, res4, res5, nTIM*CS<CR><LF>` |
| **Example** | `$PCAS03,1,1,1,1,1,1,1,1,0,0,,,1,1,,,,1*33` |

**Parameter Description**

| Field | Name | Format | Parameter Description |
| --- | --- | --- | --- |
| 1 | `$PCAS03` | String | Message ID |
| 2 | `nGGA` | Numeric | Output frequency based on positioning update rate. n(0-9) means output once every n updates. 0=Disable. Empty=Keep original. |
| 3 | `nGLL` | Numeric | Same as nGGA |
| 4 | `nGSA` | Numeric | Same as nGGA |
| 5 | `nGSV` | Numeric | Same as nGGA |
| 6 | `nRMC` | Numeric | Same as nGGA |
| 7 | `nVTG` | Numeric | Same as nGGA |
| 8 | `nZDA` | Numeric | Same as nGGA |
| 9 | `nANT` | Numeric | Same as nGGA |
| 10 | `nDHV` | Numeric | Same as nGGA |
| 11 | `nLPS` | Numeric | Same as nGGA |
| 12 | `res1` | Numeric | Reserved |
| 13 | `res2` | Numeric | Reserved |
| 14 | `nUTC` | Numeric | Same as nGGA |
| 15 | `nGST` | Numeric | Same as nGST |
| 16 | `res3` | Numeric | Reserved |
| 17 | `res4` | Numeric | Reserved |
| 18 | `res5` | Numeric | Reserved |
| 19 | `nTIM` | Numeric | TIM (PCAS60) Output frequency, same as nGGA |
| 20 | `CS` | Hex Numeric | Checksum |
| 21 | `<CR><LF>` | Character | Carriage Return and Line Feed |

1.6.5 CAS04 

| Information | CAS04 |
| --- | --- |
| **Description** | Configure working system. |
| **Type** | Input |
| **Format** | `$PCAS04, mode*hh<CR><LF>` |
| **Example** | `$PCAS04,3*1A` (GPS+BDS) |

**Parameter Description**

| Field | Name | Format | Parameter Description |
| --- | --- | --- | --- |
| 1 | `$PCAS04` | String | Message ID |
| 2 | `mode` | Numeric | Working system configuration: <br> <br> 1=GPS, 2=BDS, 3=GPS+BDS, 4=GLONASS, 5=GPS+GLONASS, 6=BDS+GLONASS, 7=GPS+BDS+GLONASS |
| 3 | `CS` | Hex Numeric | Checksum |
| 4 | `<CR><LF>` | Character | Carriage Return and Line Feed |

1.6.6 CAS05 

| Information | CAS05 |
| --- | --- |
| **Description** | Set NMEA protocol type selection. |
| **Type** | Input |
| **Format** | `$PCAS05, ver*CS<CR><LF>` |
| **Example** | `$PCAS05,1*19` |

**Parameter Description**

| Field | Name | Format | Parameter Description |
| --- | --- | --- | --- |
| 1 | `$PCAS05` | String | Message ID |
| 2 | `mode` | Numeric | NMEA protocol type: <br> <br> 1 or 2 = NMEA 4.1+ <br> <br> 5 = BDS/GPS Dual mode protocol (compatible with NMEA 2.3+, 4.0) <br> <br> 9 = Single GPS NMEA 0183 (compatible with NMEA 2.2) |
| 3 | `CS` | Hex Numeric | Checksum |
| 4 | `<CR><LF>` | Character | Carriage Return and Line Feed |

1.6.7 CAS06 

| Information | CAS06 |
| --- | --- |
| **Description** | Query product information |
| **Type** | Input |
| **Format** | `$PCAS06, info*CS<CR><LF>` |
| **Example** | `$PCAS06,0*1B` |

**Parameter Description**

| Field | Name | Format | Parameter Description |
| --- | --- | --- | --- |
| 1 | `$PCAS06` | String | Message ID |
| 2 | `info` | Numeric | Info type to query: <br> <br> 0=Firmware version <br> <br> 1=Hardware model/Serial <br> <br> 2=Working mode <br> <br> 3=Customer ID <br> <br> 5=Upgrade code info |
| 3 | `CS` | Hex Numeric | Checksum |
| 4 | `<CR><LF>` | Character | Carriage Return and Line Feed |

1.6.8 CAS10 

| Information | CAS10 |
| --- | --- |
| **Description** | Receiver Restart |
| **Type** | Input |
| **Format** | `$PCAS10, rs*CS<CR><LF>` |
| **Example** | `$PCAS10,0*1C` (Hot Start) |

**Parameter Description**

| Field | Name | Format | Parameter Description |
| --- | --- | --- | --- |
| 1 | `$PCAS10` | String | Message ID |
| 2 | `rs` | Numeric | Startup mode: <br> <br> 0=Hot start (Backup data valid) <br> <br> 1=Warm start (Clear ephemeris) <br> <br> 2=Cold start (Clear all except config) <br> <br> 3=Factory start (Clear all, reset to default) |
| 3 | `CS` | Hex Numeric | Checksum |
| 4 | `<CR><LF>` | Character | Carriage Return and Line Feed |

1.6.9 CAS12 

| Information | CAS12 |
| --- | --- |
| **Description** | Receiver Standby Mode Control (Supported by 5L low power module) |
| **Type** | Input |
| **Format** | `$PCAS12, stdbysec*CS<CR><LF>` |
| **Example** | `$PCAS12,60*28` (Standby for 60s) |

**Parameter Description**

| Field | Name | Format | Parameter Description |
| --- | --- | --- | --- |
| 1 | `$PCAS12` | String | Message ID |
| 2 | `stdbysec` | Numeric | Standby duration in seconds (Max 65535) |
| 3 | `CS` | Hex Numeric | Checksum |
| 4 | `<CR><LF>` | Character | Carriage Return and Line Feed |

1.6.10 CAS20 

| Information | CAS20 |
| --- | --- |
| **Description** | Online upgrade instruction |
| **Type** | Input |
| **Format** | `$PCAS20*CS<CR><LF>` |
| **Example** | `$PCAS20*03` |

**Parameter Description**

| Field | Name | Format | Parameter Description |
| --- | --- | --- | --- |
| 1 | `$PCAS20` | String | Message ID |
| 2 | `CS` | Hex Numeric | Checksum |
| 3 | `<CR><LF>` | Character | Carriage Return and Line Feed |

1.6.11 CAS15 

| Information | CAS15 |
| --- | --- |
| **Description** | Satellite system control instruction. Can configure reception of specific satellites. (Supported in versions post V5200) |
| **Type** | Input |
| **Format** | `$PCAS15, X, YYYYYYYY*CS<CR><LF>` |
| **Example** | `$PCAS15,2,FFFFFFFF*37` (Enable BDS 1-32) |

**Parameter Description**

| Field | Name | Format | Parameter Description |
| --- | --- | --- | --- |
| 1 | `$PCAS15` | String | Message ID |
| 2 | `SYS_ID` | Numeric | 2=BDS 1-32, 3=BDS 33-64, 4=SBAS (1-19, PRN 120-138), 5=QZSS (1-5, PRN 193-197) |
| 3 | `SV_MASK` | Hex (1-8 chars) | Satellite mask. Each hex char controls 4 satellites. |
| 4 | `CS` | Hex Numeric | Checksum |
| 5 | `<CR><LF>` | Character | Carriage Return and Line Feed |

1.6.12 CAS60 

| Information | CAS60 |
| --- | --- |
| **Description** | Receiver time information. (Supported in 5T versions post V5302) |
| **Type** | Output |
| **Format** | `$PCAS60, UTCtime, ddmmyyyy, wn, tow, timeValid, leaps, leapsValid*CS` |
| **Example** | `$PCAS60,091242.000,23122019,2085,119580,1,18,1*33` |

**Parameter Description**

| Field | Name | Format | Parameter Description |
| --- | --- | --- | --- |
| 1 | `$PCAS60` | String | Message ID |
| 2 | `UTCtime` | `hhmmss.sss` | UTC Time |
| 3 | `ddmmyyyy` | Numeric | Date |
| 4 | `wn` | Numeric | Current GPS Week Number |
| 5 | `tow` | Numeric | Current GPS Time of Week |
| 6 | `timeValid` | Numeric | Time validity (1=Valid, 0=Invalid) |
| 7 | `leaps` | Numeric | Leap seconds (GPS vs UTC) |
| 8 | `leapsValid` | Numeric | Leap seconds validity (1=Valid, 0=Invalid) |
| 9 | `CS` | Hex Numeric | Checksum |
| 10 | `<CR><LF>` | Character | Carriage Return and Line Feed |
