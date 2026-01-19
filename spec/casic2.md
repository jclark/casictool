
## **2 CASIC Protocol**

### **2.1 CASIC Protocol Features**

The CASIC receiver uses the custom Standard Interface Protocol (CSIP, CASIC Standard Interface Protocol) to send data to the host. Data is transmitted in asynchronous serial mode1.

### **2.2 CASIC Protocol Framework**

**CSIP Packet Structure** 2

| Field 1 | Field 2 | Field 3 | Field 4 | Field 5 | Field 6 |
| :---- | :---- | :---- | :---- | :---- | :---- |
| **Message Header** | **Payload Length** | **Message Class** | **Message ID** | **Payload** | **Checksum** |
| 0xBA, 0xCE | Unsigned Short | 1 Byte | 1 Byte | \< 2k Bytes | Unsigned Integer (4 Bytes) |

**Field 1: Message Header (0xBA, 0xCE)** Four hexadecimal characters serve as the message start delimiter (message header), occupying two bytes3.

**Field 2: Payload Length (len)** The message length (two bytes) indicates the number of bytes occupied by the Payload (Field 5). It does not include the message header, message type, message ID, length, or checksum fields4.

**Field 3: Message Class (class)** Occupies one byte, indicating the basic subset to which the current message belongs5.

**Field 4: Message ID (id)** A one-byte message number following the message class6.

**Field 5: Payload (payload)** The payload is the specific content transmitted by the data packet. Its length (in bytes) is variable and must be a multiple of 47.

**Field 6: Checksum (ckSum)** The checksum is the cumulative sum (by word, where 1 word \= 4 bytes) of all data from Field 2 to Field 5 (inclusive). It occupies 4 bytes8.

The calculation of the checksum follows this algorithm:

C

ckSum \= (id \<\< 24) \+ (class \<\< 16) \+ len;  
for (i \= 0; i \< (len / 4); i++) {  
    ckSum \= ckSum \+ payload\[i\];  
}

In the formula, payload contains all information from Field 5\. During calculation, Fields 2 through 4 are first assembled (4 bytes form one word), and then the data in Field 5 is accumulated in order of 4-byte groups (received first in the lower bits)9.

### **2.3 CASIC Types and IDs**

Each class of interaction messages for the CASIC receiver is a collection of related messages10.

| Name | Type | Description |
| :---- | :---- | :---- |
| **NAV** | 0x01 | Navigation results: Position, Velocity, Time |
| **TIM** | 0x02 | Timing messages: Time pulse output, Time mark results |
| **RXM** | 0x03 | Receiver output measurement information (Pseudorange, Carrier Phase, etc.) |
| **ACK** | 0x05 | ACK/NAK messages: Response messages to CFG messages |
| **CFG** | 0x06 | Input configuration messages: Configure navigation mode, baud rate, etc. |
| **MSG** | 0x08 | Receiver output satellite navigation message information |
| **MON** | 0x0A | Monitoring messages: Communication status, CPU load, Stack usage, etc. |
| **AID** | 0x0B | Assistance messages: Ephemeris, Almanac, and other A-GPS data |

11

### **2.4 CASIC Payload Definition Rules**

**2.4.1 Data Encapsulation** To facilitate structured data encapsulation, data in the payload section is arranged in a specific way: data within each message class is packed tightly. 2-byte values are placed at offsets that are multiples of 2, and 4-byte values are placed at offsets that are multiples of 412.

**2.4.2 Message Naming** Message names consist of a structure like "Message Type \+ Message Name". For example: the configuration message for PPS is named CFG-PPS13.

**2.4.3 Data Types** Unless otherwise defined, all multi-byte numerical values are arranged in Little-Endian format. All floating-point values are transmitted according to IEEE754 Single Precision and Double Precision standards14.

| Abbreviation | Type | Bytes | Remarks |
| :---- | :---- | :---- | :---- |
| **U1** | Unsigned Char | 1 |  |
| **I1** | Signed Char | 1 | Two's complement |
| **U2** | Unsigned Short | 2 |  |
| **I2** | Signed Short | 2 | Two's complement |
| **U4** | Unsigned Long | 4 |  |
| **I4** | Signed Long | 4 | Two's complement |
| **R4** | IEEE754 Single Precision | 4 |  |
| **R8** | IEEE754 Double Precision | 8 |  |

15

### **2.5 CASIC Message Interaction**

Defines the mechanism for receiver message input and output. When the receiver receives a CFG type message, it must reply with an ACK-ACK or ACK-NACK message based on whether the configuration message was processed correctly. The sender must not send a second CFG message before the receiver replies to the received CFG message. Other messages received by the receiver do not require a reply16.

### **2.6 CASIC Message Overview**

| Message Name | Class/ID | Length | Type | Description |
| :---- | :---- | :---- | :---- | :---- |
| **Class NAV** |  |  | **NAV** | **Navigation Results** |
| NAV-STATUS | 0x01 0x00 | 80 | Periodic | Receiver navigation status |
| NAV-DOP | 0x01 0x01 | 28 | Periodic | Dilution of Precision |
| NAV-SOL | 0x01 0x02 | 72 | Periodic | Reduced PVT navigation information |
| NAV-PV | 0x01 0x03 | 80 | Periodic | Position and velocity information |
| NAV-TIMEUTC | 0x01 0x10 | 24 | Periodic | UTC time information |
| NAV-CLOCK | 0x01 0x11 | 64 | Periodic | Clock solution information |
| NAV-GPSINFO | 0x01 0x20 | `8 + 12 *` | Periodic | GPS satellite information |
| NAV-BDSINFO | 0x01 0x21 | `8 + 12 *` | Periodic | BDS satellite information |
| NAV-GLNINFO | 0x01 0x22 | `8 + 12 *` | Periodic | GLONASS satellite information |
| **Class TIM** |  |  | **TIM** | **Time Messages** |
| TIM-TP | 0x02 0x00 | 24 | Periodic | Time pulse information |
| **Class RXM** |  |  | **RXM** | **Receiver Measurement Info** |
| RXM-MEASX | 0x03 0x10 | `16 + 32 *` | Periodic | Raw measurement info (Pseudorange, Carrier Phase) |
| RXM-SVPOS | 0x03 0x11 | `16 + 48 *` | Periodic | Satellite position information |
| **Class ACK** |  |  | **ACK/NACK** | **Message** |
| ACK-NACK | 0x05 0x00 | 4 | Response | Reply indicating message was not correctly received |
| ACK-ACK | 0x05 0x01 | 4 | Response | Reply indicating message was correctly received |
| **Class CFG** |  |  | **CFG Input** | **Configuration Messages** |
| CFG-PRT | 0x06 0x00 | 0/8 | Query/Set | Query/Configure UART working mode |
| CFG-MSG | 0x06 0x01 | 0/4 | Query/Set | Query/Configure information transmission frequency |
| CFG-RST | 0x06 0x02 | 4 | Set | Restart receiver / Clear saved data structures |
| CFG-TP | 0x06 0x03 | 0/16 | Query/Set | Query/Configure receiver PPS related parameters |
| CFG-RATE | 0x06 0x04 | 0/4 | Query/Set | Query/Configure receiver navigation rate |
| CFG-CFG | 0x06 0x05 | 4 | Set | Clear, save, and load configuration information |
| CFG-TMODE | 0x06 0x06 | 0/28 | Query/Set | Query/Configure receiver PPS timing mode |
| CFG-NAVX | 0x06 0x07 | 0/44 | Query/Set | Query/Professional configuration of navigation engine parameters |
| CFG-GROUP | 0x06 0x08 | 0/56 | Query/Set | Query/Configure GLONASS group delay parameters |
| **Class MSG** |  |  | **MSG** | **Receiver Satellite Message Info** |
| MSG-BDSUTC | 0x08 0x00 | 20 | Periodic | Receiver output BDS system UTC info |
| MSG-BDSION | 0x08 0x01 | 16 | Periodic | Receiver output BDS system Ionosphere info |
| MSG-BDSEPH | 0x08 0x02 | 92 | Periodic | Receiver output BDS system Ephemeris info |
| MSG-GPSUTC | 0x08 0x05 | 20 | Periodic | Receiver output GPS system UTC info |
| MSG-GPSION | 0x08 0x06 | 16 | Periodic | Receiver output GPS system Ionosphere info |
| MSG-GPSEPH | 0x08 0x07 | 72 | Periodic | Receiver output GPS system Ephemeris info |
| MSG-GLNEPH | 0x08 0x08 | 68 | Periodic | Receiver output GLONASS system Ephemeris info |
| **Class MON** |  |  | **MON** | **Monitor Messages** |
| MON-VER | 0x0A 0x04 | 64 | Response/Query | Output version information |
| MON-HW | 0x0A 0x09 | 56 | Periodic/Query | Hardware configuration status |
| **Class AID** |  |  | **AID** | **Assistance Messages** |
| AID-INI | 0x0B 0x01 | 56 | Query/Input | Assist position, time, frequency, clock bias info |
| AID-HUI | 0x0B 0x03 | 60 | Input | Assist health info, UTC parameters, Ionosphere parameters |

17171717

### **2.7 NAV (0x01)**

Navigation results: Position, velocity, time, precision, heading, DOP, satellite count, etc. NAV messages are divided into several types containing different information18.

#### **2.7.1 NAV-STATUS (0x01 0x00)**

**Message Structure** 19

| Header | Length (Bytes) | Identifier | Payload | Checksum |
| :---- | :---- | :---- | :---- | :---- |
| 0xBA 0xCE | 80 | 0x01 0x00 | See table below | 4 Bytes |

**Payload Content**

| Char Offset | Data Type | Name | Scale/Unit | Description |
| :---- | :---- | :---- | :---- | :---- |
| 0 | U4 | runTime | ms | Running time since boot/reset |
| 4 | U2 | fixInterval | ms | Positioning time interval |
| 6 | U1 | posValid |  | Positioning flag (Remark \[1\]) |
| 7 | U1 | velValid |  | Velocity flag (Remark \[2\]) |
| 8 | U1\*32 | gpsMsgFlag |  | Almanac and Ephemeris message validity flags for 32 GPS satellites (Remark \[3\]) |
| 40 | U1\*24 | glnMsgFlag |  | Almanac and Ephemeris message validity flags for 24 GLONASS satellites (Remark \[3\]) |
| 64 | U1\*14 | bdsMsgFlag |  | Almanac and Ephemeris message validity flags for 14 BDS satellites (Remark \[3\]) |
| 78 | U1 | gpsUtcIonFlag |  | Validity flags for GPS UTC and Ionosphere messages (Remark \[4\]) |
| 79 | U1 | bdsUtcIonFlag |  | Validity flags for BDS UTC and Ionosphere messages (Remark \[4\]) |

**Remark \[1\]: Positioning Flag**

| Value | Description |
| :--- | :--- |
| 0 | Positioning Invalid |
| 1 | External Input Position |
| 2 | Roughly Estimated Position |
| 3 | Maintaining Last Position |
| 4 | Dead Reckoning |
| 5 | Quick Mode Positioning |
| 6 | 2D Positioning |
| 7 | 3D Positioning |
| 8 | GNSS+DR Integrated Navigation |

**Remark \[2\]: Velocity Flag**

| Value | Description |
| :--- | :--- |
| 0 | Velocity Invalid |
| 1 | External Input Velocity |
| 2 | Roughly Estimated Velocity |
| 3 | Maintaining Last Velocity |
| 4 | Velocity Reckoning |
| 5 | Quick Mode Velocity |
| 6 | 2D Velocity |
| 7 | 3D Velocity |
| 8 | GNSS+DR Integrated Navigation Velocity |

**Remark \[3\]: Message Validity Flag**

Upper 4 bits indicate Almanac message validity; Lower 4 bits indicate Ephemeris message validity.

| Value | Description |
| :--- | :--- |
| 0 | Missing |
| 1 | Unhealthy |
| 2 | Expired |
| 3 | Valid |

**Remark \[4\]: Message Validity Flag**

Upper 4 bits indicate UTC parameter validity; Lower 4 bits indicate Ionosphere parameter validity.

| Value | Description |
| :--- | :--- |
| 0 | Missing |
| 1 | Unhealthy |
| 2 | Expired |
| 3 | Valid |

20

#### **2.7.2 NAV-DOP (0x01 0x01)**

**Message Structure** 21

| Header | Length (Bytes) | Identifier | Payload | Checksum |
| :---- | :---- | :---- | :---- | :---- |
| 0xBA 0xCE | 28 | 0x01 0x01 | See table below | 4 Bytes |

**Payload Content**

| Char Offset | Data Type | Name | Scale/Unit | Description |
| :---- | :---- | :---- | :---- | :---- |
| 0 | U4 | runTime | ms | Running time since boot/reset |
| 4 | R4 | pDop |  | Position DOP |
| 8 | R4 | hDop |  | Horizontal DOP |
| 12 | R4 | vDop |  | Vertical DOP |
| 16 | R4 | nDop |  | North DOP |
| 20 | R4 | eDop |  | East DOP |
| 24 | R4 | tDop |  | Time DOP |

#### **2.7.3 NAV-SOL (0x01 0x02)**

**Message Structure** 22

| Header | Length (Bytes) | Identifier | Payload | Checksum |
| :---- | :---- | :---- | :---- | :---- |
| 0xBA 0xCE | 72 | 0x01 0x02 | See table below | 4 Bytes |

**Payload Content**

| Char Offset | Data Type | Name | Scale/Unit | Description |
| :---- | :---- | :---- | :---- | :---- |
| 0 | U4 | runTime | ms | Running time since boot/reset |
| 4 | U1 | posValid |  | Positioning flag (Remark \[1\]) |
| 5 | U1 | velValid |  | Velocity flag (Remark \[2\]) |
| 6 | U1 | timeSrc |  | Time Source (Remark \[3\]) |
| 7 | U1 | system |  | Receiver multimode reception mask (Remark \[4\]) |
| 8 | U1 | numSV |  | Total number of satellites used in solution |
| 9 | U1 | numSVGPS |  | Number of GPS satellites used in solution |
| 10 | U1 | numSVBDS |  | Number of BDS satellites used in solution |
| 11 | U1 | numSVGLN |  | Number of GLONASS satellites used in solution |
| 12 | U2 | res |  | Reserved |
| 14 | U2 | week |  | Week Number |
| 16 | R8 | tow | s | Time of Week |
| 24 | R8 | ecefX | m | X Coordinate in ECEF frame |
| 32 | R8 | ecefY | m | Y Coordinate in ECEF frame |
| 40 | R8 | ecefZ | m | Z Coordinate in ECEF frame |
| 48 | R4 | pAcc | m² | Variance of 3D position estimation error |
| 52 | R4 | ecefVX | m/s | X Velocity in ECEF frame |
| 56 | R4 | ecefVY | m/s | Y Velocity in ECEF frame |
| 60 | R4 | ecefVZ | m/s | Z Velocity in ECEF frame |
| 64 | R4 | sAcc | (m/s)² | Variance of 3D velocity estimation error |
| 68 | R4 | pDop |  | Position DOP |

**Remark \[1\] & \[2\]** refer to Section 2.7.1 Remarks23.

**Remark \[3\]: Time Source**

| Value | Description |
| :--- | :--- |
| 0 | GPS Timing (Time of week and week number obtained from GPS satellites) |
| 1 | BDS |
| 2 | GLONASS |

**Remark \[4\]: Multimode Reception Mask**

| Bit | Description |
| :--- | :--- |
| B0 | 1 \= GPS satellites used for positioning |
| B1 | 1 \= BDS satellites used for positioning |
| B2 | 1 \= GLONASS satellites used for positioning |

24

#### **2.7.4 NAV-PV (0x01 0x03)**

**Message Structure** 25

| Header | Length (Bytes) | Identifier | Payload | Checksum |
| :---- | :---- | :---- | :---- | :---- |
| 0xBA 0xCE | 80 | 0x01 0x03 | See table below | 4 Bytes |

**Payload Content**

| Char Offset | Data Type | Name | Scale/Unit | Description |
| :---- | :---- | :---- | :---- | :---- |
| 0 | U4 | runTime | ms | Running time since boot/reset |
| 4 | U1 | posValid |  | Positioning flag (Ref 2.7.3 Remark \[1\]) |
| 5 | U1 | velValid |  | Velocity flag (Ref 2.7.3 Remark \[2\]) |
| 6 | U1 | system |  | Multimode reception mask (Ref 2.7.3 Remark \[4\]) |
| 7 | U1 | numSV |  | Total satellites used in solution |
| 8 | U1 | numSVGPS |  | GPS satellites used in solution |
| 9 | U1 | numSVBDS |  | BDS satellites used in solution |
| 10 | U1 | numSVGLN |  | GLONASS satellites used in solution |
| 11 | U1 | res |  | Reserved |
| 12 | R4 | pDop |  | Position DOP |
| 16 | R8 | lon | deg | Longitude |
| 24 | R8 | lat | deg | Latitude |
| 32 | R4 | height | m | Ellipsoidal Height |
| 36 | R4 | sepGeoid | m | Geoid Separation (Diff between Ellipsoidal and MSL) |
| 40 | R4 | hAcc | m² | Variance of horizontal position accuracy |
| 44 | R4 | vAcc | m² | Variance of vertical position accuracy |
| 48 | R4 | velN | m/s | North Velocity in ENU frame |
| 52 | R4 | velE | m/s | East Velocity in ENU frame |
| 56 | R4 | velU | m/s | Up Velocity in ENU frame |
| 60 | R4 | speed3D | m/s | 3D Speed |
| 64 | R4 | speed2D | m/s | 2D Ground Speed |
| 68 | R4 | heading | deg | Heading |
| 72 | R4 | sAcc | (m/s)² | Variance of ground speed accuracy |
| 76 | R4 | cAcc | deg² | Variance of heading accuracy |

#### **2.7.5 NAV-TIMEUTC (0x01 0x10)**

**Message Structure** 26

| Header | Length (Bytes) | Identifier | Payload | Checksum |
| :---- | :---- | :---- | :---- | :---- |
| 0xBA 0xCE | 24 | 0x01 0x10 | See table below | 4 Bytes |

**Payload Content**

| Char Offset | Data Type | Name | Scale/Unit | Description |
| :---- | :---- | :---- | :---- | :---- |
| 0 | U4 | runTime | ms | Running time since boot/reset |
| 4 | R4 | tAcc | s² | Time estimation accuracy (1/c²) |
| 8 | R4 | msErr | ms | Residual error after rounding milliseconds |
| 12 | U2 | year | year | UTC Year (1999\~2099) |
| 14 | U1 | month | month | UTC Month (1\~12) |
| 15 | U1 | day | day | UTC Day (1\~31) |
| 16 | U1 | hour | hour | UTC Hour (0\~23) |
| 17 | U1 | min | min | UTC Minute (0\~59) |
| 18 | U1 | sec | s | UTC Second (0\~59) |
| 19 | U1 | valid |  | Time valid flag (Remark \[1\]) |
| 20 | U1 | timeSrc |  | Timing system flag (Remark \[2\]) |
| 21 | U1 | dateValid |  | Date valid flag (Remark \[3\]) |

**Remark \[1\]: Time Valid Flag**

| Bit | Description |
| :--- | :--- |
| B0 | UTC Time of Week valid (0=Invalid, 1=Valid) |
| B1 | UTC Week Number valid (0=Invalid, 1=Valid) |
| B2 | UTC Leap Second correction valid (0=Invalid, 1=Valid) |

**Remark \[2\]: Timing System Flag**

| Value | Description |
| :--- | :--- |
| 0 | GPS Timing |
| 1 | BDS Timing |
| 2 | GLONASS Timing |

**Remark \[3\]: Date Valid Flag**

| Value | Description |
| :--- | :--- |
| 0 | Date Invalid |
| 1 | External Input Date |
| 2 | Date from Satellite |
| 3 | Date from multiple satellites (reliable) |

#### **2.7.6 NAV-CLOCK (0x01 0x11)**

**Message Structure** 27

| Header | Length (Bytes) | Identifier | Payload | Checksum |
| :---- | :---- | :---- | :---- | :---- |
| 0xBA 0xCE | 64 | 0x01 0x11 | See table below | 4 Bytes |

**Payload Content**

| Char Offset | Data Type | Name | Scale/Unit | Description |
| :---- | :---- | :---- | :---- | :---- |
| 0 | U4 | runTime | ms | Running time since boot/reset |
| 4 | R4 | freqBias | s² | Clock drift (frequency bias) |
| 8 | R4 | tAcc | 1/c² | Time accuracy (Variance) |
| 12 | R4 | fAcc | 1/c² | Frequency accuracy (Variance) |
| **Repeating Part** | **(N=0: GPS, 1: BDS, 2: GLONASS)** |  |  |  |
| `16 + 16 *` | R8 | tow | ms | Time of Week |
| `24 + 16 *` | R4 | dtUtc | s | Fractional seconds difference between Sat time and UTC |
| `28 + 16 *` | U2 | wn |  | Week Number |
| `30 + 16 *` | I1 | leaps |  | UTC Leap seconds (Integer diff between Sat time and UTC) |
| `31 + 16 *` | U1 | valid |  | Time validity flag |
| **End Repeat** | **N max is 2** |  |  |  |

#### **2.7.7 NAV-GPSINFO (0x01 0x20)**

**Message Structure** 28

| Header | Length (Bytes) | Identifier | Payload | Checksum |
| :---- | :---- | :---- | :---- | :---- |
| 0xBA 0xCE | `8 + 12 *` | 0x01 0x20 | See table below | 4 Bytes |

**Payload Content**

| Char Offset | Data Type | Name | Scale/Unit | Description |
| :---- | :---- | :---- | :---- | :---- |
| 0 | U4 | runTime | ms | Running time since boot/reset |
| 4 | U1 | numViewSv |  | Number of visible satellites (0\~32) |
| 5 | U1 | numFixSv |  | Number of satellites used for positioning |
| 6 | U1 | system |  | System Type (Remark \[1\]) |
| 7 | U1 | res |  | Reserved |
| **Repeating Part** | **(N=numViewSv)** |  |  |  |
| `8 + 12 *` | U1 | chn |  | Channel Number |
| `9 + 12 *` | U1 | svid |  | Satellite ID |
| `10 + 12 *` | U1 | flags |  | Satellite Status Mask (Remark \[2\]) |
| `11 + 12 *` | U1 | quality |  | Signal Measurement Quality (Remark \[3\]) |
| `12 + 12 *` | U1 | cno | dB-Hz | Carrier-to-Noise Ratio |
| `13 + 12 *` | I1 | elev | deg | Elevation (-90\~90) |
| `14 + 12 *` | I2 | azim | deg | Azimuth (0\~360) |
| `16 + 12 *` | R4 | prRes | m | Pseudorange Residual |

**Remark \[1\]: System Type**

| Value | Description |
| :--- | :--- |
| 0 | GPS |
| 1 | BDS |
| 2 | GLONASS |

**Remark \[2\]: Satellite Status**

| Bit | Description |
| :--- | :--- |
| B0 | 1 \= Satellite used in solution |
| B1-B3 | Reserved |
| B4 | 1 \= Satellite prediction info invalid |
| B5 | Reserved |
| B7:B6 | 00=Reserved, 01=Prediction based on Almanac, 10=Reserved, 11=Prediction based on Ephemeris |

**Remark \[3\]: Signal Measurement Quality**

| Bit | Description |
| :--- | :--- |
| BIT0 | 1 \= Pseudorange measurement prMes valid |
| BIT1 | 1 \= Carrier phase measurement cpMes valid |
| BIT2 | 1 \= Half-cycle ambiguity valid (Inverse PI correction valid) |
| BIT3 | 1 \= Half-cycle ambiguity subtracted from carrier phase |
| BIT4 | Reserved |
| BIT5 | 1 \= Carrier frequency valid |
| BIT6-7 | Reserved |

29

#### **2.7.8 NAV-BDSINFO (0x01 0x21)**

Structure and Payload identical to NAV-GPSINFO, with ID 0x01 0x2130.

#### **2.7.9 NAV-GLNINFO (0x01 0x22)**

Structure and Payload identical to NAV-GPSINFO, with ID 0x01 0x2231.

#### **2.7.10 NAV-IMUATT (0x01 0x06)**

**Message Structure** 32

| Header | Length (Bytes) | Identifier | Payload | Checksum |
| :---- | :---- | :---- | :---- | :---- |
| 0xBA 0xCE | 32 | 0x01 0x06 | See table below | 4 Bytes |

**Payload Content**

| Char Offset | Data Type | Name | Scale/Unit | Description |
| :---- | :---- | :---- | :---- | :---- |
| 0 | U4 | tow | s | Receiver GPS Time of Week (Remark \[1\]) |
| 4 | U2 | weekNum | week | Receiver GPS Week Number (Remark \[1\]) |
| 6 | U1 | flag |  | Attitude Valid Flag (Remark \[2\]) |
| 7 | U1 | res |  | Reserved |
| 8 | I4 | roll | 1e-5 deg | Roll Angle |
| 12 | I4 | pitch | 1e-5 deg | Pitch Angle |
| 16 | I4 | heading | 1e-5 deg | Heading Angle |
| 20 | U4 | rollAcc | 1e-5 deg | Roll Accuracy |
| 24 | U4 | pitchAcc | 1e-5 deg | Pitch Accuracy |
| 28 | U4 | headingAcc | 1e-5 deg | Heading Accuracy |

**Remark \[1\]:** tow/wn meaning refer to RXM-MEASX.

**Remark \[2\]:** 0x01 \= Attitude Valid; 0xFF \= Attitude Invalid.

### **2.8 TIM (0x02)**

#### **2.8.1 TIM-TP (0x02 0x00)**

**Message Structure** 33

| Header | Length (Bytes) | Identifier | Payload | Checksum |
| :---- | :---- | :---- | :---- | :---- |
| 0xBA 0xCE | 24 | 0x02 0x00 | See table below | 4 Bytes |

**Payload Content**

| Char Offset | Data Type | Name | Scale/Unit | Description |
| :---- | :---- | :---- | :---- | :---- |
| 0 | U4 | runTime | ms | Running time since boot/reset |
| 4 | R4 | qErr | s | Quantization error of next time pulse |
| 8 | R8 | tow | s | Time of week of next time pulse |
| 16 | U2 | wn |  | Week number of next time pulse |
| 18 | U1 | refTime |  | Reference Time (Remark \[1\]) |
| 19 | U1 | utcValid |  | Valid Flag (Remark \[2\]) |
| 20 | U4 | res |  | Reserved |

**Remark \[1\]: Reference Time**

| Bit | Description |
| :--- | :--- |
| B3:B0 | 0=GPS, 1=BDS, 2=GLN |
| B7:B4 | 0=Base is UTC, 1=Base is GNSS |

**Remark \[2\]: UTC Parameter Valid Flag**

| Value | Description |
| :--- | :--- |
| 0 | Missing |
| 1 | Reserved |
| 2 | Expired |
| 3 | Valid |

### **2.9 RXM (0x03)**

#### **2.9.1 RXM-MEASX (0x03 0x10)**

**Message Structure** 34

| Header | Length (Bytes) | Identifier | Payload | Checksum |
| :---- | :---- | :---- | :---- | :---- |
| 0xBA 0xCE | `16 + 32 *` | 0x03 0x10 | See table below | 4 Bytes |

**Payload Content**

| Char Offset | Data Type | Name | Scale/Unit | Description |
| :---- | :---- | :---- | :---- | :---- |
| 0 | R8 | rcvTow | s | Receiver GPS Time of Week (Remark \[1\]) |
| 8 | I2 | wn | week | Receiver GPS Week Number |
| 10 | I1 | leaps | s | UTC Leap Seconds (Remark \[2\]) |
| 11 | U1 | numMeas |  | Number of measurements (0\~32) |
| 12 | U1 | recStat |  | Receiver Status (Remark \[3\]) |
| 13 | U1 | res1 |  | Reserved |
| 14 | U1 | res2 |  | Reserved |
| 15 | U1 | res3 |  | Reserved |
| **Repeating Part** | **(N=numMeas)** |  |  |  |
| `16 + 32 *` | R8 | prMes | m | Pseudorange measurement. GLONASS IFB compensated. |
| `24 + 32 *` | R8 | cpMes | cycles | Carrier Phase measurement (Remark \[4\]) |
| `32 + 32 *` | R4 | doMes | Hz | Doppler measurement (Approaching \+) |
| `36 + 32 *` | U1 | gnssid |  | 0=GPS, 1=BDS, 2=GLONASS |
| `37 + 32 *` | U1 | svid |  | Satellite ID |
| `38 + 32 *` | U1 | res4 |  | Reserved |
| `39 + 32 *` | I1 | freqid |  | Frequency ID (Offset 8\) for GLONASS. \[1,14\] \-\> \[-7, \+6\] |
| `40 + 32 *` | U2 | locktime | ms | Carrier phase lock time (Max 65535\) |
| `42 + 32 *` | U1 | cn0 | dB-Hz | Carrier-to-Noise Ratio |
| `43 + 32 *` | U1 | res5 |  | Reserved |
| `44 + 32 *` | U1 | res6 |  | Reserved |
| `45 + 32 *` | U1 | res7 |  | Reserved |
| `46 + 32 *` | U1 | trkStat |  | Satellite Tracking Status (Remark \[5\]) |
| `47 + 32 *` | U1 | res8 |  | Reserved |

**Remark \[1\]: rcvTow** Receiver time is aligned to GPS time system. Use rcvTow, wn, leaps to convert. For GLONASS only mode, rcvTow \- leaps \= UTC (ignoring recStat valid flag)35.

**Remark \[2\]: leaps**

Difference between GPS and UTC. Validity indicated in recStat.

**Remark \[3\]: recStat**

| Bit | Description |
| :--- | :--- |
| BIT0 | 1 \= leaps valid |
| BIT1 | 1 \= Clock reset occurred (integer ms jump) |

**Remark \[4\]: cpMes**

Carrier phase initialized with approximate integer ambiguity to match pseudorange. Clock reset affects both prMes and cpMes.

**Remark \[5\]: trkStat**

| Bit | Description |
| :--- | :--- |
| BIT0 | 1 \= prMes valid |
| BIT1 | 1 \= cpMes valid |
| BIT2 | 1 \= Half-cycle ambiguity valid |
| BIT3 | 1 \= Half-cycle ambiguity subtracted |

#### **2.9.2 RXM-SVPOS (0x03 0x11)**

**Message Structure** 36

| Header | Length (Bytes) | Identifier | Payload | Checksum |
| :---- | :---- | :---- | :---- | :---- |
| 0xBA 0xCE | `16 + 48 *` | 0x03 0x11 | See table below | 4 Bytes |

**Payload Content**

| Char Offset | Data Type | Name | Scale/Unit | Description |
| :---- | :---- | :---- | :---- | :---- |
| 0 | R8 | rcvTow | s | Receiver GPS Time of Week |
| 8 | I2 | wn | week | Receiver GPS Week Number |
| 10 | U1 | numMeas |  | Number of measurements |
| 11 | U1 | res1 |  | Reserved |
| 12 | U4 | res2 |  | Reserved |
| **Repeating Part** | **(N=numMeas)** |  |  |  |
| `16 + 48 *` | R8 | X | m | Satellite Coordinate |
| `24 + 48 *` | R8 | Y | m | Satellite Coordinate |
| `32 + 48 *` | R8 | Z | m | Satellite Coordinate |
| `40 + 48 *` | R4 | svdt | m | Satellite Clock Bias |
| `44 + 48 *` | R4 | svdf | m/s | Satellite Frequency Bias |
| `48 + 48 *` | R4 | tropDelay | m | Tropospheric Delay |
| `52 + 48 *` | R4 | ionoDelay | m | Ionospheric Delay |
| `56 + 48 *` | U1 | svid |  | Satellite ID |
| `57 + 48 *` | I1 | glnFreqid |  | GLONASS Frequency ID |
| `58 + 48 *` | U1 | gnssid |  | 0=GPS, 1=BDS, 2=GLN |
| `59 + 48 *` | U1 | res3 |  | Reserved |
| `60 + 48 *` | U4 | res4 |  | Reserved |

#### **2.9.3 RXM-SENSOR (0x03 0x07)**

**Message Structure** 37

| Header | Length (Bytes) | Identifier | Payload | Checksum |
| :---- | :---- | :---- | :---- | :---- |
| 0xBA 0xCE | `16 + 16 *` | 0x03 0x07 | See table below | 4 Bytes |

**Payload Content**

| Char Offset | Data Type | Name | Scale/Unit | Description |
| :---- | :---- | :---- | :---- | :---- |
| 0 | R8 | rcvTow | s | Receiver GPS Time of Week |
| 8 | I2 | wn | week | Receiver GPS Week Number |
| 10 | I1 | leaps | s | Current GPS Leap Seconds |
| 11 | U1 | numMeas |  | Number of measurements (Remark \[2\]) |
| 12 | U1 | recStat |  | Receiver Status |
| 13 | U1 | timeSrc |  | 0=GPS, 1=BDS |
| 14 | U1 | rcvrId |  | 0 |
| 15 | U1 | res |  | Reserved |
| **Repeating Part** | **(N=numMeas)** |  |  |  |
| `16 + 16 *` | I2 | accX | 1g/16384 | Accel X (-2g\~+2g) |
| `18 + 16 *` | I2 | accY | 1g/16384 | Accel Y |
| `20 + 16 *` | I2 | accZ | 1g/16384 | Accel Z |
| `22 + 16 *` | I2 | gyroX | 250/32768 | Gyro X (-250\~+250 deg/s) |
| `24 + 16 *` | I2 | gyroY | 250/32768 | Gyro Y |
| `26 + 16 *` | I2 | gyroZ | 250/32768 | Gyro Z |
| `28 + 16 *` | I2 | temp | 1/326.8 | Temperature |
| `30 + 16 *` | I2 | res |  | Reserved |

**Remark \[2\]:** numMeas depends on CFG-MSG rate. If rate=1/2/5/10/25/50, outputs that many samples.

### **2.10 ACK (0x05)**

#### **2.10.1 ACK-NACK (0x05 0x00)**

**Message Structure** 38

| Header | Length (Bytes) | Identifier | Payload | Checksum |
| :---- | :---- | :---- | :---- | :---- |
| 0xBA 0xCE | 4 | 0x05 0x00 | See table below | 4 Bytes |

**Payload Content**

| Offset | Type | Name | Description |
| :--- | :--- | :--- | :--- |
| 0 | U1 | clsID | Class ID of NACK'd message |
| 1 | U1 | msgID | Msg ID of NACK'd message |
| 2 | U2 | res | Reserved |

#### **2.10.2 ACK-ACK (0x05 0x01)**

**Message Structure** 39

| Header | Length (Bytes) | Identifier | Payload | Checksum |
| :---- | :---- | :---- | :---- | :---- |
| 0xBA 0xCE | 4 | 0x05 0x01 | See table below | 4 Bytes |

**Payload Content**

| Offset | Type | Name | Description |
| :--- | :--- | :--- | :--- |
| 0 | U1 | clsID | Class ID of ACK'd message |
| 1 | U1 | msgID | Msg ID of ACK'd message |
| 2 | U2 | res | Reserved |

### **2.11 CFG (0x06)**

#### **2.11.1 CFG-PRT (0x06 0x00)**

**Query Message:** Length \= 0\. 40**Set Message:** Length \= 8\. 41

**Payload Content (Set)**

| Offset | Type | Name | Description |
| :---- | :---- | :---- | :---- |
| 0 | U1 | portID | Port ID (0=UART0, 1=UART1, 0xFF=Current) |
| 1 | U1 | protoMask | Protocol Mask (Remark \[1\]) |
| 2 | U2 | mode | UART Mode Mask (Remark \[2\]) |
| 4 | U4 | baudRate | Baud Rate (bps) |

**Remark \[1\]: Protocol Mask**

| Bit | Description |
| :--- | :--- |
| B0 | 1 \= Binary Input |
| B1 | 1 \= Text Input |
| B4 | 1 \= Binary Output |
| B5 | 1 \= Text Output |

**Remark \[2\]: UART Mode**

| Bit | Value | Description |
| :--- | :--- | :--- |
| \[7:6\] | 00 | 5 bits |
| | 01 | 6 bits |
| | 10 | 7 bits |
| | 11 | 8 bits |
| \[11:9\] | 10x | No Parity |
| | 001 | Odd Parity |
| | 000 | Even Parity |
| | 00 | 1 Stop Bit |
| | 01 | 1.5 Stop Bits |
| | 10 | 2 Stop Bits |

#### **2.11.2 CFG-MSG (0x06 0x01)**

**Query Message:** Length \= 0\. 42**Set Message:** Length \= 4\. 43

**Payload Content (Set)**

| Offset | Type | Name | Description |
| :---- | :---- | :---- | :---- |
| 0 | U1 | clsID | Class ID |
| 1 | U1 | msgID | Message ID |
| 2 | U2 | rate | Output Frequency (Remark \[1\]) |

**Remark \[1\]: Output Frequency**

| Value | Description |
| :--- | :--- |
| 0 | No Output |
| 1 | Once per fix |
| N | Once per N fixes |
| 0xFFFF | Output immediately once |

Special Case: For RXM\_SENSOR (0x03 0x07), rate sets samples per second.

#### **2.11.3 CFG-RST (0x06 0x02)**

**Message Structure** 44

| Header | Length (Bytes) | Identifier | Payload | Checksum |
| :---- | :---- | :---- | :---- | :---- |
| 0xBA 0xCE | 4 | 0x06 0x02 | See table below | 4 Bytes |

**Payload Content**

| Offset | Type | Name | Description |
| :---- | :---- | :---- | :---- |
| 0 | U2 | navBbrMask | BBR Clear Mask (Remark \[1\]) |
| 2 | U1 | resetMode | Reset Mode (Remark \[2\]) |
| 3 | U1 | startMode | Start Mode (Remark \[3\]) |

**Remark \[1\]: BBR Mask**

| Bit | Description | Bit | Description |
| :--- | :--- | :--- | :--- |
| B0 | Ephemeris | B5 | Clock Drift |
| B1 | Almanac | B6 | Osc Parameters |
| B2 | Health | B7 | UTC Params |
| B3 | Ionosphere | B8 | RTC |
| B4 | Position | B9 | Config |

**Remark \[2\]: Reset Mode**

| Value | Description |
| :--- | :--- |
| 0 | Immediate Hardware Reset |
| 1 | Controlled Software Reset |
| 2 | Controlled Software Reset (GPS Only) |
| 4 | Hardware Reset after Shutdown |

**Remark \[3\]: Start Mode**

| Value | Description |
| :--- | :--- |
| 0 | Hot Start |
| 1 | Warm Start |
| 2 | Cold Start |
| 3 | Factory Start |

#### **2.11.4 CFG-TP (0x06 0x03)**

**Query Message:** Length \= 0\. 45**Set Message:** Length \= 16\. 46

**Payload Content (Set)**

| Offset | Type | Name | Unit | Description |
| :---- | :---- | :---- | :---- | :---- |
| 0 | U4 | interval | us | Pulse Interval |
| 4 | U4 | width | us | Pulse Width |
| 8 | U1 | enable |  | Enable Flag (0=Off, 1=On, 2=Auto Maintain, 3=Fix Only) |
| 9 | I1 | polar |  | Polarity (0=Rising, 1=Falling) |
| 10 | U1 | timeRef |  | 0=UTC, 1=Satellite Time |
| 11 | U1 | timeSource |  | 0=GPS, 1=BDS, 2=GLN, 4=BDS(Main), 5=GPS(Main), 6=GLN(Main) |
| 12 | R4 | userDelay | s | User Delay |

#### **2.11.5 CFG-RATE (0x06 0x04)**

**Query Message:** Length \= 0\. 47**Set Message:** Length \= 4\. 48

**Payload Content (Set)**

| Offset | Type | Name | Unit | Description |
| :---- | :---- | :---- | :---- | :---- |
| 0 | U2 | interval | ms | Interval between fixes |
| 2 | U2 | res |  | Reserved |

#### **2.11.6 CFG-CFG (0x06 0x05)**

**Message Structure** 49

| Header | Length (Bytes) | Identifier | Payload | Checksum |
| :---- | :---- | :---- | :---- | :---- |
| 0xBA 0xCE | 4 | 0x06 0x05 | See table below | 4 Bytes |

**Payload Content**

| Offset | Type | Name | Description |
| :---- | :---- | :---- | :---- |
| 0 | U2 | mask | Config Mask (Remark \[1\]) |
| 2 | U1 | mode | Action Mode (Remark \[2\]) |
| 3 | U1 | res | Reserved |

**Remark \[1\]: Mask**

| Bit | Description |
| :--- | :--- |
| B0 | Port (CFG-PRT) |
| B1 | Msg (CFG-MSG) |
| B2 | INF (CFG-INF) |
| B3 | Rate (CFG-RATE/TMODE) |
| B4 | TP (CFG-TP) |
| B5 | Group Delay (CFG-GROUP) |

**Remark \[2\]: Mode**

0=Clear, 1=Save, 2=Load.

#### **2.11.7 CFG-TMODE (0x06 0x06)**

**Query Message:** Length \= 0\. 50**Set Message:** Length \= 40\. 51

**Payload Content (Set)**

| Offset | Type | Name | Unit | Description |
| :---- | :---- | :---- | :---- | :---- |
| 0 | U4 | mode |  | Timing Mode (0=Auto, 1=Survey-In, 2=Fixed) |
| 4 | R8 | fixedPosX | m | ECEF X |
| 12 | R8 | fixedPosY | m | ECEF Y |
| 20 | R8 | fixedPosZ | m | ECEF Z |
| 28 | R4 | fixedPosVar | m² | Position Variance |
| 32 | U4 | svinMinDur | s | Min Duration for Survey-In |
| 36 | R4 | svinVarLimit | m² | Var Limit for Survey-In |

#### **2.11.8 CFG-NAVX (0x06 0x07)**

**Query Message:** Length \= 0\. 52**Set Message:** Length \= 44\. 53

**Payload Content (Set)**

| Offset | Type | Name | Unit | Description |
| :---- | :---- | :---- | :---- | :---- |
| 0 | U4 | mask | | Parameter Mask; only parameters with corresponding bit set are applied (Remark \[1\]) |
| 4 | U1 | dyModel | | Dynamic Model (Remark \[2\]) |
| 5 | U1 | fixMode | | Fix Mode (Remark \[3\]) |
| 6 | U1 | minSVs | | Min satellites for fix |
| 7 | U1 | maxSVs | | Max satellites for fix |
| 8 | U1 | minCNO | dB-Hz | Min satellite CNO for fix |
| 9 | U1 | res1 | | Reserved |
| 10 | U1 | iniFix3D | | Initial fix must be 3D (0/1) |
| 11 | I1 | minElev | ° | Min satellite elevation for fix |
| 12 | U1 | drLimit | s | Max DR time without satellite signal |
| 13 | U1 | navSystem | | Navigation system enable (Remark \[4\]) |
| 14 | U2 | wnRollOver | | GPS week rollover count |
| 16 | R4 | fixedAlt | m | Fixed altitude for 2D fix |
| 20 | R4 | fixedAltVar | m² | Fixed altitude variance for 2D fix |
| 24 | R4 | pDop | | Max position DOP |
| 28 | R4 | tDop | | Max time DOP |
| 32 | R4 | pAcc | m² | Max position accuracy |
| 36 | R4 | tAcc | m² | Max time accuracy |
| 40 | R4 | staticHoldTh | m/s | Static hold threshold |

**Remark \[1\]: Parameter Mask**

| Bit | Description |
| :--- | :--- |
| B0 | Apply dynamic model setting |
| B1 | Apply fix mode setting |
| B2 | Apply min/max satellite count settings |
| B3 | Apply min CNO setting |
| B4 | Reserved |
| B5 | Apply initial 3D fix setting |
| B6 | Apply min elevation setting |
| B7 | Apply DR limit setting |
| B8 | Apply navigation system enable |
| B9 | Apply GPS week rollover setting |
| B10 | Apply altitude assist |
| B11 | Apply position DOP limit |
| B12 | Apply time DOP limit |
| B13 | Apply static hold setting |

**Remark \[2\]: Dynamic Model**

| Value | Description |
| :--- | :--- |
| 0 | Portable |
| 1 | Stationary |
| 2 | Pedestrian |
| 3 | Automotive |
| 4 | Marine |
| 5 | Airborne <1g |
| 6 | Airborne <2g |
| 7 | Airborne <4g |

**Remark \[3\]: Fix Mode**

| Value | Description |
| :--- | :--- |
| 0 | Reserved |
| 1 | 2D fix |
| 2 | 3D fix |
| 3 | Auto 2D/3D |

**Remark \[4\]: Navigation System Enable**

| Bit | Description |
| :--- | :--- |
| B0 | 1=GPS enabled |
| B1 | 1=BDS enabled |
| B2 | 1=GLONASS enabled |

#### **2.11.9 CFG-GROUP (0x06 0x08)**

**Query Message:** Length \= 0\. 54**Set Message:** Length \= 56\. 55

**Payload:** groupDelay (R4\[14\]) \- GLONASS group delays in meters.

#### **2.11.10 CFG-INS (0x06 0x10)**

**Query Message:** Length \= 0\. 56**Set Message:** Length \= 4\. 57

**Payload:**

* 0: attMode (U2) \- Installation mode (0=Front, 1=Right, 2=Rear, 3=Left, 9=Auto).  
* 2: ramStart (U2) \- 1=Enable DR on backup power, 0=Disable. 58

### **2.12 MSG (0x08)**

#### **2.12.1 MSG-BDSUTC (0x08 0x00)**

**Payload Content** (Length 20\) 59

| Offset | Type | Name | Unit | Description |
| :--- | :--- | :--- | :--- | :--- |
| 0 | U4 | res1 | | Reserved |
| 4 | I4 | a0UTC | s | BDT clock bias (2⁻³⁰) |
| 8 | I4 | a1UTC | s/s | BDT clock rate (2⁻⁵⁰) |
| 12 | I1 | dtls | s | Delta UTC before leap second |
| 13 | I1 | dtlsf | s | Delta UTC after leap second |
| 14 | U1 | res2 | | Reserved |
| 15 | U1 | res3 | | Reserved |
| 16 | U1 | wnlsf | week | Week of new leap second |
| 17 | U1 | dn | day | Day of new leap second |
| 18 | I1 | valid | | Validity (0=Invalid, 1=Unhealthy, 2=Expired, 3=Valid) |
| 19 | U1 | res4 | | Reserved |

#### **2.12.2 MSG-BDSION (0x08 0x01)**

**Payload Content** (Length 16\) 60

| Offset | Type | Name | Description |
| :--- | :--- | :--- | :--- |
| 0 | U4 | res1 | Reserved |
| 4 | I1 | alpha0 | Ionosphere Param (2⁻³⁰) |
| 5 | I1 | alpha1 | Ionosphere Param (2⁻²⁷) |
| 6 | I1 | alpha2 | Ionosphere Param (2⁻²⁴) |
| 7 | I1 | alpha3 | Ionosphere Param (2⁻²⁴) |
| 8 | I1 | beta0 | Ionosphere Param (2¹¹) |
| 9 | I1 | beta1 | Ionosphere Param (2¹⁴) |
| 10 | I1 | beta2 | Ionosphere Param (2¹⁶) |
| 11 | I1 | beta3 | Ionosphere Param (2¹⁶) |
| 12 | U1 | valid | Validity |
| 13 | U1 | res2 | Reserved |
| 14 | U2 | res3 | Reserved |

#### **2.12.3 MSG-BDSEPH (0x08 0x02)**

**Payload Content** (Length 92\) 61 Includes: sqra, es, omega, M0, i0, Omega0, OmegaDot, dn, IDOT, Cuc, Cus, Crc, Crs, Cic, Cis, toe, wne, toc, af0, af1, af2, tgd, iodc, iode, ura, health, svid, valid.

#### **2.12.4 MSG-GPSUTC (0x08 0x05)**

**Payload Content** (Length 20\) 62 Similar to BDSUTC but for GPS. Includes tot, wnt.

#### **2.12.5 MSG-GPSION (0x08 0x06)**

**Payload Content** (Length 16\) 63 Identical structure to BDSION.

#### **2.12.6 MSG-GPSEPH (0x08 0x07)**

**Payload Content** (Length 72\) 64 Standard GPS Ephemeris parameters.

#### **2.12.7 MSG-GLNEPH (0x08 0x08)**

**Payload Content** (Length 68\) 65 GLONASS specific parameters: tauN, X/Y/Z, vx/vy/vz, gammaN, tk, nt, accel, dTauN, bn, tb, M, P, ft, en, p1-p4, ln, n4, svid, ni, valid.

### **2.13 MON (0x0A)**

#### **2.13.1 MON-VER (0x0A 0x04)**

**Payload Content** (Length 64\) 66

| Offset | Type | Name | Description |
| :--- | :--- | :--- | :--- |
| 0 | CH\[32\] | swVersion | Software Version String |
| 32 | CH\[32\] | hwVersion | Hardware Version String |

#### **2.13.2 MON-HW (0x0A 0x09)**

**Payload Content** (Length 56\) 67

| Offset | Type | Name | Description |
| :--- | :--- | :--- | :--- |
| 0 | U4 | noisePerMs0 | Noise Power DIF0 |
| 4 | U4 | noisePerMs1 | Noise Power DIF1 |
| 8 | U4 | noisePerMs2 | Noise Power DIF2 |
| 12 | U2 | agcData0 | AGC Data DIF0 |
| 14 | U2 | agcData1 | AGC Data DIF1 |
| 16 | U2 | agcData2 | AGC Data DIF2 |
| 20 | U1 | antStatus | Antenna Status (0=Init, 1=Unknown, 2=OK, 3=Short, 4=Open) |
| 24 | U4\[8\] | jamming | Jamming Frequencies |

### **2.14 AID (0x0B)**

#### **2.14.1 AID-INI (0x0B 0x01)**

**Payload Content** (Length 56\) 68

| Offset | Type | Name | Description |
| :--- | :--- | :--- | :--- |
| 0 | R8 | ecefXOrLat | ECEF X (m) or Latitude (deg) |
| 8 | R8 | ecefYOrLon | ECEF Y (m) or Longitude (deg) |
| 16 | R8 | ecefZOrAlt | ECEF Z (m) or Altitude (m) |
| 24 | R8 | tow | GPS TOW |
| 32 | R4 | freqBias | Clock Freq Drift (ppm) |
| 36 | R4 | pAcc | Position Accuracy |
| 40 | R4 | tAcc | Time Accuracy |
| 44 | R4 | fAcc | Frequency Accuracy |
| 52 | U2 | wn | GPS Week |
| 54 | U1 | timeSource | Time Source |
| 55 | U1 | flags | Flags (B0=PosValid, B1=TimeValid, B2=DriftValid, B4=FreqValid, B5=LLA format, B6=AltInvalid) |

#### **2.14.2 AID-HUI (0x0B 0x03)**

**Payload Content** (Length 60\) 69 Includes Health flags for GPS/BDS/GLN, UTC parameters (A0, A1, LS, LSF, TOW, WNT, WNF, DN) for GPS and BDS, Klobuchar Ionosphere parameters, and validity flags.

