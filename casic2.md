
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
| NAV-GPSINFO | 0x01 0x20 | ![][image1] | Periodic | GPS satellite information |
| NAV-BDSINFO | 0x01 0x21 | ![][image1] | Periodic | BDS satellite information |
| NAV-GLNINFO | 0x01 0x22 | ![][image1] | Periodic | GLONASS satellite information |
| **Class TIM** |  |  | **TIM** | **Time Messages** |
| TIM-TP | 0x02 0x00 | 24 | Periodic | Time pulse information |
| **Class RXM** |  |  | **RXM** | **Receiver Measurement Info** |
| RXM-MEASX | 0x03 0x10 | ![][image2] | Periodic | Raw measurement info (Pseudorange, Carrier Phase) |
| RXM-SVPOS | 0x03 0x11 | ![][image3] | Periodic | Satellite position information |
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
| 48 | R4 | pAcc | ![][image4] | Variance of 3D position estimation error |
| 52 | R4 | ecefVX | m/s | X Velocity in ECEF frame |
| 56 | R4 | ecefVY | m/s | Y Velocity in ECEF frame |
| 60 | R4 | ecefVZ | m/s | Z Velocity in ECEF frame |
| 64 | R4 | sAcc | ![][image5] | Variance of 3D velocity estimation error |
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
| 40 | R4 | hAcc | ![][image4] | Variance of horizontal position accuracy |
| 44 | R4 | vAcc | ![][image4] | Variance of vertical position accuracy |
| 48 | R4 | velN | m/s | North Velocity in ENU frame |
| 52 | R4 | velE | m/s | East Velocity in ENU frame |
| 56 | R4 | velU | m/s | Up Velocity in ENU frame |
| 60 | R4 | speed3D | m/s | 3D Speed |
| 64 | R4 | speed2D | m/s | 2D Ground Speed |
| 68 | R4 | heading | deg | Heading |
| 72 | R4 | sAcc | ![][image5] | Variance of ground speed accuracy |
| 76 | R4 | cAcc | ![][image6] | Variance of heading accuracy |

#### **2.7.5 NAV-TIMEUTC (0x01 0x10)**

**Message Structure** 26

| Header | Length (Bytes) | Identifier | Payload | Checksum |
| :---- | :---- | :---- | :---- | :---- |
| 0xBA 0xCE | 24 | 0x01 0x10 | See table below | 4 Bytes |

**Payload Content**

| Char Offset | Data Type | Name | Scale/Unit | Description |
| :---- | :---- | :---- | :---- | :---- |
| 0 | U4 | runTime | ms | Running time since boot/reset |
| 4 | R4 | tAcc | ![][image7] | Time estimation accuracy (1/c²) |
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
| 4 | R4 | freqBias | ![][image7] | Clock drift (frequency bias) |
| 8 | R4 | tAcc | ![][image8] | Time accuracy (Variance) |
| 12 | R4 | fAcc | ![][image8] | Frequency accuracy (Variance) |
| **Repeating Part** | **(N=0: GPS, 1: BDS, 2: GLONASS)** |  |  |  |
| **![][image9]** | R8 | tow | ms | Time of Week |
| ![][image10] | R4 | dtUtc | s | Fractional seconds difference between Sat time and UTC |
| ![][image11] | U2 | wn |  | Week Number |
| ![][image12] | I1 | leaps |  | UTC Leap seconds (Integer diff between Sat time and UTC) |
| ![][image13] | U1 | valid |  | Time validity flag |
| **End Repeat** | **N max is 2** |  |  |  |

#### **2.7.7 NAV-GPSINFO (0x01 0x20)**

**Message Structure** 28

| Header | Length (Bytes) | Identifier | Payload | Checksum |
| :---- | :---- | :---- | :---- | :---- |
| 0xBA 0xCE | ![][image1] | 0x01 0x20 | See table below | 4 Bytes |

**Payload Content**

| Char Offset | Data Type | Name | Scale/Unit | Description |
| :---- | :---- | :---- | :---- | :---- |
| 0 | U4 | runTime | ms | Running time since boot/reset |
| 4 | U1 | numViewSv |  | Number of visible satellites (0\~32) |
| 5 | U1 | numFixSv |  | Number of satellites used for positioning |
| 6 | U1 | system |  | System Type (Remark \[1\]) |
| 7 | U1 | res |  | Reserved |
| **Repeating Part** | **(N=numViewSv)** |  |  |  |
| **![][image1]** | U1 | chn |  | Channel Number |
| ![][image14] | U1 | svid |  | Satellite ID |
| ![][image15] | U1 | flags |  | Satellite Status Mask (Remark \[2\]) |
| ![][image16] | U1 | quality |  | Signal Measurement Quality (Remark \[3\]) |
| ![][image17] | U1 | cno | dB-Hz | Carrier-to-Noise Ratio |
| ![][image18] | I1 | elev | deg | Elevation (-90\~90) |
| ![][image19] | I2 | azim | deg | Azimuth (0\~360) |
| ![][image20] | R4 | prRes | m | Pseudorange Residual |

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
| 0xBA 0xCE | ![][image2] | 0x03 0x10 | See table below | 4 Bytes |

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
| **![][image2]** | R8 | prMes | m | Pseudorange measurement. GLONASS IFB compensated. |
| ![][image21] | R8 | cpMes | cycles | Carrier Phase measurement (Remark \[4\]) |
| ![][image22] | R4 | doMes | Hz | Doppler measurement (Approaching \+) |
| ![][image23] | U1 | gnssid |  | 0=GPS, 1=BDS, 2=GLONASS |
| ![][image24] | U1 | svid |  | Satellite ID |
| ![][image25] | U1 | res4 |  | Reserved |
| ![][image26] | I1 | freqid |  | Frequency ID (Offset 8\) for GLONASS. \[1,14\] \-\> \[-7, \+6\] |
| ![][image27] | U2 | locktime | ms | Carrier phase lock time (Max 65535\) |
| ![][image28] | U1 | cn0 | dB-Hz | Carrier-to-Noise Ratio |
| ![][image29] | U1 | res5 |  | Reserved |
| ![][image30] | U1 | res6 |  | Reserved |
| ![][image31] | U1 | res7 |  | Reserved |
| ![][image32] | U1 | trkStat |  | Satellite Tracking Status (Remark \[5\]) |
| ![][image33] | U1 | res8 |  | Reserved |

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
| 0xBA 0xCE | ![][image3] | 0x03 0x11 | See table below | 4 Bytes |

**Payload Content**

| Char Offset | Data Type | Name | Scale/Unit | Description |
| :---- | :---- | :---- | :---- | :---- |
| 0 | R8 | rcvTow | s | Receiver GPS Time of Week |
| 8 | I2 | wn | week | Receiver GPS Week Number |
| 10 | U1 | numMeas |  | Number of measurements |
| 11 | U1 | res1 |  | Reserved |
| 12 | U4 | res2 |  | Reserved |
| **Repeating Part** | **(N=numMeas)** |  |  |  |
| **![][image3]** | R8 | X | m | Satellite Coordinate |
| ![][image34] | R8 | Y | m | Satellite Coordinate |
| ![][image35] | R8 | Z | m | Satellite Coordinate |
| ![][image36] | R4 | svdt | m | Satellite Clock Bias |
| ![][image37] | R4 | svdf | m/s | Satellite Frequency Bias |
| ![][image38] | R4 | tropDelay | m | Tropospheric Delay |
| ![][image39] | R4 | ionoDelay | m | Ionospheric Delay |
| ![][image40] | U1 | svid |  | Satellite ID |
| ![][image41] | I1 | glnFreqid |  | GLONASS Frequency ID |
| ![][image42] | U1 | gnssid |  | 0=GPS, 1=BDS, 2=GLN |
| ![][image43] | U1 | res3 |  | Reserved |
| ![][image44] | U4 | res4 |  | Reserved |

#### **2.9.3 RXM-SENSOR (0x03 0x07)**

**Message Structure** 37

| Header | Length (Bytes) | Identifier | Payload | Checksum |
| :---- | :---- | :---- | :---- | :---- |
| 0xBA 0xCE | ![][image9] | 0x03 0x07 | See table below | 4 Bytes |

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
| **![][image9]** | I2 | accX | 1g/16384 | Accel X (-2g\~+2g) |
| ![][image45] | I2 | accY | 1g/16384 | Accel Y |
| ![][image46] | I2 | accZ | 1g/16384 | Accel Z |
| ![][image47] | I2 | gyroX | 250/32768 | Gyro X (-250\~+250 deg/s) |
| ![][image10] | I2 | gyroY | 250/32768 | Gyro Y |
| ![][image48] | I2 | gyroZ | 250/32768 | Gyro Z |
| ![][image11] | I2 | temp | 1/326.8 | Temperature |
| ![][image12] | I2 | res |  | Reserved |

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
| 28 | R4 | fixedPosVar | ![][image4] | Position Variance |
| 32 | U4 | svinMinDur | s | Min Duration for Survey-In |
| 36 | R4 | svinVarLimit | ![][image4] | Var Limit for Survey-In |

#### **2.11.8 CFG-NAVX (0x06 0x07)**

**Query Message:** Length \= 0\. 52**Set Message:** Length \= 44\. 53

**Payload Content (Set)**

| Offset | Type | Name | Description |
| :---- | :---- | :---- | :---- |
| 0 | U4 | mask | Parameter Mask (Remark \[1\]) |
| 4 | I1 | dyModel | Dynamic Model (0=Portable...7=Air 4g) |
| 5 | U1 | fixMode | Fix Mode (1=2D, 2=3D, 3=Auto) |
| 6 | I1 | minSVs | Min Satellites |
| 7 | I1 | maxSVs | Max Satellites |
| 8 | U1 | minCNO | Min CNO |
| 9 | U1 | res1 | Reserved |
| 10 | I1 | iniFix3D | Initial Fix must be 3D |
| 11 | I1 | minElev | Min Elevation |
| 12 | I1 | drLimit | Max DR time |
| 13 | U1 | navSystem | Nav System Mask (B0=GPS, B1=BDS, B2=GLN) |
| 14 | U2 | wnRollOver | Week Rollover |
| 16 | R4 | fixedAlt | Fixed Altitude (2D Mode) |
| 20 | R4 | fixedAltVar | Fixed Altitude Variance |
| 24 | R4 | pDop | Max PDOP |
| 28 | R4 | tDop | Max TDOP |
| 32 | R4 | pAcc | Max Position Accuracy |
| 36 | R4 | tAcc | Max Time Accuracy |
| 40 | R4 | staticHoldTh | Static Hold Threshold (m/s) |

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

**Payload Content** (Length 20\) 59 | Offset | Type | Name | Unit | Description | | :--- | :--- | :--- | :--- | :--- | | 0 | U4 | res1 | | Reserved | | 4 | I4 | a0UTC | s | BDT clock bias (![][image49]) | | 8 | I4 | a1UTC | s/s | BDT clock rate (![][image50]) | | 12 | I1 | dtls | s | Delta UTC before leap second | | 13 | I1 | dtlsf | s | Delta UTC after leap second | | 14 | U1 | res2 | | Reserved | | 15 | U1 | res3 | | Reserved | | 16 | U1 | wnlsf | week | Week of new leap second | | 17 | U1 | dn | day | Day of new leap second | | 18 | I1 | valid | | Validity (0=Invalid, 1=Unhealthy, 2=Expired, 3=Valid) | | 19 | U1 | res4 | | Reserved |

#### **2.12.2 MSG-BDSION (0x08 0x01)**

**Payload Content** (Length 16\) 60 | Offset | Type | Name | Description | | :--- | :--- | :--- | :--- | | 0 | U4 | res1 | Reserved | | 4 | I1 | alpha0 | Ionosphere Param (![][image49]) | | 5 | I1 | alpha1 | Ionosphere Param (![][image51]) | | 6 | I1 | alpha2 | Ionosphere Param (![][image52]) | | 7 | I1 | alpha3 | Ionosphere Param (![][image52]) | | 8 | I1 | beta0 | Ionosphere Param (![][image53]) | | 9 | I1 | beta1 | Ionosphere Param (![][image54]) | | 10 | I1 | beta2 | Ionosphere Param (![][image55]) | | 11 | I1 | beta3 | Ionosphere Param (![][image55]) | | 12 | U1 | valid | Validity | | 13 | U1 | res2 | Reserved | | 14 | U2 | res3 | Reserved |

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

**Payload Content** (Length 64\) 66 | Offset | Type | Name | Description | | :--- | :--- | :--- | :--- | | 0 | CH\[32\] | swVersion | Software Version String | | 32 | CH\[32\] | hwVersion | Hardware Version String |

#### **2.13.2 MON-HW (0x0A 0x09)**

**Payload Content** (Length 56\) 67 | Offset | Type | Name | Description | | :--- | :--- | :--- | :--- | | 0 | U4 | noisePerMs0 | Noise Power DIF0 | | 4 | U4 | noisePerMs1 | Noise Power DIF1 | | 8 | U4 | noisePerMs2 | Noise Power DIF2 | | 12 | U2 | agcData0 | AGC Data DIF0 | | 14 | U2 | agcData1 | AGC Data DIF1 | | 16 | U2 | agcData2 | AGC Data DIF2 | | 20 | U1 | antStatus | Antenna Status (0=Init, 1=Unknown, 2=OK, 3=Short, 4=Open) | | 24 | U4\[8\] | jamming | Jamming Frequencies |

### **2.14 AID (0x0B)**

#### **2.14.1 AID-INI (0x0B 0x01)**

**Payload Content** (Length 56\) 68 | Offset | Type | Name | Description | | :--- | :--- | :--- | :--- | | 0 | R8 | ecefXOrLat | ECEF X (m) or Latitude (deg) | | 8 | R8 | ecefYOrLon | ECEF Y (m) or Longitude (deg) | | 16 | R8 | ecefZOrAlt | ECEF Z (m) or Altitude (m) | | 24 | R8 | tow | GPS TOW | | 32 | R4 | freqBias | Clock Freq Drift (ppm) | | 36 | R4 | pAcc | Position Accuracy | | 40 | R4 | tAcc | Time Accuracy | | 44 | R4 | fAcc | Frequency Accuracy | | 52 | U2 | wn | GPS Week | | 54 | U1 | timeSource | Time Source | | 55 | U1 | flags | Flags (B0=PosValid, B1=TimeValid, B2=DriftValid, B4=FreqValid, B5=LLA format, B6=AltInvalid) |

#### **2.14.2 AID-HUI (0x0B 0x03)**

**Payload Content** (Length 60\) 69 Includes Health flags for GPS/BDS/GLN, UTC parameters (A0, A1, LS, LSF, TOW, WNT, WNF, DN) for GPS and BDS, Klobuchar Ionosphere parameters, and validity flags.

[image1]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAE4AAAAWCAYAAABud6qHAAADhElEQVR4AeyXWaiNXxiH93/+I2S4MEtIKLkgY0Ru5EJJhBCZiQwZUiRlniKkDHFhnhNFogxJKENmciOzDJlKeJ46q3bbt9lrx6bTPv2e/a5vzd/7vWs4f6aKf3l5oOi4vNyWShUdV3Rcnh7Is1l6xP1DH31hEUyD+vCr9DcDj4OykKSGZE6G+TAQykBBFRynXcvIOmsn9iYcgt5QKPnhRjHYErgLy6AcZKonGWvgCTyDpXAdGkDBpMMcbBA/D2E2nIFd0AdWwn8QozZUHguxci7/08gPdgqbpIpkroDRsAEWQHeoA5uhYHKyDtaOn0qQrls8VIEKECOjpHxMg5K6H7BG2xHsK0hSMzKrwR4IOkHiHrSEgkVdcJwhP4SB3TPCfuGSOEaeSwKTs0KfOTeIqHiRus5pOzZdb0se/GglyaymAyVuA5j8FV7SJanz3HCd3FS6HAr9IVZ/xDaIqG8kdqb+DAhy+TbiwQ98A5tNHjiW1eWnPSjf/y8TsdjQNoa6E3rDgyfWXKwHxAvs7y4/ti8/iYm+hyQ1JfMpDIDH8ADcF49jDRpMnILjKtNsNcyCKfAOHGQH1klhElWd3BoZ2Jd7XGa+z+Gr0yQnfS963fMm0JNz3oTNpmsUDAfrGq3eHk7zfA58Z0ycguM20sxNdiHWk6o51tO1KzbblUTnLKY8k2Hk2S4z3+fGlMXoW47zQ+ylszHgnDFZ9YmSbTAeXKrOYwvpmWD0YeKk42rRpBusgqCbqVTKpXuHjNaQpNdkemH22pLOPPLdvNPzQvoyZTHK5jhP+t10pCPWYVUPfmpDklwZJynwCuPJfYB0VXCLcmWRjJOO8+KZNEGX63m6ewS/Sknz+pfJuCynY/dB0AgSzhnzlT6So+NcSV6uPX29u3rhDicyVXKXjtPrOmhiRrN6PBttW7GFls5xzMzLt45cT0EL0HFHsW7wbis6xQOArK/kietNwcPOSPN+aiWXr/8pmY5Cx32mRS/oAofB02k5dj+MBJcrpiC6xCheKVx2Xj10yFXyBoNyjv1I1IRO4HbSEdsKbkMu0lFGWy51s9bRcRYavn6xOTw8B/cA7zoHSRdSnpLeybybif8lNGECRhkm5X8VRl0Sba2QA0bdhRzqfbNKcJyV3AcMeydp5L00Mw+u0MYXxJRepTvuR73lfTo6C6VaP8Nxpdph4eWKjgueiLRfAAAA//9GkiHTAAAABklEQVQDAG+3mS3wagmIAAAAAElFTkSuQmCC>

[image2]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAFYAAAAWCAYAAABaDmubAAAEW0lEQVR4AeyYWchVVRTHT9E8EBUVFQ00EBUFFQ1UFE30EEHRHEEUNFHRHM0kguKsqCiKs6Iv4oADzogPoqI+OM8IirMiiiMOv9/lbLwez/7uuZfvfPpwP/7/s9Zee5+9z11nnbXX/i5Omn+leKDp2FLcmiRNxzYdW5IHSpo2L2LvZK1PYUu4h84/YWf4GmxrXMOCX8Ku8Cfo8yDOwQtY2qV8A3kRbBMExz7Ear/BMXAdfB/G8A0dc+AOOAP2h+/BtsJtLDQVnoRj4YNwBfwIVkOnf4FhLbwOToQ+75XI0hEcawTsZbUusCV8SGcv+DIcDI9Bo6WRqB3NvY3gd24KzpyP/h28BPaFV0HxEhef6VvkKPgj/B++Ao1gRLkIjl3IMoPgYhjDFXTo1HHIDVAs4eLLMGpR68ItdY0+M/g46o3wPih8uUdRroeXQ/Ecl0ehqQpRwfDKNUk+TmWpIji2yCKvM+hmaJR4393oh6ARpINR64Jz1HVDOvgP5ANwBBTqV6P4XPuQYhoXg0WJWoHPquJYZS3+wIBaew1D8lHPj3MjcJYbuIyE38Pl8B/YCBrdSE6wmHkTkdzEpQfcAj+DAYtQnoZ+XYgKbKvM89ICTSt2G/GPqMDLYF2ox7G3pjObZz9H/wW6abVHVv8omm0C0890VnoKfgXXwBh8iVYxBxigROTCjXkVPU9CN+ftSANqPdLfjSiGmGN9kOwMl6YGc9WRVDdit6L/B2NwY3Qnz9IoyNpsmytjc1Xbv6bxGLQaMDL7oMdgdWAEvsUAKwhELkwvA+mx2nDzexddWzfkBFgYMcfmTbAzNW5MZRDmLvOt+TfYquU7NHywLO+N2M1tdBWGJZSbrhWAa2VvtELwxVvJzM52ZtoHaZtaOiB9EfJfdF/aYWRhxBybF7Gb0llDtKbN5FSqxOYaRr9RlaWfXNZm27KIW6LQ8ZZY1QNCGtB51XYd0xODdvMuauL9yjy+iNH8/QFyAOwNfWErkU/Awog5I8+xk9JZ3bxStSKsHU0HIaIrxpIufhk6yh9s2gjLXJsqe1Kp8ATp2Ddp6CxEYvppqdwyaIzOVxnsJunX+Dz6UGhZhyiGrGPNozo11IPVs6ymMQu+DQPuR7kddoKehBClws1kNyt4uNiGFObwZ1E84AxBCvO0pzPTkzafey4dloVWEKi5WIDVlKVTrZUNIuvmjtiXwcIIjvUc7adp/jSXPM4M6n5iHgdpVvAJ17ugm4X15GR0o8K3jFo6jCjTxTOsZNT+ijTH6gijLKQr7R7TH6bfNCDd3W37mzDXhCe07jVHRQYEx+ogj4l3ME5HSo+qFt/7sQUYMdZ2/TDsgu6yPyNDnkUtHTNZQQdNQRqlbkw+61LaAX+j+OXl8S/6isASa3ORgXljgmPz+mI2nWj96BHYpB4bV8vu7ltrTKzfr0rH+v8KI9bPNTb2vNgbcWxrPej41proQpznfDr2QvRHqz1T07Gt5sqzJzoNAAD//8VA3TUAAAAGSURBVAMAr5DALdBcUfYAAAAASUVORK5CYII=>

[image3]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAFYAAAAWCAYAAABaDmubAAAEKUlEQVR4AeyYZ4hUVxTHJyGNFEISSEhCOqmQXiEhCSEN8iXNLoiKiIgKNhQLiqCo2Lui2BtWVGyIIIgF1A+KvSKKDVGxYf/91rmwvnlv9s26M+uHWf7/e245c+9955177nn7cKb8VxQLlA1bFLNmMmXDlg1bJAsUado4j32dtZrAfHibwa5wAPwN1iaeYPGl8A0Yxbt09IDusx7yEVgSBMN+xGqd4Gy4D9aFSWjFwFp4Eq6GY2EdWFvozcJ/wadgZXxFYxzcBufDH+A6+DQsOoJhXewsqw2E+VCfwWHwFzgJXoN6b3W8dha/vV98wwStYRQP0TEH/gP15k3INvAMbAmLjmDYzaw0EW6BSfDIadSFKByAYiuFL0OvpVoQXipIO1f5cbqS1jacvcn4M7AyPI1vVe4oVj0YNs38f6D0ItwA/Z0bv0y9M9TAiILgHAX9IKLck7ZH/RQyivN03IJr4HdQPElhyJiLTIN2KFV116ASj0Ie7sfsFM8jp0OP1g5kd1gdeFyr8zt/8znFB3AmjMM5Oj1d7yHXQ+uetFHUjbOIRIQL7hM0PobiMYtCWIhhX85ObJxtRr0D9NLqg2wKS4VHWWgw9MUiEuFJmsKoz9gW+RncCfPBi3kXCl9DL+cTSB1qP9LnRqSDi8ZpxnmTD6TuVIqrUOixx6h4LBGx8GJ8hZEo9YJon+3n0M0HDeYejudTYqwR1Ov+RBq+DGPLqf8EkzCNgQnQLMIL+X/q9g1CLoapkWTYuAlCLDsYGTTOGm/deGSoovkfpRuL8p2EfmMbQ7EwLfyWkckwH/S44Sho1JVIUy1PmHF3PO0kXGRgCOwLfSnSPHgk7SswNZIMG+exh7KzBm/NNjO3s5WkuTyODdCJ0iMX7bPdC90k/MzAp/Aw9AXLbtTFKoqNULSgWACDM2jQED6Mu94TDOdAb95Lrx8TvoAR1E3nDCFfUk+NJGPEGdZ80Imjm/K2NRyEh1CnWBzNxH5hSfNnaVigO/M7RcgATMVo5sCLTM+7kDNyt0On0Tt/pXkTehr1dk+IOTtd6RA1rHFUo8ZtbDdTmr6YdFOtgJ+Mr1LrD/UKRMnhnl00SOvzKP6F0Zy1OX2eoBvIOPghYcjSqC+goBNdR/aD22FqBMOa33k0PVq+0S+Ywfoe5LMwoDEVvcXUpQv1ZXAo9C0jSoqGrOb+PLZ64AraeiQis4TCjwc/fHzp7tVQoRN0ZCwN/FQ2fKTRzdEJhtVAHzL6GtSQ0mP2Pm2TbUQFTD/M7cbQOg3/hu1hiLNUSwZzWPdnFuF+TQe/r7S6F5Aplv8rOEq/+zRlukQ9DUyxjqRRjNMJho0bS+rTiL59P4EN6kl6VfV7+1alc7/jxn7/sTSDiUwNEaVBdQxbUztbVFMTPYjz1KZhH0R71NieyoatMVPeO9EdAAAA//8ZL8rHAAAABklEQVQDANV0ti0DULcCAAAAAElFTkSuQmCC>

[image4]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABYAAAAWCAYAAADEtGw7AAABz0lEQVR4AdSUSyhEURzGB9kRKaSQR0ShpKSUx8KIohCKhVHskZ1sPVLySMlSyUI2kpXIqyZSisbGRmLjFWXlkd93OTN3GrNyLUzf7/84Z+a755w5M5GuP3o5aVzNGidgAOKdMm7BLA9GIQ28Thm3Y1YLDzAEOU4Zj2CmYyC5ogkRThmfYHYAUhfB55QxXpbyiW3gdtI4BcNhaIQXYxxD0wCpIEURisENmiNZKiA2QS7YFUszDXOQAR4ZR1CsQBmcQQ2sQh00wyVkwRL0gExPyZ1gNEPRCvtwDFMy1qqOaBYhDhagF/RND5ITQPOz5D4YBx/oipEsdRO1QD8yzmRwGUpB8hBuQUpWgEnwgqQP6zyf1IRDxvNMnkMl6M3aDqWlCiu6XOvfWamQoAduk8NKxmayimIP3sFID3uk0ZmSLOks36jWIKyMsW5DNu/aAbv0x7LLwAcY6Ww3ae5At0DfAWWwjLHZ8pZtWmefTm8fS6LPAa1WC0mk1v8DKVjGuIjhK9BPk2RJZ6ktb1jdV7gnHUI9jIFuCSlUxlhXq4Rp+5a1Kl32C8aNdP7lNP3QATfwo4zxM7PmilH6de2vAoV2oYe9BoZCK2McOvPLkf9n/AkAAP//0Mw0jgAAAAZJREFUAwBH/E0tDHfsYwAAAABJRU5ErkJggg==>

[image5]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADMAAAAWCAYAAABtwKSvAAADzElEQVR4AeSWR6hUSRSGnZxzYDIDE2BgMsMkswhiWogRUTC7EBVM6EoRAy7MgisT5oiYcGFAMSGKGRQDIiJmMWBO39da/aqv1fKe2i708X/v1D2n+tY9datO3RcrPUN/z0UyH/LC3oRS61UGeAPKqy/p+AKk1Dj1Zr6g53x4BUqtvgxQDcqr6nQcByk1zybzGr1mQW84D6WUM1yPAVZBeTWDji+Bz4cp0JBsMoMJ74ItUGpVZoCtcAMqoj507gc/QaztcTLvEekIY+BpqDWDTIOK6gI/mAz9oUBxMm2I7LsPpqR6nbv/CZvgUTSTHzWFjyCvOJkmeDdASm7Sf6LAV7Trw7cQ9AkNfTWwrmtMUTUgsgTuQErv4qwFNeFtyGo7jqtgHJPTOyEZB/8DV2qvdMbvLMzFWn0GYQfC9+Ca74TtABPhGxgNS+FhcolNL9LBvbSa2K/wC6yE9yGW+2wHDicZk9OYkIzl+C1cJyGWSTpwd5xHYQjshHbgQzvoSNo/Q0MYD5OgDhQsAa6DPqbh/jyAzcoKZ8UaSmAU2Odv7A+Qlc/6eeRsG5IJmZ+Lgja/5t88eBl+hykwB4I+pXEEekGQAzhzl4MjY1twPRtS+gynb7cl1mW9G2s7tWJ8VieGLvcUkvEk1uM61AYO03CGnB1Patc5rpy81r+cq5sQVJuGG/sKNqVmOIslc5yYCTTCeo/12IOQ2ls+a8FXSkjmLD9Qvn5tFje1N1wbBf6l7SG7BhvkPrJK+QURfLH9kYvTEMajWSDHcFN3w7sA/HwZgU3J1WSZzsdCMg6g8wP/JTCZPfhPQZC+21zECTrr+iwWvqH2xGO5/4qdLVavE3T+DcZCY/A8uYRNyWTi56kUkrlIbze4M0uzQH6j/Ycn+9lhMlaUeJar0M/1fQzbA+Jl6eb286VYpbNcu8/28zvlEvqLRrGq57NuI55XSEaHJfB/Gxn8kTdenPFbNhdlfO4fi4KzP4GYM43JyZK7mdY1SMkvD4uJFdM34+SZyNREZ880n2tdHIuTccaqErRyYfLaS+s7WAGx/DbyzIl9PpD36Iozu29a4Us9GO6cLDZ+Fffkyvt4hgyjnZL7yiNiYxyMk3HDnSHoWsXk5aY8lL8qazjrcRULEZerZTNca62WHsoFgxtI4H1datcTseDqQsO3hylTnMwt3J7wfl57WHL5xFSXOy0DJwbzWHK5+onjUs7fyEacjNfui4U0BsCTlAflw5ZYecey2g6ns+eQ5wzNMmWTMeI+cPkUnK4GHgOrTmqpVvSWbgH3o4Xigd/eBQAA//9ibdBAAAAABklEQVQDAH9+q8+deST9AAAAAElFTkSuQmCC>

[image6]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACAAAAAWCAYAAAChWZ5EAAAC0ElEQVR4AcSWWahNURjHN0JCSmRIMhSKzNfwIHOITG9uplCGxAtleJMhulzKnJeLV8lMSea5xIOpKBmSzCIzv99xFnufc89J2rm3/2996/vOOnt/+1vf2udWj6r4r6oS8L6TefYyJ9j/ruXc8R6U/00CtVnYENLUDC5WAo+LJdCfBa/hIxyCNDWNi+2FqFgCp1jQBtRZhxQ5yLUeQNEE/LyHA5gMJnWVFquAdxvA8B3SrgCXjNziksoS6M6nI6E+mMB1rL2ASagl3jjoAIXUjg/GQBOIqxPOdKiIJ+AFzxC0Q7tgj4OdehIbV2cc123ANofVsAjiqodTAWHNHuZebz1WHWCYBNdCAs1wvOhN7BxYCSegJsT33+q4HUeJ+/SbsAthPAR5zcM4LWAUbIGlMBjegGrNUE1cjI1WMDSFJRD0lYn7b2JMI7+wk8krWAM1wFJux66CoHlM+sEy+AaqrgOYPOaPTMD9mULoMryAIJvkBs5LUL0ZOoIXtaQyFX82ZM40Vs1neAbxm9lLX4idh4RMoCsRbXyv6xDrBfHyWzZCmWqNZjIWFsAtCPKN2QrnNJgoJqOBjFfhPSTkjUN54tn1ZZWvYBPow3wWWHpM9MQhB5vRkE+pveOQpRG2G8QfEPeXTMDSu98uNNqYYS2oKwwTweQuYJ+DlcH8ltu3Luu9w1r6cDQb4O8D+6VgAo9YMBcWg8dmF9ZmfIgtg1pgL9jBE5h7fMqx4ivVk1KKH2RCPowPtpXgW/gM5yBPVsDgNoae4JEZgT0CbcHjMxMb5Fluj+M6T47HbAe+pwWT0X1Gm85KmbDJXCKWt//EEr8FHwjchh+g3E9/s4NvTGyuu0zcDkxC9ooVCEF/zHx37A+BXBsqkBv/F99GtDJDsl/25bab+UXYCJUqzQSecgffoDbxMea+tExgEHP/p8DkK80E7AN7Zji3GQZDYTN8goL6CQAA//8Xow+sAAAABklEQVQDAHSAii03uWuRAAAAAElFTkSuQmCC>

[image7]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAA8AAAAWCAYAAAAfD8YZAAABTklEQVR4AcTTzStEURjH8UusbJRslbCTLFBYUDYmkbXI0ktJUnZKYYPyvpOXspD4A1iJhaLYWExhYaNmM03N1Kym5vubOvUs5kxnmsVMz+ecc+c+v+7ce8/URhV8ygm3c51NbKADUWi4leZlHCCOT3SFhmM0TyGFG3xhPjR8T/McclDVM+RCwwma76DqZmjDaWiY3kI1MO5jAvFywnUEDrGCZwwUC+vJjnOyE/b8HscPqMEQYvYkx9E2wwmasYgdqGYZ9KpumT/whF8bHuGLBUziHE0YheqKQVe0Lm24j4ZG6JW0MJ9hGt6yYf0Uvcdjuv+wBO0mpuJlw6+0DGIL2kF6aDOsveXCR3R84w3r6EUWaXjLhXVvL6arh3UGj/CWC6/Sob+Z7vea9S7GkIS3XPiCjmFoB60x9+MdJcuF1aQn/cPiH0Flw0EB21S9cB4AAP//e5HXEQAAAAZJREFUAwCf2jctBofWOwAAAABJRU5ErkJggg==>

[image8]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAB8AAAAWCAYAAAA4oUfxAAACE0lEQVR4AcSWSyhtURjHud1H97qPyZ3c96MQGSlGFAOlDCRFXkkGhgYYGjCTKI8BipRIFAPJiERSSsJAHjEgGSkDlPfvr5Zz9m7vffZG0f93vm9961vfZ+29zuq8inrBv5do/pn91kHTczVXQepF1Gsy2mFEPEfzGAqNgh/FkVQKX2HZqflvJsrBr/JJnAI/2iKpAjYgyjRPZKD3MIzdhgLwq2IStQ4TUVdkDMAZxJjmHxkcQzME0U+Sb+AIgqrFNF9iZS8sQxCVkDwEQVXDggXTHP9RymPVOLjpDxM6EynYaJB04D7grD+leTIFdD5OsXbp0E4Q7IZvUA9dEAt90AgrT2muHejwUMeiv4zm4QCyoQfSIB30z77F6ilEuzXXJDmu0mWRwew02KVm7wnWgnTJRxtUgkVuzS1JDoMsYjNwDeFKYqC5Max5Hbf4DbAIFrk1j7TzMqo4PfJU4tKcPiLxmOafKPoPVsEuPWLFdvRh47tt/HDDmfgbHO36HdZN+urosTrNzxK8AN2YmHupXjWe3jsmJLPzHEK6b3ex56CvkfxN/C8QriIGg+CkfYJV0ASt0Ak6G7oFC/EtMs0niSbAL1Az8R8/Hk7A6AeOCh1i3dTPhNbKtuBnQgdoHSYk0zwU8fa8dh2+Uid9jcAeuCpo81wqeV2nTPtXkOZ6LToH2pX/Dh6ZQZrrjtZPII9ywabuAAAA///1Fyj1AAAABklEQVQDAI+0U6JoQVecAAAAAElFTkSuQmCC>

[image9]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAFYAAAAWCAYAAABaDmubAAAC2klEQVR4AeyXW6hNQRzGN7klJRQhl0iieCBvokQevJB7KfEmSRFRiBQhtygicitehOKF5FEUL+R+yYNyKaWEiHN+3zkzndNu5pyZ2WutvU+t3fdb/1lrzeW/vj17Zu3ulfKTiwOlsbnYWqmUxpbG5uRATt26ZuxIxloJHWkMN7fCfpgD9VLD5mqNnYgzm+AKvIYl4NMabtyDz3AHTsJiKEpdIldrbD9c+QYHoCMt4+ZRmAVn4Q9o9qbM2su0TVE9co3O0xr7kJZn4BH41IcbMvUa8S1Ijznoy9CspRilIVG12yrXI9e20QNL1tiQ6nOpNBjug9qNJv6EzSCDCVFSH1ENIipnket6xutsr6GKWzEPN8N0MZB4CdbBU9gGKeqW0iiwTS259jBjTCZOAqmXDjHEGDvUdKx1djXljaBNazdxFTSSUnPVxvycB5kG2pw/EfUlvSHquQlh8hnrmk09TZcXiL9B0oz9SGEH+KTNZhg3q9EsqL6m8wHUjVGWuV5k4NNwFbQhLyLq2kHiDQiWz1hXB1/MxXcm2qB1Vuut1l97rX1cyIkSq2as57rWNm7VpNRcfzDqYdgDWgrEdsrH4RcEy2esaxa8N73a2WpOK02m4OvrPPeXO9BPznV9J3VjlGWuMxn4FSyFU3AM1sIzmArB8pnhSvam6VWblym2hL4ctRzYWcJpocoyV00azc7ZPME/0K9xOvEc6J2dEKZqY7WOKtHejuYvuHYXFoDVOArDYR/8hyKVR64PeAAtWTJ1EGVNor/EvfAEgmWNnUcL/TS1fmotmcK5yi+J/cFqBYVRoD8JW4i34AjoWyYUoqJy3cXTHIIkWWNl0AR6GAEyUuiv6njOv4OVXj/0bneCC19hPmwAu85SzF1F5apXrA+pT2ONjWkvE2/TQH+BtahTTJJ236SGEY2yyjViyNaqKca2tqz9eL32Lhq3h3oa27iuZJBZaWwGJrq6aAYAAP//4PQcIQAAAAZJREFUAwCgYqstuHZUcgAAAABJRU5ErkJggg==>

[image10]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAFYAAAAWCAYAAABaDmubAAAECElEQVR4AeyYR8gVVxiGJ70nJCG9JyQhgWSRBglppC4SSEI6BEIChiSiYsWOoigq9q7YFXUhFhRBERc2VNSFvetCsICoiBXL88AcGYe59WfudXF/3ud+p86Z+eac75z5b44af7l4oOHYXNwaRQ3HNhybkwdyumxyxj7AGP/DAGgJT0Ap/UqD3lAvPcvAf0IxvUhlJ+gPX0JNFBz7KqMthVtgNzQD7ffYQnqSitHwMtRSrzNYe5gF3uMv2EL6j4rlcAR8vjHYnyF3BceOZaSRMBzGwUdwHmbAI5Al2zrLs+rKKZtZTqOMNvdSdhxcWZiC+o2aofAZTIQL4OytyazVsc7S9xl0EjgLMdGJKIoWwN3wHaT1BwVbQedjqtJjVfWKonX0mwAboJDupEKnzsXuBbWRH1+Gs5ZkvtKxlxjCG12MPQZBZ+LEPbEN5nESzaCpsdWxuUwu+pqrPgprwHGex/o8HbA6GFNSrWhRKn7TJFsOao2b1jckLkLQe3FiRWyDcSa0I+PSwlStm6ruWbrjx3GTh7DToQVsga5QSrfGDd7EvgHqdn8qITg23ecrCt4Bw0PyDf9E2QFYDzeywonGOPs3N9oW3LR6Yf+CQnKz207lu+CGdxjrS9qD9VqY8pTl2PvpOgzmwb8Q9DAJ33wPbCVyszF2p3EWpMvMP1jJxWmbNfNvo1xN5eccKGfsIRLdoZCmUTEe5oCbnBPJsoHk50PZSjvWZTCb3ivBiyaXuxfvQvlZqEQ/0ti+aV4qUG5so6pJOhr33hfbYIyzxlvjbyhL2tNkBkMfMBRIN9IjoKLnTjrWN++xaxMXcXNyU/PCHlcoij7gx+PXfqw3bEi4i7Sx2fzvpLM0hULr0rjk0mXmK10R3jdDXCfv0YIwW03LFX8g+dxkr+kTUrvADx+PnR4pm5PfBm9D2UoO0JNeHrg7Y8MNfEvaDQATvcLPc/ACeB4MAy2K89WeS+neJGU5dmF8xXDvcTby+Gg4CDM6lAfri3B2fkGBE8sZ/iHpyZBcvWSLKzj2H5q1Bo8py7B+razCejzZic2SMdLyEM9M1xLH1al3ZAy6gzKf4wdskF+IT5HpB5chS2spNGTpVPcUX4wnpb6Ub4aypWNdzqPo4SbzKdalr3Xp30feHRFznVaT82RwCvs5ONNdxiRzl6HHMGL4Me69xYimnQDJL0E/YlxhfiR0pI0rawjWGYkpKVfwoJKtCjTQsd6cm5ZvP41fZdanu+v0pyn0QcTZUKtQoINeY+xnwLHF0OT/O05SFuRRyXOo/8/ww8f/e7ShMoQ5kkXlhDpYtEWRSh1bpDrXKnffXAfg4jpxCdYvSzcgkrVRPR3rObk2T1mHUerp2Do8bu2GbDg2J19fBQAA//+KeaaBAAAABklEQVQDADN7ry1gGEfDAAAAAElFTkSuQmCC>

[image11]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAFYAAAAWCAYAAABaDmubAAAEcUlEQVR4AeyYeehVRRTHX/teVFRUtFNRUEQbFW1EGxS0bxRERTsVrVSUKIKi4r4r7ooL7guiIoILoqD+obgviAhuiIr7/vk87sDleu979/rjPRXej+/3npkzc+/M78yZM2fe+aXGX00s0DBsTcxaKjUM2zBsjSxQo8/GPfYaxvgBtoM/w5thGu5F+T9sCz+CF8IzhdsZ+HNYCXfT+A90vq8g64Jg2PsZbQa8AK6BX0Pl28g4HqfSGy6BY+CzcDa8EtYLDzLQn3AEdI4fIrPwPQ2z4Fbo/9cL+QGsOYJhNVZ3RusK+8Dn4CE4DN4AxXk8RsJ34GS4AP4Ed8BvYVEML/pC1N9F3EnZnYXIxMe0dIYvwf7wMNR76+K1GlYvfZpBB8BboNjFYyK8HL4FhdvuTgpXwTj0mrviipzlm3L2S3ZbiKIfXASzcCkNGnUcch0Ui3m4GHotxdpCwx5jCCc6FbkdBuyPCldEcjfyOJwJn4JCw79BYRQsCscu+k7e/q/R8UY4HzqODuH/8xd1DYyoil/oUS1+0yUdDmqLh5YGOmIl4pORnBNJvVgvuI/6PGhZjzCEGGdRFYKhpdALBTo/H/W9DjkUGrKWIf+D1RAO44fp+BAUF/sowmDY5DuvovCgMjzEV9gVH0Sb75k5PEJ5OTzbEDIa4+yXTO536KHVEvkFzIKH3Qoan4AeeFuQLtJapN9C5IMGSva8GkUXOB5+B+P4lIor+TrSbeZ2M4S8QD0LHjbG7iT1gqTO+rVZH8rQp3n+RVHfwciDUOixmyk0g1kYQkNfaMbjIfc+ZXXtkRNgbiQN6zbw5J/LF/yoJynFMlxFDa5Rp6Ex1dITjLtmEqhS8R5aJ5bkPRl6YxtNTcK26O31kQzCOGu81SGCLi73UukIW0EdSJqzd6N+AOZG3LCuvGmXOap5rIeaHzZd8YPqxlIIk9agHagbv4y7xjOqp8DQ8QnaJN1ySZ315vQtAued7L8hUgRvjaqlE1Eh/n9HqrJw562m5MVHZzH9/JG64e4xZG7EB2jBW6ZO/yLDBN6kHAx2CeU0eJC5mnvSGuugSzOsebZDh7lblmYxhoPgHOridCH0zpdR6lh6uDtzIPX47qVaGcGw39DtV2iaYjrlbUWDeVitQi9G83gXJnPWr9DplUeR9YRxVKOmLfhKJuL/4WWGYhlexW+l1Aa62xCnwEuPIUujXk+rC2Om1JryUpgbGvYyeveAHjIvIt36ymcoexnwRKRYmsTDBNsE3cn9TX06dLJ/IOsF00LDiPHTnfIoA1vWAfy9g2oZn/G8A5oSOtcplDtBPRJRFe5gQ13VjmkdNKyT89By9ZP0VmZ7eNegboplHN6E8jdoGrIPWS9ooAcY7DaoIaVXVX/v8BKDugxTJfPQntS8+Pi7h/MNYQ51RehQGyv2qNCoYSs0pzYZo/wBxN8RTGFSO+VQevrm6NakLhrRXeXN0gOoSR8r8vLpGLbI9yv1NU+u1H5Ot51Jw57Thqs2+YZhq1noNNtPAgAA//9uenvmAAAABklEQVQDABx3yC277/yvAAAAAElFTkSuQmCC>

[image12]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAFYAAAAWCAYAAABaDmubAAAEY0lEQVR4AeyYV6gdVRSGj10siIqKigULoqKgooiIoijWB8UOFvTBgopYUVBRBHtFRUlIDySBVEgh/SEPISEF0nsIpFcCIZWU7zvMukyGU2buYU7uw7n8/15rt9n7rll77TXn5ErnrxQLdAxbilkrlY5hO4YtyQIlPTbtseewxpvwV/ghvAbWgu3v0fE9fBKeSFzJ4q/BRnC/XzDgZ/gwbAvCsJex2gR4BI6AN8LF8CWYxgNUpsGNcCj0RQxDngTbhZtY6FPo+iuRz8N6eIeO6XALnAz/h8/B0hGG/YyVwpgz0fXIU5H/wrOgsD4I5R84Ei6Ar8PH4KuwKIYUnZCM92TtRP8FNsKLdP4FH4R94UGo97bFa8Owh1j0QngdFG7iAMr58AwoHqe4HOoBiCp2UGrgV5BFcUnRCcn42cg+cC6shzPp0KijkKuhmEfhy9BrUctFGPZzlrkB6pGIivrZKHrvLqR41ALqLYguWL+X2mmwCGLtInPyjn2EgRdD9+86V6PvhZ5MDYzaFB8woln8ZkhtuKg9hylWQHERxR9wPfSoI6rwolDRk5VB63r1BdGQU5YZl+9L9uCeBqO/DxfBL2EzGPIccyvFLVCcblGEYdiY4zGZROUu+BZcDgMRa30J0ab0wlP6Tyh7Ai9NNmGcfQP9Y+il9R0y7SxUj4OX3VJa7oReeJuRvqRVSJ+FyIesYd9m2m3QbMD45EVFtQrjrko9TwsDOyZNLxuzjiz1gmybdeN6en4zvdZ+IiwNZPJ+KPTYDShfw3owFPam08zIS+5ZdNt+Q46BuZE1bEw0NfFyeJeGZ6DYbgFPgWlEPfrTferOd2NZXktnts26sY2ulrA1mb0mkSGMs8Zb42+0peUeKoZBc3RDgfyKNh1sHzI3wrD+M6ZY6YkRBkxXbPdtK73UlEE90g3HJRftIQegeAKy9Mhl26x/w/giqOWxa5MHhLcm1crRRIn/O6l2ifvRvGteQPaCf0OdawnyDpgbLuAb/JMZPsSjiFrFudWyUjGlUvUDQpkeY914NhGlXiigq1TUMuzYZMVs3Pee0EHCo5NhXcIXoXc+RIt3iQ5jxtOfeoRC1ObQsAZoj7EJ+6Zkil54D7qpVD+kmEFhTvgUMmBa5peQCXi0tUsaRzWqGUl2zWU0TIVPw8D1KObhPyHrOcEs+gxHGtW83hdjjv8D7QthbmhY35JH8G5m6bWfII2xPtw3F8fKujdj3K5+bQ1n7I8wPAS1dDzBCoYR46dx73bq6oau89ADL6NcBb2EzdPHoXsy9UjUpviWEb/DbkHDOnEKxc1wPNRLvTn9/JtPPY05VPRS281fTcQN7jS3DRrIz+8rWFFDSvfqvnbTFvAkmof+R8M26En7CBlxFrUhTLHWNRzRoDMM6xDfvob1WOuxHgHbs/Tm9LcCf3zxx5hsf966t2/esd0dpxHNy/0E9gLq7nMKz0sbtvDkFieMbnF+j55+Ig3bow3T6uY6hm3VgnXmHwMAAP//nTLPCQAAAAZJREFUAwAcM8gtzHzZswAAAABJRU5ErkJggg==>

[image13]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAFYAAAAWCAYAAABaDmubAAAD7klEQVR4AeyXaehNaRzH70yzNUvTzDQzzUwzI0u2KESSKJHkDdlLWV5YQnZRiJR9DRHZFSWhLGXJCy9E4YV9T5GdSNYsn8+/8+h03Hv/1//vXNG9fT/n93ue8yzn/s6znS8zpV8qESgFNpWwZjKlwJYCm1IEUmo2PmJ/pI9+MBuGQ1XIpS+40Qf+gY+p/+i8F+ST/2McBWZCGyiKQmD/prdd8Ao2Q204CT0grt4kpsNpWAnWwxRVdehtNGyE89AVcmkgN/bDTdgDS6ELpK4Q2DH0FIJ5EH8wfAWL4XsI+gnnAOyAympDBRtwZt2j7izIp+7cXACtwEHwHOvoLcqoDYF9Qae/QXVQPsQznF/gWwhaiGNQ72Arqz8r2MBh6q2AI5BL33HDoG7BXgR1lIsvw1GLm65CYMfSTU1YB0r/BxxH731sGgp9p9F2Wxr9A3x++6mC/xicmQYYt1wNpUR56zdFsstOvfOSyzlQv3OZB1fBDQqTitwAU2mYRluA+pXLehgCJ2A8lCeXQMvU51IP1Dde3ocQ2FDHabKbRBPoD2fhU9Rf0UO7zvbFHwluWlOw+QaLm50bc2PKueHdwPqSLmBtC1OYkoEdQLUG4GnA9WkRfj4VMurcbDw9JHEUJPNMu67n6zN5L9szfB0VWot9CsoRew1nIuSSS+FybnoycpPrjG/eHOw2KFjJwIaKHk3cHAaR0QlyKdufSpa1vg+WpBoFk3mmXdu4VSndimpfimwwrrOut66/IS9uH5FwGZyKdSmQCfgOsCfYghUC65/xiBWvGJYBjyvx/LhfSGDXUMEZkMQpl8wzPYny76Nsz3A5aiCM1iiZeR054X9HybemJZ57TTfsMvAU5OA6hd8ICpYd+AbnU8NGnIq4ZfLMqnPXSw6y/akcRVPLzvYM26Pe3Lwit8x4Jnc5CCO6LDN28UU4OluT54buCG+Ovxo8gmIKk4F1gfZc6oH9elTNdbEZvgfxVdikXB/Ni59xTRcT11GDmu0ZzvAg+6AjBNXA8RN8BtYvTMw7OkSOy5FB9Vzvi/GMP43841CwDKxvySnYlFqO2lFY11gb982FaUV2xs9eH3oYiYewCZzSrkO4RVF7erFP10/XvYak9V26fsYP6onzP7gJe073w8aZ6Ygku1xNpsRcqJAMrBX3cqkLO8FR6s7p598x0nG1I1EL3Ln9E555/RT2GEN2UWSA7PNfevMZxGf1o+YBeUHORM+hS8i4DR1gBIR1FjevPGJdyVsiz80QWIv49g2s39WOWKeA+Wnh7ptW26Fdg+i53E9gN6CQn7qNBzb1zhIdbE2kP6vkxwzsZxXI5J8pBTYZkQ+UfgMAAP//vFOFUgAAAAZJREFUAwC1Fastjg+NCgAAAABJRU5ErkJggg==>

[image14]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAE4AAAAWCAYAAABud6qHAAADjklEQVR4AeyXWchNXxiHz380ZQgXhnCBzHJBMs8XbpCUqQiFEBlClOEOZSgRF4YkIhnKEBJlTFKGDIWkRIaMGUp4Hp1V2/7OYe8T59PXOf2e/a619lprr/3uNbzn70zpV5AHSo4ryG2ZTMlxJccV6IECm0VnnOlB9LMCZkMtKC/9y4NnQFXIpeYUzoXlMBaqQFGls3xgdS5HYRwcgM9wE5pCsfQfD5oCq+AerIFqENcwCjbCU3gOq+EWNIOiKThuPU/sAuPhLDiYk9idkFb2Mz1tI+o7lsrYI+AYMGVUk5K1MBW2gKtjMLYx7ICiycH6pYfzxLvwAoLOk+gELSGNnCXO4DRtrPuRi7PtOPY15FJ7CuvBPgg6TeI+ONaizTod53LUee95eFRvs5n+WZvU2GfSumnrXaGBK2E3Nqp32YwfLZvMa3pyx20AU7h8yVfZ5v9kbTBhY/YLh7Ik9q8klQqs40zsS9tFEOTybUHGPe82Np88cLzXhEt3UL5//L0t/yk2fEwtN+O62KjaZTN1svZPNZ6uvvwcBvgBcqkNhc9gDDyBR+C+eAq7DlJLx32hlZt5I2w/UHY6wARE9z2y36k+uQYxapN3j4uXmw9fnSqJ9LPZ6543i57mwTbIJyOESdy0rrPV7ekc+UuwFFJLx9noEBdjuCXY/bAYNoB64CUHOmcl5XEmUjYQ4uXmW1GeRj9ynB/CsU6jQ09XTF4ZXu3i7kxwqToOIwbf09lHcToFx9nqMJceMAQmZDKZsMf5ZSgqozeUjIKRMZaRd/OOl5u/xr00yue4GnSyF3TEJqwaysVVgykjV8YZSg1hPLkPknZr8jR2+ZJNp+A4wxE7c0Chh94kfNhVbHkpl+P+ZzAuy4VYg3XMN03mGo8MKPqmT1x9lw5Y93NPX4N9A+5wInMruYLjDCJdXk5/WzvzupFYAOUhneNzK3mJoCM3k+8IOu4E1g3+AlaneACQLCNP3PmUvgRnWjjwXL57KEut4LittPRvi39n3C+MwkdQZnCJKZqc3YYULjtDDx1yg6f7jwaTMaYcTaIh9AFDk17YznAHkkhHOduS1M1bJzjuGDWcca75i6TbgnsIpqjylDQmMzYTY8jWjMBZhsn4r8JZl4uuVkiAs+5ygno/rBIcZyVPz+0k/CIhKCabWtdp4QtiKq6ijvtVb/mQjpy1mIqr3+G4iuutyJuVHBdxRprkVwAAAP//uaPxlwAAAAZJREFUAwAW448tkXDVJQAAAABJRU5ErkJggg==>

[image15]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAFYAAAAWCAYAAABaDmubAAADgUlEQVR4AeyYWahNURzGt+GSoYQixAMPQjyQPBCZMpcyK+SBEsUDD4hIIXPxROaEMkeSkDyZi5CxFKIMiYyR33daq87d7XX2Wjp733vr3L7f/ta01173f9ZZa+1TP6r8ZRKBSmAzCWsUVQJbCWxGEcio26QZ24lnzQKXOlOxANbCWKhJpY11IINbbRiD14NcZAPbnactgSPwFCZDkgZTeBnegNrOxY9CbgPmWb5j3UTbOfAEWsAZuAhNIHPZwDbnSR9hI7jUkIqDsANOwD2YDaNgJoTqcOgNpr3PWDUBhtN+PhyCRbAKhoJmMJatbGBv8JjdcBtcGk1FB7gCVh9IKMAz8FC1Db3BtPcZa3/a9oINYHXAJKYbz9RsYH0eMtI00sw2yYIpP4BUFYQo5Nkh/artBS76AOQkC/pWuEZRM+NptpAGpfYaqt0K+ee0Uainn7oUoXxj8q0gRFmuyzcZSD84CVbKK31NlxJoyVO1ZnxPJaARBCkksE1Nz3+MW/trEqGBNbflYvoQl/KkLyDHEjWP0kfQF97BW9DJ4hk+FbzlCqwGEu/klylIqlOVDbDSxWizaU9BHM2CeJnyLWkbItd4ivvQ6UAzcDyFD8Albc67qDwO2vwm4irbjJ8Gb7kCm9TBe1PYwLg1m7f1ttz6BBIaWJwujnKtbVSVTTohrKS3IaCjIubUV2q2gs7o+iDECvI6CX3HveUKbNIseG16jS/+mpHaGD6Z+rjtp2BaAvrKJZXrWERzbyWN1d6swGwjo6Bq3SUZlfrgBtFA594p+E7YDjqyPcT7gLdCAnve9Kqvq0kWrB1X7b6upYDqTOUKrDZbBXUcT1ewsEjLT6nj1g8aaXYOw7WXaMLoxLOPvF0KSaYrHtgqbtFAtcuTrCbtps8p0TqFFdSVq96E9uB5q9RYtU5rIrRhUHvhElyFO/AKXLpOhZYsBbU1aW3Iv/F1cB+8ZQOr92h9NV9wp9aS3rjSj3G9DmKRHqadcRKZNaC3rWP4ejgLeclnrIsZjD7wHriWAaHdXXn9TxSnSm9oW1JbORrYwJ6jvht0BAVS6McWzcjPlFndIqGyu7jOryNwLe5YbvIZ63JGo29eEsuo85GOWC99Gia1sYFNqnOVaefUbwX68UU/xrjapZVr901rU2fr/yew5fpnT5Wro9rYT00GtjbGo2xjqgS2bKGs3tE/AAAA//9siBbKAAAABklEQVQDADB4ly1ndOqPAAAAAElFTkSuQmCC>

[image16]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAFYAAAAWCAYAAABaDmubAAAC9ElEQVR4AeyXS8gOURjHh1wSEkIRCxZusSBZELktJKXIbYOFhSxYsEBECrkXK3JPlORSkkTJCrGRu5SyoKRcQqT8/m9zordzzjy933dmNvP1/33Peec8c84z/3feM2c6ZvVfEgdqY5PYmmW1sbWxiRxINKzvjh3CXMsgpg50roBBUKWKap1Ccdty5hBVNyG9nLGjmGo9nIdXsBB8Ws7BXfAMjsNAKFvWWvdS2Ep4Cb3gKtyEbpBcztgezPQJ9kBMPem8C9egrTrX4gCWWqcx9ixYDWdhLWyFGaA7mJBWztj7THMMHkJMh+iUqR+JbdWAFgew1DqJscfCbnA6nTeW5jFpcMYmnSQweMq5bzCnvgBFmg19b/zPsu55LAprSCh61pDiV8qL88/472jKB8kDppkIl8BJn9XWUqYYolPeoTt+TN7ukkdzqNJYc5HtkKgvcQPjfAVFglerOKoH8wTiB3gP2lm8Ji4Gs0LGqhDLIJY8PWy0e2hGd0HzMX3ubZn4vxxLDdod6A6cx3lPIKQzdByFi6CH3wKiju0jXgGzQsZaB7Bc1HwGU2HNDAsc19pGV7tJO4QtjDYdbkNM3+g8ADtAX4TYTPsw/ACzQsZaDNMklrxTJC7xoJ+c77i2RaSbFatBxhxkJJmqdZdmFvvippKgfe8i4hHQLkhbtqe0x4NZZRhrLqbFxJCxeiuTqXMZV2YRMi0/se3WT5J0d84k/gHtJCYTT8IvMKvZ2M6cqUK7EmNSgeovylNOKmK1ap2+zsT94QTcgjvwCN5BSPfo0JIlU/vS7gO/YSc8BrOcsXqP1k/zDWdqLRlHVPsFUa+DhIZU7HNaepP5QrwAOk/rEM1SZKl1HZXo1Xc0UcuA0NNdn3VNHC6U3tD2F2YFEpyxepsaSc5gkJFiKO3h8BmcZtMYAbojlNOPts7bTixLllo3UYx+eT420meRtlhvLYm+HGesry/1MT19U89R2fhVGnu5sqsuYeIqjS3h8qqbojY2kfd/AQAA//+KtQzRAAAABklEQVQDAMlaei1MA6yNAAAAAElFTkSuQmCC>

[image17]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAFYAAAAWCAYAAABaDmubAAACuklEQVR4AeyXOWgWQRiGV/FAFEQFBUELLURFC0UsFMWrEkFQvBorC7HQQgsVRRsFb9BKES9EG/EAEREFsVLRRkzIQSCQImkCISEJCYE8b9ghYdn5M7P77xHY8D37zT/zzcw3b2Z3Z6cH1V8mClTCZiJrEFTCVsJmpEBGw8bt2OXMdRxsto2GqyF78dOgKCttrkbYNShzDl5DCxyCOLtF5QlohvnwAb7AHMjLpkSuRth5qNINN8FmO2jYA6fgJZyBK7ALtINxXvbKK3o8uIhcx2d3LBlhfxH/GP6AzbbQsB5ugLHnYeFY6H3cEp/gCbFF5DphereiEdYl+jNBWpQ8xTHrH7sGwdzQ+zifuX3GVaxyTJvraQaq9a6h2W4+i/vNMJvhLRjTb5V/6OJJli+9NLnOCNehu3NdWJ4VemfnI2x0UAlznspekMeV1lxzPckKGmETdEEn6BTUij8CzmYTVolMNohOB/qv7ifwP9hML5ulNEbRLojW6fcCYn2snrm+YOJH8Ab0oj6IV91t/HtwNpuwkw2gE8JlgnbCN6hlB2hUYlFWWur1bKOpbuaTax+z3oVroE0jLlF+AAPgbDZha+0CTXaPGSSqnmUUg1piPCPgaAy65eLqdYQj3Nnqmet2ZtUZ/TD+IdwHHS8b8BvB2XyF1ZeORN3HDEoAF+iWTnLcUt96YBM2Sa6DJKTduRs/Ajr1bMU/hSFwtqiwM+mpRGfjo6Zn3ycqF8MT+Arf4S90QN6WRa4/WYQeWRJ1EeWFMAzX4R84mxFW3/y6NdvoqWfJBrzKTXh9uuKCs1z0ObkWr8eA0BtTvxVHdS6WV676mryTdEVG2I8MsBqWgYQUKyivgh6QXeSi3RzHBdrysrxy1RGrPemijLBJ+6fpp7dvmv6l7luksO9KrUzK5IoUNmXq5e5eCZvR/2cUAAD//49R1EQAAAAGSURBVAMA4KePLUXuuUIAAAAASUVORK5CYII=>

[image18]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAFYAAAAWCAYAAABaDmubAAADlklEQVR4AeyYR6gVVxjHbzohCSEJJBBIFskipAkqFqxYNyIIim3jyoUoKFhARVEUxS6oIIrY0Y3YEBULFhCsCPaCIIjoRhDFiuLv95iDep2Zd+b67vUJ9/H97v/MOWfOfPPNqe/TUv2vKhGoB7YqYS2V6oGtB7ZKEahSs2k99neeNQyyrC0FM2EG9IPP4UNZY752wbHpCX3QT6AmFgL7D08bD5vhGgyENJtE5ijYD6dgORyC76BWFuvrfBwaDlfhe9gB++BrqLqFwH7Lk+7BPMiyHymwp36GGszt6AroCAYbKWSbCtV+XTnG125U7wUjYSOMgWnQA+zBSHUtBPYEj1kFpyHPnlHYHoI9SBK/JFpEKrnH9mN89WO3oPJcCLYuSQxNtKoSAhvzEHv0H1RsBcFaJondiRaRIs8u0q519/LjB1BJNtijht9S6ZtEG5PRVMhbayjOtqIvd5um7oOLgAtXf9LOZW++AFlRZhtRFSuodJJ72sFWCOa16aP+5BAWY3v8/0m9LxONlqKBteEO/ByBpbATZkFzNz/iRJx06lJJptoIci9BG7gLd8CdxXV0MERbVmB1JKuRYxR0hj/BYXUe9esiqeZi8ysl5dgLyvO8/oG6RSzP19COuwN9dJRdCJkpup68lbAFXPwGoOYtQLdDtGUFNqaBp1RaDAZjA5plThc6Vo4fpjzPa+e2rLYqyXeHMJUbu8NByLOHFC4CR6EfQqZw7eh8jEZbVmDTesHftOp8+hca7EqScC76OUmXy1oyhqTgkEvLd1tE9WhL8zXcbGD8+AbVedf8vA/XlQruewehbiWXoG7ZLqKtIdqKBHYCrY5NQBrMYW7CbZjzl+lakxVYT2UGtS8OGSyk5PSTt916QiV7Z0/0BbiT6ISuAd8RibPywH7BbTr6FVpuzqXuCNzvhrLeSWIZWmioUP99Lc9X52m3gI6i1TzoAByGM3ALsuw4BU5HBvUn0h6KnqOz4RxEWwis52iH5g3uNEDuVU071D0Okl3yS+4h4XQwGZ0DnsQM6jjStbIYX/XHo++/OOU0IK7uXvtOZDdqntAWNloro0II7C7KnUN/Qw2keBhwPrWXkl1ysXLL4Qp7k4yz8B94nH2J1spifPXDO/LS8P8dMb66xfI9Y+q+UycE9p2CnIzLlLkL8Kxvr+ayInP1rejGj+GmSgLbVO+1rakaao7tfMjANsd4NJlP9cA2WSjfbugVAAAA//+iUyW/AAAABklEQVQDAJ3Cmy28CR+dAAAAAElFTkSuQmCC>

[image19]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAFYAAAAWCAYAAABaDmubAAADLUlEQVR4AeyYW8gNURTHh1wSJRSSSwghHkgKkduTlCK3lCcPknjgARElyl2UIrklXuRSkkRJKcSLkEsu5YEX5ZJryu9/vtnJtOfMmjn2TF+dr//vrL33rLP3mnVmX+ZrGzX/gmSgmdggaY2iZmKbiQ2UgUDd+p7Y/oy1FCxagNNWqEpZsU4msC0xs7BtoBS5xI5gtLVwFp7DfMhSHxwOwRAoU9ZYdxHUMngGXeESXINOEFwusV0Y6QPsBKsO4KiAMYV0ptC3osgS61T6ngkr4DSshs0wHfQEY8LKJfYuwxyF+2DREpwewQ8oql4Fv2iJdSJ9j4Yd4HQyLiyObVDjEptnkN44a4o1urYWGZuhTbqKl34AWYo1fa19RlHn2GaZVThY9xpc/1WRm9tPF2vgJzSikBvJPQIbD+fBSXWVb+mjDu3ia3riR8XlDrE1m7yJnUfPr0GBY1qN9COuI9rPIIvxajmtT2AcvId3oJPFC+xCMCstsQok2UkPGlaCNgGMWdpsdIJIoqcg2aZ6N3PPLY6+WFuu/P3U0qUncA5N2hswXp2i9QicA21+epDUtpv6RTArLbG+DtT5Bi58gzyai7O+m2RwSrvWNi79N+mEsInepsENqKcvXNwL20A/hNhI+SDkuu+0xPqeggl0rqPLK+xL0JKgM6EO3qovos2nEzTqWhJNuWSb6nlnhC9WhqxJidlHSUl1y1e9H24Kvjr36sXnMGUdKXVke0x5LJiVJ7FD6XUADIRB4Aa6TFn1oudSvt6Q0hKrtzIldTa9K1mYSMtPvePWd5z0dM7A/gadJCZhj0OuzTqZ2PZ0oEA7YrOkIOWj78iWjcZNi1Xr9BUC6gnH4DrchAfwFtJ0hwtaspRU7Sndqf+C7fAQzHKJ1XTW1NSU1loyhh5Ufor1vV3dpl1T6xNWbzN6DdY0phpcllh1HNSr70ii0TIgtLurrnuiOVN6Q9uT6ZXi4BKr6Twcn36gRApN72HUP0JSWm/70ig/of8XlLUUWGLVJqun2cd64rZIR6w3Fkefj0us71roNu2+oceorP8qE3uhsrsuYeAqE1vC7VU3RDOxgXL/BwAA//+tZz0WAAAABklEQVQDAObOhi32Qa14AAAAAElFTkSuQmCC>

[image20]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAFYAAAAWCAYAAABaDmubAAADjklEQVR4AeyXachNQRjHD9kpoQhZIgnxgeQDkS0fpMguJcoHSWTLHimyE0VkJ77IEgkh+SDEF/ueoiylRIgsv/9tJtxmzp1zuue+71v39v+dZ87MnDnPfc6cZ+ZUj8q/TCJQDmwmYY2icmDLgc0oAhkN65qxrbnXJIhTOxoXwloYDBWlQr72xbEVhqHYalAS2cB25m7z4Cg8gTHg0zQaLsNbuAA7YDSUSqG+rsehqfAYGsIpkL91sZnLBrYBd/oA6yBO42jcAgNgD3wHzd40s/YI16ZRiK/9GVg+TccehlmwHAaCZjAmW9nA3uA2u+EW+FSHBgX1OPYZSLc56GFo1lJMpGaJev/tHOJrb7p3A6UqTE4HcscommBspsYGNuQmQ+jUFK6BrmuL/QLzQQHGJJLGSHRBgs7n6KsHIEsxJ/mqQn0dAphJn0JrDV3cSvLntBBolMYcDsEMuAtLII2yXEhu4lAv0NuFyUnnKlzVIYYapk0zvqsp1zI22CQJbHMzqvLsFMpzQIvWSuxkqMzSQ9Qu5hNOymKc0sL8gJaeoMX5DVYT6ilW/xsTJl9g5Uj+CDVNhXLVN1PWjH1NeRn4pMWmBY35aBbk1+m8EX2TyOVr/vXaHWgGDqfhHvh0kIZdcAy0+I3Cqm4D9iQEyxdY1wDvTOVzY61R7lK+Vf61df/akZzIsXzae+qV22gqmrRD0IPXTuZSgVE/074JVoEehFhKeRt8hWD5AuuaBS/MqHa2mtPotyn4xtpP+3gHeuVc9doW0T1YLl/txQrMZk4UVOVdilHcg+tHB+17x2J3wlbQlu0+tgcEyxcMl7OnzahavEwxZ+pxVDqwM5rTksrlqxzQV5mCOowTBQsTKf3Ebbc0aTQ7B9H5J+ht7IPdB9qzY8KUH1jlUTla23H5Q+ouwgiw6kChJayBX1BKxfmqPH0WZ5Se9mLl9xWstoWvsD5dp0EpS0FtQlmT6Ad2NdyBYNnA6jtar6byp3JJd0ZQ+RFWn4OYnCZybAPaxizAngHNCj1liiVRiK9z8USfvl2wSgNCq7vO9Z+oLih9oW0s2MvTwQZWAepEn1agQAp9qnbk/CNYafuhvd12Kt6DVtnZWJtnKWauEF8X44XePBeLaAuRtlgvQzq6+tjAutp8dQrieRr1CaykTjGVtPqmurAqXJQmsMX6XyeKNVBlHKciA1sZ41E0n8qBLVoo/x/oDwAAAP//5tEV2gAAAAZJREFUAwD0yJ0toeqFRAAAAABJRU5ErkJggg==>

[image21]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAFYAAAAWCAYAAABaDmubAAAEY0lEQVR4AeyYV6gVVxSGJ510kpBKSC8kIYGQ3nvykIQEEkgMgZCH9A5BEkVREAV7r9gR8UEsoGJHbKioD6JiwQKCihUVK5bvO8yWc8aZe+ccnXvvw7n8/157r93XrL32PvfyqP5XiAXqhi3ErFFUN2zdsAVZoKBhyz32Zub4FXaDf8K7YWP4igadYFPjBib8EXaH/8CHYBreRNkx5sfIy2CTIBj2cWabDa+Am+APUPk5Mgv3UDEIPgqbEs47gwnPwInwCbgWtoLl0OjuYyNKnWYq0j1eiywcwbBDmGkA7AeHwjfgCTgO3g7TYFsXnFaXRzc+T6OUNq3RBWMuJf87vBK6/uuQ4h2SD+Bv0D38jewA34N6MKJYaFi99BWmGQn1BkR0MIoiv7AL/Yx8Et+i0Es0PtmacGdNvaLoFP1ug49AcZLEddyCvAaK10iegV1hwJg4800sCxUa9jQzDIcerz3IgKNx5vpYBnEXGY/YxcZW52aoqvEfPQxdY5HCvGvUew+ogDPhcqhElJC1n1JlSvIXuu9gTQib89IyuOsNYaAX48zCWAbRh8y/UE9B1IxaLxIdwbjpxIapXmR2wO9hwAoyL8FJMMCy+eR+1JXTsGJZj3/aDLwaVoVg2GSnD1E8Dw0Pq5ABX5LZBl04olkxmNlnQR3gJ+QGmAU/4v9UHoZKRCp+QbsevgB3w13Ql8Vm5NcwN9IMexO9+8LJ8GcYYFz7g4KXACI3fBoZu5PUC5I6y8bKPIO7tmdp2Arqmf2RWTB06YG+crwbstoZXoZR6WvDy09HUtcD3RSYG0nDegwm0HsRdNDy4+7gbdEfg9XgCxrbN8mHM/TGNqpywyfUSlr7AnAushXwhdAezbtwHmwIR6g0tHRG+iFkO/J+tKr2XW5Yj4vPrtUM5Bc2ljmwC0IVvUri02Urcgs0JPgmNDZb1nNQX4DRaKxL0iOX1Flu7ERoeJ9YDHseIQyEtYYK19+bgvoQvuyPKhVvoTV++8PHZ6dPSj/YOvTPwdwoN6zvO38UtKH3WSg+IbkVisdI7ocPQn/phImmxeVa36V0z40HaKmh3LBhg2IJN5bSKNoXS8V9JLb9FKmxEJHhp6Hn1nEa6Z3vI3UsXxKvkx8Fy08vxYYRDOvPQ38afkTzuXA+XAxbw+ANZCvgIlVcZdJE9DLZy1x+xJ1IYQz3NO2n4GWLiIzTPh/voKDOPS0g70XsC4JsKpahNWRpVO8UncqXUhf0a2BuaFiP80B6uMC3kR4bpYvVE7wRUVdgCSWP1iGkv2b0dI8xxUKhRznPy8yi1/rsM8ZqCL3MMEVVpP5JMk9B9yO93S1nOQpNK+AJ7lmhqaKgYQ3KXlrG2CT9VWZ9ckiNfi9Kf9JK/1+gF6EqHHOYQQNNR+qlXkyGJu8GVCV4ySb3EsqGulKjRhIdansjbTKrNWxmZcEV3r61TuHH1rAjGECP9biSbTloTsP6Tm45lrjEK2lOw17irbSs4eqGLeh7nAMAAP//W0vjIAAAAAZJREFUAwBCqcQtu5/TCAAAAABJRU5ErkJggg==>

[image22]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAFYAAAAWCAYAAABaDmubAAADPUlEQVR4AeyYWchNURTHD4lMCaE8SCghSjKEyPQkpSjDizyYolCSIeKFkqlQoozJkwwPZCx5EMKDECkphTI8kDHy+93uzul0r8651znfp67+v7PW3nfvu9dZd5991qdl1PiXSwYaic0lrVHUSGwjsTllIKevje/YDqyxELbDSugDlTSOzs1lpmJbQNFq9rGGxPYkMxfgF5yCAfAQ5kBcJn0BHU+hE5yDy9AWitJ/EWtI7GqyEpJ5E38ZtIJ90A7UBC5TYCmcgBWwCSaBOxiTSSczjf4zuCli/bN6Si8k9gfju0I/UN+5fIPO0AbUGC5DYBsEHSs7c8s2i+mRZXBsbFPEGls+nRsSu4bh/eE4KP32OO7eD1h1kctt0GJK+ly6RpFjy25qE9ZOPaE8sKhYl7PePKhJ4eZ+MttzExN147ILXsJ8CLqDMxJOQ5Bt/RteMlLrSy/vWD0CvRWfzsE60BoyKSQ2TNqPcwlGwCJ4AtVkYtby4UfQYgpVHrEu4Q4ew3B4A6/BKugZdjakVjKxi5k5FKwG3Jl78avJ6sBfdToDrCAwFWVp5Js8ibsg2Wfbc73iFyU684jVo/Ag61gZ+aKeiW/fDuxZSK1kYsNES6i7NKwAZmCTskLYSOdEuAZ/k/MNLElfJiX7bHu28VFq/ctYP7Gqx+AWrJtGNuC7wb5gUysk1puxxIpPDMeAyYv3u9huOuz33MWNnK+txFE6fQKS+Mgl+2xbwjGlqlwrr1jHs6rvmlnYA7AH3FyPsMMgtUxsb0abKL/ER5FmSR1L1yh6V7aaXlwcOw1rAJjIR7qWcsu5Wck71q8E5O6cjPUladUzFv8IWIJi0snEekC/ZbgF+yus8lwcjfMeDoPy7POvs+407LuKvQ73wAoCk7vyjvUWd+BxZFKt67vQtm7ein0AqWVi/ZV8BEcxy127Cuu55Zf7yz2nrewfiDMIPAbEN6btcGzwUa4qMlb/mtxZ692YWOde4WKCzmPdpb6Y/E+Y+7SD1uNYYlViHZ8VpaJitcR6UetNhcQ637eeiT1Ewx3rI4Cbm3z71vrlRceaOc54YjNPrnPCmTrnN+vpTZnYZp2YeoNrJLbeDFaZ/xsAAP//205rMwAAAAZJREFUAwDbkNUtA7SAKQAAAABJRU5ErkJggg==>

[image23]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAFYAAAAWCAYAAABaDmubAAAEJUlEQVR4AeyYWchVVRTHj9E8EBUVFVQ0EBUFEQ1UFE30EEFR0UAQBU2kOCLOKILirKgoirPikzjggDPig6ioD87igKA464PiiMPvdzkbD4d7r/teOMeX+/H/77XOHs5eZ5111l73uyNp/RXigZZjC3FrkrQc23JsQR4o6LbZiH2QPf6GQ2FH+AKsBce6MzgYfgnLRqytH2NYv5RfI9vAUhAc+zS7LYHX4Bz4KtwOf4F5/EfHangMLofj4Y+wLMTaaoD8hVF74MNwAdTe+5CFIzi2KzsFZ65DbwvvhGPh/TDgZ5RR8DM4GV6GRm8zUTubtc0gxtZPubE2/Y+cBTvAvvBzaAQjikVw7BW2eQy+BIUOu4TyCLwHintpdOpc5D4oNtMMgUYtoiE82dDsm5NjbP2Q6W9CUxWigumVNkl+TWWhIji2G7u8AmdAof4AitF7Bim+onkC2ue659HPQyNIB6M2BO/R0IJ0coytS5m7ASoRFWiris+lvBXbM+F32BTCw11ltbkIkTxOMwIegn/AAA8C9UdpZsJ2cBvsBZtBswdJjK0bMeg96NeFqMBrlbU2dWgKdNiIf0MF3g0bQnBsWOQnvYyLd+E/cDcMeCpVzLN/oneGHlr9kdkXwGUpqGdr3gBfolXMWQaUiKrwYN7JyDvQw/ko0oDai/S5EXHIO/Zflr0FrQZ822PQA+5KFXPVxVQ3Yg+j94G1YGnkSZ6nUZDv89q8Xute2f56tmbnqVsdGIHfcmG1g6gKU+FERqyMPPx+QLdvGHI+jEbesWGhZckmLjxVv0eK4zZwP8zC3GW+Nf9m+4Pueg3L80Um5Pu8NrcxFI1qtmYXWyH44q1kVmUHqujn6DMNDkD6ImRvdAPsAjIawbE+jCVWdmFIAxpk/wEbGKIVtYLrlTap+fN4GuN+AXn6yeX7vLYsYklNxNgaFuuYkVz4DOZd1MT1ymr8hE7Pmp+QE+BoaHDtQL4No6FjjTY39yZ+imHxQ6lyKpULU+nhlaoVYZ1rOggRXeksqIm11e2fpfG5vkHqLERi+qlXbhk0RucXTPaQ9Gv8CH0qtARFxEHHmqBPMt2C/QhSmBc/QDkNp0Cxi2Yl/A4GvIzyDBwE/dWGKBSxtpqn/SVpetJ+7V6DZZaFVjuoVbGeXtORTrWuN4ismwfSvxVGQ8f6lvwE32eVUdsFad7y5r65kALoTn6jeQ56sFlPLkI3KnzLqIUj1laf4TWseR2aBqSnu9chxTFUF/5CG153Rp1BHevwCho3XYw0Sk32/lTdwnUWRoy13Tg6T0BP2U7IkGdRC0eMrT2xok0N9qA/BpZYB2MmVpsTHOuYp56O9X8ARqyfgP156kRr3UkMmNQRTcHTt6mFLIq1lam3B1nHlm3BvLI3LHO/2+nYMp+z9L1aji3I5TcAAAD//7omFJ4AAAAGSURBVAMA77HjLcxuUn0AAAAASUVORK5CYII=>

[image24]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAFYAAAAWCAYAAABaDmubAAAD7ElEQVR4AeyYV6gVVxRAJyGkh5CEJCSQkAYhFUJIIQkR25cIioIFQQQrKiqKWLD9KIgNC4iKFfHDLqJYQfwQO3YsIIK9IvaKaz3ekWG83nvmPe4V4T72mr1PnT17zpyz73s1qf6VJQLVwJYlrElSDWw1sGWKQJmmTa/Yd7lHVxgH/eAbyMoSKlrD7/Ar/JziC+xKSYyv+vI/l1G1NEO/AhWRENjPudtaeAxL4Qc4BO0gyJsYLWEx7IJ9cCDFUOxKSIyv+uEC6YJxDN6HVbAB3oKySwjsQO4UgrkNuxe8BtPgbVC+43IWZoH1k9GyCH0OhkEecVye/qFvjK8N6dwUesJC6AsjoTG4glHllRDYB9zmIzB4qOQ+l3vwAbwByvdcDKSrwMD3oazD76E7wCXII5/m6ZzqG+Prv/R3qxqLDjK/1mhfq8uqQmAHcRcDtwCtaL+D4eq9hlaOcnGPRT2V3lj7YTPklXDvvONifF3HpDtAjaqR2zXXJPG5as2iyoXTsWiPIo3h4R7Rx70IlXzMZSKchk4Q5CDGSQji1tGZwgioi9T1IInxdScO/QXLIYhl7a1eiuAWaLMr/hcNeB1ySQhsGDQdYz38Cd3AVYoqKH5mM2l5CC9C8vjqSxyMkzdAjSooPag9An/ABTgPZhYn0G0hWrKB7c7I38BswLc9FbuQ/Eil6csydCkxNfIkz+IqyNZZdl8vNaftsb7a13PBFdiCgtkOqqC4FbpYzIw8/EwtrRtP75UQLdnAhoGmJbspeKq2QmfF/ec6lWeglDhex7J8y8BsnWXnpilaSvlqhjCc2RpBqbPgJn3cBkejfRFituMCu0NdtITA+jCe9OmBYRvQoXS9tm/zuEYE8+jjF5DFTy5bZ9m0iCHPlTy+GphJzOQzuO9iJo5XF6IBlZ41bdAzYAq4uA6j/VGEihMD+xVdvbmT+ClSrBHTKI0rXlJ8hv01hGwBs2KSx9cv8crnao42WKjE7adYunWXTq7OJmgPSTOJ/7DngikoKk4MrBv0ZbqbsJvoYybui/9gXIU5kJZwUprnpusrYcf66j7tL8lPcEr/N6G3wB4w20EVlO3Uuh0ZVPP6DymbN49B+ysTFScG1rfkJ/g3Q1y1A9DuW07um0unWDQlt7yAeyyqohLrq8/gAfsT3rkNiKe75bDF0VRU/IU2oWiPIo0G1uaNXLzpGrSr1M3ef8LspZwVfzT4efXPNlSoHOOr/7cwxSrEkEg/TbFORfZ9plsIrA2eegZ2NgVXrJ8A5jPiP2pWU3sR6iOevnUdH+trXeev97h0YOs9Wc4JVuTs/1J1f5GBfakCldfZamDzRiyy/xMAAAD//0dKF3YAAAAGSURBVAMAkU3ZLd750R8AAAAASUVORK5CYII=>

[image25]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAFYAAAAWCAYAAABaDmubAAAEM0lEQVR4AeyYaagWVRjHp4iijaiooCDao6IoWqko2iCIoA3aPkREG+0p4oKiXxT3HVzAFXHBXVFcQUVERf3ghguIqLjgvu/4+73MuQyvc1/PXJkrwiv/3zznnDln5nmfOfPMc70xqf8rJQL1wJYS1iSpB7Ye2JIiUNJlszv2Du7xC/SA/+AxyNOTDLaHbvA13ATNrVhf38GxTimfYG+AZlEI7IPcbTZchEnwDKyHbyGrV+gMhjXgvLexi8EfimkWxfrqBvkZjzbDXTAd5sGtULpCYFtxpxDMZbT/BHfiQOxtoHza42l8DjNhOfwF++FXKKqxRRek82N8fY+5H8EfMAb+hY7wAbiDMeUqBPYct7kXngB1lsMZuBtuAfUwh0fgTshqC51HoageKLognR/j61vMfQFMV5iKRlWOSfJdaks1IbCtucvTMBqU7dtpuHsPYdURDqaKBdg3QLmbzV0T7BQk3LvgsiTG1zlcdAVoMRWdrByTxN+VNmuafzj7AzRJ4cddYLW5CJPcx6E37IQfIegwjb7wFCwF21OwpgvzLM1CMrUUWpBOjvF1JXNfB/3DVGTfxhIPNTAFetod/7wNuBkKKQQ2LBpEYy68BubNTdiszG8jGXDd39gXYQNcC13J16xPPsQ2DBwDLSZXvzO6EV6FvbAHrCy2Yr+BaBmg7OTf6LwEVgM+7QG0s/qejk/yY6xp4n6s1cS72MZkxeCXvBp3QfWYffN6Y9fKjl/J1+xcqwP9/oxBqx1MrkyFQzljxePH7yvajvXEToNoVQc2LLQsWUXHr+qXWOVT7EfDoJq7LLVa0DfvDsE2JtfrWDWPs6B6zL65jVPRyvM1u9gKoQMD78NCqKXjnDQNdsb6IMSa3Q12irFohcD6YyyxsgtDGtAhx33qk2nsA2VAe9Gw5DLv3kM7T6YO34BqfOWqx+xbFuVdJ4zF+BrmGpg+dPwN5l2aieu1efjm+a3xDx83S38mublMdy/TjpaBtYTy5l7EVzEsDmXVgXQglF1pt8H4IfNpHm0YKa8R66seWB76uz6lY7AwiemnVrl1mknuzg+xfiStJHwzR9C3BMXEycCaoC3yLdh3p8vMi2/SPgjDQU3k8AVU16w/MeauPI8tW7G+mqfN/X4D9N8ScRHOrQarHUyu/KPHdGRQret9C62buzB7LUTLwPqUfAWtTd21LVlt3vLiPrlt9NUMDt3B+rAr1nrSCuIh2q7BlK5YX/XnWbx5DkwD4tfdfkhxnKop/0Iz1dWc1NhJA+u5+Ry86Sysu9Rk73/C+H8CDDXIpG6J5fgORv8Hy5AT2OZSjK/tcMYSK4+2nIuRJdb2mIl5c0JgPWeeNLDD6LhjfQVoXqZdjIwD/wZfh22q/Po2dW2sr029/lWvywb2qi9W8AJTC86/rqZfy8BeV4Eq6mw9sEUjFjn/EgAAAP//ec3RsAAAAAZJREFUAwDKs+UtDlx+mQAAAABJRU5ErkJggg==>

[image26]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAFYAAAAWCAYAAABaDmubAAAEL0lEQVR4AeyYV6hUVxSGT3onpJM8JCEJhCQkEEIKSbDriwiCYkNsYEOxIWJB0RcFsYEFUbAXEMTyYK+IiP1BVBRFBMGCBXvD8n3DbJx77txxj3hGkLn8/167nr3OmrXXXue+mlT/MrFA1bCZmDVJqoatGjYjC2T02EKPfZ89esAJcCD8DhbDN3QOghNhPfgiEKur+o1BQdkc+QqsCIJhv2K3tfAhXA5/godhe1iI1jR2wYtwNRwPJ8NKIlZXHaQ7ih2HH0L13Yh8B2aOYNgh7BSMqeH60n4dTofvQvEzxWI4Fy6A22EnOADqDYiysLSs2U8mx+jakOlNYR+ozuo4mnpjqPciskUw7H22+QT+AMU9irvwI/gWFG0o3oT7YIDecJlGR1guvih3QX5+jK7/Mfc36IlC5KAzWOlgkTWDYYey0Y9wIRTW36Oi915BCvuUdywKeJ16E1guwt7lrovRdT0P3QOViBxu5cok8b3y1ZKiP6Od4TMhvNwDVut9iOQzCuPmGWRXGHAtX3ktL4NQUb39jdARKZ/1IonRdS86/A1XwADb1ndYlKAh0GE9/lcr0JOKiEcwbFgxk8oG+BfsCY/BgJ35yqd5qfiSQqNqJCXNiqGUrmkl1G8YnZ4uJdWi6E3vUfgnPA/PQTOLE8h2MBppw/Zi5e/QbMBfexr1gEVUDA16cVjXjz6P2CNkCBlUa8DUyJs8Tb0g3WfbuF7jAXU0SumaXmJ2oAe2ZMBsB1EUhsLZjJgZefmZBdlnarmK/mgEA6UXmJbsp9NbtRVSmIo1o3ISboHLoEfuJvIC9LJD1ILrVSzN75mZ7rNtbGMoGsV0LVxshjCKjkZQvRF14gYjhsGxSH8IOZK6DnYbGY1gWF/GFKtwYQgDKhT63bgbjQbQLGEl0hAQwgTNWphPjycgTY9cus+2aRFL6kSsrj5Aw0yh4jvoBFQT1yuLsT6d3jVtkbPgVKhzHUH+AaOhYb9ltpv7EI8izRw+yJVJcikv30aaZHdBBhh/vMxmhI6MZayuqvE1he/VAqmxEInhp1S6Zcajd5rleEka5v5n4TxoCoqIg4Y1QPslZcJ+Nr/MuPgvdXNUPwioJiqqkoYD2xrU1GcdjacdMaY8F8Tqapz2S/JzdlX/zUg/aA4gzXYQRbGbXsORRvUkfkzbvHkc8hCMhob1V/II/sMqvXYw0rjlw/3lTtEW3oxbqRhL/V/BNupu6m3p5UUzc8Tq6jv4pfgLGhkGpKfLdghxDJWEX2iTSs4oMahhHd5E4aZrkHqpwd5/whykHeDl5U25hA4zAP9RowdfpV1JxOg6AoVMsYpxOGMx0JFOx0wsNicY1jFvPQ07h4YeqzdSrQG92DGPV+GnbY1JkQ1v38iptabF6FprUSU7Cg1byX3dy4xC+VLyRRr2pTRoeKmqYYMlnrN8DAAA//+cONcgAAAABklEQVQDAHrA5i1utLXJAAAAAElFTkSuQmCC>

[image27]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAFYAAAAWCAYAAABaDmubAAAEe0lEQVR4AeyYZ6gdRRiG1xK7iIqKCioq2FARsaBi7wUEFQuo+MOGigoiFhRFULGDBQuoSUiDdEJ6IYSQnkBCEhJSIZ0USEIqCXmeZQfOnbt7zp6bszf5cS7vu+/MN7M7c76d+ebbe2zS/qvEA23HVuLWJGk7tu3YijxQ0WOLVuxJjDcCXgxjXIrhbfg1fBweCZzGoK/BH+D70DkhnXAnli8zPoYeA7sFRY51Mk7k1GgW91CfCNfB/tAfNwDttgkz1gVwFDwIB8Gr4EL4PKyFTn8Vw1J4BhwOx8GTYeXIc+zNjPoWjHE8ht7wNzgYzoevwEfgS7BZ9Gv2hqz/h2hw5jTK7h7n9jvlU6BwATxAwd/RB30PfgHvgy4apFrEjj2R4b6Hf8IYj2K4EE6CAVso6OAX0WZxXrM3ZP33o2fDy6HYx2UvPBM6fyS5nct18DsY0CsrvJBppRI79nNG+wtugjEezgxbMw1i/Q4qPWAziMcue+9HdLwCunuQxLIhy9W7TQMcA2dCFUmxK70miX2zYl15l9aXYZdQ++Nu4AlXwr4wDxdlRldHVkzFuivlrLRW/tLVuHyAIYybSHIOl5/hGmhYQlLM4noLHAIDrFue4qUODSs2u+KvtQBPgE0hOLYHd/0E34FFCPHLH1bbx0PEerOO9Z7DoeFqLA/wTHgdXQKL4Ev8mMYdUEVy8SbWxfAmuBFugGYWy9DnYGkEx3ogGIM87YtuNpbZ5iTVmMHBsd3UyJM8pqsgtlk3VsbPyKu/gdFdZjbgyvRQxZQLswNX4JO0mkEguTC8/EOL2YaH39OUtf2IDoOloWOvprfb5H+0HjZnjcdlGiTUQ3uwB32KghOLeVmB3dhGU2mYQs2htxmAY1HsADMEz457sZoqIoXYSYuhxRzdFyE/w+ZL242Who69m97Xw1VwRcZPUeFWm24BroUiDv6uSA+GcHDYp5Y9qbiqYrrlYpt10yJuKYSON8Wq7RDCgM6rteuYXzBoN+5STLxfzeNdGI3fz6J/w1+hL2wReiMsDR37B739wpJ+wUjDAubkQS63QmFSrrpd1cDzKXj6FoUCmluGS3iSjvIH187jdOzC9E+VHrb2fYKKzkISw0+9dGsPnVyd96OeJS4YMx53cwiFNDWGjs3r5WGmPahlT9PlFIxTSApTHUPJv2mt+ouHiSHHj4v12XDumNsom/b9hwrjtAvhXCraJqCT4VxoBoHkYgZWQ5ZONVf2QDZv/gb7AlgasWN9m24rt8J2njIaToXCwTwZn6HyFfRrayD6LfT/CkjlcEUZLtxFrtoPGNEY69xcZSupC+2+8GuoGAakp7t1fx/mhvALzUypYce8DrFjzWFdhb5xv6/d5n7FhHtnU7B9Hmr++hBqcEe6DeMZSQeNRF2lHkyGL+eEKYVnhNlLHj9JezS+mGKtbtwtv0fs2PxeHa2enP6vwH++1EvPOt7Vuebp29lazuIJrWMNQa5Yt2u5O7upV1cc26qpDW3Vg47G5xxJxx6N/mjZnNqObZkrOz7oEAAAAP//rTvoJwAAAAZJREFUAwCpucMt6YYghgAAAABJRU5ErkJggg==>

[image28]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAFYAAAAWCAYAAABaDmubAAADxUlEQVR4AeyYWaiNaxjHv3M689DpnBPiAqFMIckQMnMjpSjDjVyYQijJEHFDmcuQoYzhSoZkpiSZwoUQyVAyZShkjPx+u/VleVtr931rr7X3vli7/+973vdd7/Cs53untX+Myn8liUA5sCUJaxSVA1sObIkiUKJu883Y3xjvADSCUD0oWJBhIPYHqG79xYBjYSlMgyaQSzXma77AGjiD9mfgrV9kDGW34B/YD8fgd6guNWCgQ/AFdkNLuAYjIFs16muuwHbCu4kQqjcF/cHPdmCnwnzoC74ITCrtSlX7W+UZJONgniU9CX6CNfAHqGL7ap+pCAP7K62XwDoI1Y2CtrAYYm3LJEZmbBpTL03lrLqfSP8PzUB95PEB/gX9x0TF9tU+UxEGdh6t18NTCHWEggugxVTobcUzisItI1NcqQnHrrRy1oczSTeH7aBMO76z96UFoI9V9XUK/YyCgpT95drTQwvYCbl0kcLOsAdimTd92kdKCj30PjOOezwmqsNjBTyA0RCrKr66rdiPq7ONCfgFUikO7M+0Wg6TIakMzCwqvwYtplrldnWUET0TxmFvQj4l9XUCHdyAjvAEHoM3i9vY4ZBYcWA9ENwvHyZuGUXeDnyrg2njqYzJKa9GnuQhzoKwzLx7Zc6OgsLx5F1l3gZcRavJ51NSX91eNtKJtw0P6qGkLVuG3QeJZWBbUdslvQWbVJ667sd9aHASKtMQPtSxkKZ5yt3b+CixvO5dora3Fcci+Z3S+PqGlm4tC7FOGplL2pf2DptYBrYXtdvBPbiTYQ5WudTOmcjCwVaSN6juZSSjyoKxlQrOqhCXXFhm3iscTfLKsbxiZVeItwF9yi5P62tPGrt/D8NugFXgC7uO7QCJZWDXUttfWOIvGHFboDgawKMLxGpIwqAOwuoAJnJJF3Ldsm1aGtPA8f3CbhtkK/R3xTOKnmesphBf39PQ2dkP6yHprac7aVez1zqSyWRgc9X0MLM8tqbd+/zFU5fMZjgBp+AyeCpjSi4Pk2eM4o+LR1jlHt6VxAvQL0xUqK/naeyWZVC9K/9H3nvzIuxVSKwwsM48l5VL4RW9HIYzoKbzcD9ujXXJiSemedtQXHI5o9wuXEXOWn1yjzUQzrK7GQ8sr6qv/pr0ppTpMp0JA+sd1gu3b9z/BdSnO3/FYCL3Xa8tuZhthWriOOP4Mg9inaUeom5fV8jHKoavXrHuxx2mtWFg07avSn1P30Lbe0Ib2E104Ix1uZKsParJwO6tPWEovic1Gdjif5ta1GM5sCV6GV8BAAD///Q1PW8AAAAGSURBVAMAWfe7LfICZRUAAAAASUVORK5CYII=>

[image29]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAFYAAAAWCAYAAABaDmubAAAEfklEQVR4AeyYV8gcVRSAx94RFRV9UFHBrqhYsPcXEQQFy4v4YENFxRBSSEhISEgPpJBCensKqaQnpJBeIT2EFAhppJBCKgn5vs0M2dzM7D+7/Lv5H/bnfHPOPXOn7Ln3nnvmvzGq/1UlAvXAViWsUVQPbD2wVYpAlW6bNWNv53lT4XEI5U0cHaEDfA03Q63lbh74K3SH/+BJSJMPcLaP+RJ9A9REsgLry/gidwVv0Yr2XzAHVsEAmA/3QK3kUR40HS7CeHgONsIPUCwG/Rcc2+BemAyz4Q6ouqQF1hn5Z8qT78fnTL0JbTAnoQfBu2CwUWXJuLJ6X+ncHDMJ5lJsn+2q6Yd9Jygfc/gc/B1j0P9CO/gUnDSo6koY2Nt4XDdwJqKukXN43oZETsTGw7EuR1Vyjfc/z+EBeBoU3+ksxn3g+6MiB/tljK6QyMjY+DHWVVVhYNvytIFwEEI5gsNc9ho6kVdjw6UZm7lV+Oy8F7ag4zMwChRtU5az96gOmAkrQI0qyKnCMYrsG5sl1T+c/QkqkuIfZ5Ce5S5jIUv2cuIYuAm4cX2DbS4r/gG4con3yNUx6HSBtnkTFT3IoRfsgZ8hkZUYb8EESMS29iIPJTCteNoZ/5IG3AplSRLYW7iqJ/wNDck7dFgIfWEKdILrIaarWTzYPeE39FbIEgexJSdNXWrMVPkD72Z4Aw7AfrCy2I7+HnJLElg3BHOQM7Khi5fQ4X14ClxWG9COLipVLI3cyUOcBaHPtrky9UaB83farjKrAWemA40rVawOfEdXmRVEaiecppfBaKsNN79vsfX1QE+C3GJgn6e3y2Q4uhxxw+jNBQZjNDpLTBe+WIgDE/psm9uy7pXmt4RazQkrAJ+FeZVYIbh3fIJ3HpSSk5w0tbgKHQhpg89BO43OLQb2I3q/ArtgR0xrtOJSW6YBljjmUzcLmgVJlp+56KGC59rDCFzOqhCXXOizbVnEJZli4C2xijsk72Hwiv0GxsHXb971nNer0/gQp/n7O7SlZB+0A7YJ/TrkFgPbn95+YYm7vpgWcEdfcEjKK9PF/7QFVRCXuYYlj/lLu5o8wc0NlD/YlUKzIMkHyuFC6/LhMZR9v0IbLFRk+ilVbp2hk7PzM7SbpJXEe9iuZn8jZj4xsGk93cz0J1rbXGpFMMRGjIHXtDgva6l4UQW4mRziOj8u9qEVB9cN1XJwmA4wT1sCuor0zcW3ANaAFQQqVZbjNR0ZVGtlP4qsmzvjXw+5JQyso+mycikc5y4zYDEojqRt04GpogtOv8QMajPsWogzynThKnLW+lxzrIFwlu2MX0K/e8cLtE0D4u5u29+Hu0HxC81KqcGOaR3CwFrDmkMdcb+vH+Eiv2JQkZuVJYc77G4c6+BFMN/53Y5ZE/H/FAZoGk9zlroxmb7W0k7EgbfESsP/dyT9SmlLLH9nqT6Z58LAZnYsOrEF2yrA5ehmR7Micfet6EIuMu0Y2KHYzliXK2bTkUoC21hvP7GxbtQU73M9A9sU49Fo71QPbKOF8uobXQIAAP//mgLHjAAAAAZJREFUAwAXEsctpWpuqgAAAABJRU5ErkJggg==>

[image30]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAFYAAAAWCAYAAABaDmubAAAEIUlEQVR4AeyYV4gVSRSGe5fNgWV32ciyOS+7i4gBFbO+iCAoGBDEBxMqKogYUBREwSxmBSPqkxgwJxAxoz6IigEDiAkDqBhR/L7htmhP37532umZebjD//epOnUq3NNVp07Pm0HpLxMPlBybiVuDoOTYkmMz8kBGw+bbse8x33r4A0xCRxrHwqrGR0zYE06Cg+DPMA6NUY7JsQ3yDVglyOdYF+NCPkxYxbe0zYG/waqE825iwmdwFfwLHoed4cvQ6T1QnIafwHVwG3wfZo44x9Zl1r6wEGZg4IIRqbAyVa8gGEK/0Jn7KPeDb8FZ8AMomvFoBf0dy5ED4WjYArppENki6th3mW4inAuT0JVGd8kjZFp8lbLjE/p9Dn+F4jEP1/Ep0vUjgoY8/oMTYIiluUKXnMxURB07itnmweswH76mwSP2urE1OjfDFoWhWP0Bl0Fh2ZDl7r2tAm6BB6ESUYb7Zc8g0DZXTBQDaO0GU+HlH1eLEf6EK2ASptM4GLpTEKmR9iJ5yozGTUTwBY+p8BLsDkMcolAProYhrFve7SOBhhWb3fH/WoDvwAohdOzb9JoC+8MkdKDxAnThiGqF4WorK/BO6IU8BfPBlziMxrtQiYhFH7QnYR14DV6FZhZnkZ1g0Qgd64VgDLqc0NO4puO9BBLMyjWZGnmTR+kuiOqsGyvLDRKj6I3OU2Y24M6cST0fDF3uwHYYeDcgYmF4WUCL2YaXnxtJ3WR0a2HR0LF/Y+0xWYxMgoOPwOABrAjaY2zfKH/Joze20VQ0TKEOY20G4FwUX4EZgndHc7Q7YRLu0WhoGYf0RciRlH1pFfrdOrYpHf+HHvFzSKkDKQYetf0WYANo6nIeqY325oTmu9bdOTSVwxI0tkXpkYvqrBc6ETreFIthXyAMAzrvhZKCjpmGVB+GL/ujikUTtMZvP3zmUzal9IWdoFwbFg0dOxtrv7CkXzDSsIA6aM2jPhS/89DmJ6Q24UQbcvW0eSndi8aPWOoof7Bhg2oZPi57BsHNnFR8z0PbtkidhQgMP0np1kOM3J0tkV6SZhKNKHuaK3RZ61j6lYOXmcpQWo7SRapLsrG9MullcoMBfYlXkMIY7mm6RWURFMZpv86+pKJuB3IXPALNIBCxOIDWkKVTvVM+o27ePB55DBaNqGN9mx4rj8IdRtkM98Ao9qLwaGnj18wZ6h5jRKZwRzmPp8hda9pnjNUR7jLDlAtQ793xDxXDgPR2t+7vQ10QfqGZKRU0jDOIOtYc1oTbN+7n6jd08isG8QrcId+h0Ub6/wJ3EarMsZ0ZdNBGpLvUi8nQdJR6CO8IU6w4Dg+NCkhTrIsFbPI2Rx2b1zCDBm/ftMN6Q+vYhQzgjvW4Uqw5qE7Hrqk5bqj8lVSnYyv/19SgEUuOzehlPAcAAP//sdsAkwAAAAZJREFUAwBgHrItCNCCWAAAAABJRU5ErkJggg==>

[image31]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAFYAAAAWCAYAAABaDmubAAAEd0lEQVR4AeyXZ6gVRxiGNyG9EJKQhORHEpKQShJCSCEJ6QmEJCQhCWlEEayoqCBiQdE/CnawYMPeEMSCvaGo2LCAqFiwgNiwoWLF8jzHs7B37+69ey53j/fHObzvvjPfmdmZ/fabb2bvDiq/XDxQcWwubg2CimMrjs3JAzndNi1iH2C8efAFGMX/VL6Gj8F7oP83R5+H5cQjDOa4/dEO8CWYhM8x9iryR/QuWBakOdbJOJGHY7NoSn05PAuvwoPwJ3gClgvPMdBCeAPOhG/AHfAfGIVOb4ZhDzQQ5qJL4YMwdyQ59kNGbQ2TcBPjOrgFzoE+zC/oZVgqppXaodi+Exo607m0oe7qGYY+BMVXXL6DPscUtD3sCb+BBg2SL+KOvZ/h+sERMAlGyX/88T78DU6HOhspGc+U3ON2h2vIk/AVKFw5Vyg8Dp0/EnzK5R3YF4aYWCz8W9RcJe7YHow2EqYt7bo6kVtWQ3zsag1SDJ2xvwYnQWHZlGX0ntEAF8ONUEUKuFi4BoFti8UapR3/NoZ1QvTh3uMOr8OpMA069gf+dMIr0RnQB0NKRl03kuuMZN5Egqe4DIKHYRMYYhOFj+AsGMK65dVeaqBpxb+N+LctwPtgSQgdey+9BsK2sCaYCkwDblhf0tAHdKJpuzJNcoPpagl3d09oge6GafAlduHP81BFEtEK6y74ATwOj0FPFvvQv2FmhI51QzAHHamlpxuFO615zqajuRg1phCKifBo5E4ep1EQt1k3VybeKGZsSd1V5gZqZA6lngbnbAT+SgNPEEgiTC8+k6cNN78/aKVtADoHZoaOfZPWLpPxaG3YSwOjFingaOEaBJ5ti8Vq8jsWJxbnyyl2cxt/ZYZHqM209gTgWBSrwBOCL945rqjyT/XKBUymlt6oL0J2p+xLu4Rmho51Sb9LD8+k+1HZDRUutfUW4M/QzeFPNIT5zrwbHnNCe1QnUDGq4nTJxW3WPRbRJRU63pUTbRCmAZ0XteuYwRi0m3cpBvZXk/gFRtPbX+goOAT6wnaipkAkG3TscJr6BSXNldK0gDn4nsvHUDjJRylEnfg0dfPXVrQceJFBdJQPbNqgWoDzsnDKS5F+DdrWgNBZmk0/NR23PI8bnd/S2KDxJPEZZVezxzqK2aBjk1q6mWkP1fJ8Lmtg9NRghJkaynLoZmw3k5OoHxdhGjKHf4LtNBwHhXnarzNfvDa/Flfxhx82niAoJmIDVlOWTvWs/AR195M+6HaYGXHH+jZdVi6Fc9xlEVwLxTYubhI61+U6hropoxGqDckdRpQv01Vk1HZkRHOsjjDKDlAX2t073qJiGpDu7tZ9Psy1wmDxpFRrw6QGcccajZ5LfeN+Xz9LJ79ikAJcWj6Yxw93zlex+smIlA3LGEkHLUCNUjcm01c0HfnCTVFJ7Eq/LPAZD2VpmNQm7tikNnGbm9tkjC61aE7DVBLcfUvqEGnsDq1jx2IzYl2uFBsO6uLY+pr97Pq6UUO8z510bEP0R73NqeLYenNl1RvdAgAA//9z7BHyAAAABklEQVQDAHOayi1LpjqLAAAAAElFTkSuQmCC>

[image32]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAFYAAAAWCAYAAABaDmubAAAEf0lEQVR4AeyYZ6gcVRTHR7EXREVFBRULNlRELKjYywcRFBULgijY0JBKSCchkJCekJ6Q3j6FFNIrIYQ0knxID6mQXiEJqaT8fste2DdvZnff8ublfdjH/3/PmXPvzL175txzz7ybo+pfJh6oOjYTt0ZR1bFVx2bkgYwemxaxdzDfLPgkTMLTGNvCnvBz2NC4hwn/gr1hc+h6ELXwAZYueX6FvAk2CNIc62JcyN0Jq/gX21J4BC6Ew+APsKHwGBPNhVfhVPgi3Ax/hoXQ6X9i2AHvgzOh670TmTmSHPsWs/4Hk/ATxgHwEzgaXoJGSyVRO4V7K0FrbgrOXIn+P7wFDoZ3QfExjWvyd0xCbwY7w0+hQYPIFnHH3s50vaBRiKgB04NOnYZ1FxTradLG01UUjxTtTe+8TNeD8FkofLkXUe6Hrh8RvUfzKjRVIXIYn2uj6Je8zFTEHduJ2YbDozCOLzE8DI0S73sK/Rw0gnQwap3gM+p0Q35wG+TzcAIU6qYs13VKA5wP10AlIgfXquJYZSk2ZcBvsCIU/rjXecILcDJMggeB9gdoJsImcBPsACtBpQfJFSYzbyKih2j6wf3wdxiwFuVt6O5C5OC1ynKbIjSt2G3Ev6ICb4N1QnDsrdzVF+osRCIezVvNs3+gt4QeWl2RhT+KywaB6WoBM3km/I3cDtPgS7SKOcMAJSIRHsxb6XkTejgfRhpQO5H+bkR5CI51O5uDDha5Tefb7bgLKtCIPYA0hSASYWnkSR6nURC3eW2uTHxQzPgP1+4yqwEjcxDXabA6MAK/YYAVBCIRppeR9FhtePh9j66tD3IGLBs69iVGu03GIosh5N3dsUHmLvOt+TfWlbv8jtaFxflMit3cRlfZsIRax2grAOdCrQErBF+8lcySGj21L85iMrV0Q/oiZEd0X9p5ZNnQsR8x+jW4F+o02R5duNVWqcA9UIRoVZfXbKDPQtTCOCxGVZxuubjNa8sibkmFjrfEKhwQ0oDOK7TrmP4YtJt3USPvVybxQ4zm7x+RI+BA6AvbgnwDlg2dMYTRfmFJa1LpdsccfUHzDhR+iSk9vJSB1o6mgxDRwZ6FdGfoKH+waSPMcW9eOZGXiidoHPs1UmchItNPsXLLoDE6P2Owh6S78X10d7NlHWp50LFJI0M+DdIx22gWw29hwHMoj8Me0C8hRKbwMDnODH5cHEIKc/i7KCfhGCjM036dmZ60ue5ldFgWWkGgJmI1VlOWTrVWNoism7tj3wjLRtyxvk23lVvhNE+ZB1fAgF9RjGwPC+vJ2VwbFb5l1MxhRJku3EVGbStmNMfqCKMspCvtnh0v028akJ7uXvv7MJeEX2hWSiUHJg2IO9Ya1oLbN+73tSWWXzHhXiPG2m4ohmPQU7YFMuRZ1MyxiBl00BykUerBZPrawHWAZ4QlVhLbhUElpCXWvhJjUrvjjk0dWNChEz3URmEzqSMqgqdvRTdykye0jvX/FUas2xVz40Eljq2v1U+vrwc1xufcSMc2Rn/U25qqjq03V9Z80HUAAAD//22EaDoAAAAGSURBVAMAbhjJLSBJKeQAAAAASUVORK5CYII=>

[image33]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAFYAAAAWCAYAAABaDmubAAAETElEQVR4AeyYV6gdVRRAR7EXREVFwS7YFRELKnb9EUFRsCCIYEVFRRELth8FU0kjjVSSfKSHkJ5ACCE9IZ0UUiC9kt5D1nrMCZNh5s7cx7s37+M+9pp9zp49c+buOWefPe/CqPFXkwg0AluTsEZRI7CNwNYoAjW6bd6MvYzxxsLtkJRhdN6Fx+EReCjBrbTrJVcx0OfQFn6AuyBLnsf4T8wb6AugLpIXWB/GB7ky8RQG+236Q2E+LIalCX6nXQ+5hUHGw2kYDvfDcvgAkmLQP8OwGq6BMTAZLoeaS1Zgn2TUryEt92DYAr2hK3SKGYLeCn9ANeJ11fgH359phGDOov0NXAQ+0xVo5SUOr4G/YxD6e/gbXgEnDaq2kg7spQzXBrpDWu7FYDCdBf6Y7+j7wFejP4KdUI3cVI1zwvcE7evBF42KjnM4BteCz4+KnuVgqvofHWRA3Pgw1jVV6cD+yWg9YAekZRUGcyzqrHxLawlMg2olPXbZ63/B0Zc8EK3YNmU5e/dqgIkwF9SoJjncdIwifeNmReXE+biiR4WTyR/3GH73wWDIkmUY10MQl+OndP6C5khzN5JTDGbeREU3cOgAm+ATCDKPxlMwEoLYtz3DQwVMK552xj9sAy6BqiQE9mKuag/OQFQpcZn1wvMknA8xXU1iYPeEL9CuKFSm+BJ/5cwBUKMy5SusK+EJ2A7bwMpiLfp9KC0hsG4I5iA3pzIXP4CTVcMIdJFYGrmTp3EWpG32zZVF9/T8lxxcZVYDzswu9PPEfcEZ+BYOVhCoTDG9OFmsNtz8LC21tcN7NJQWA2uQXCb9Sl8VReafffhvhiJ5BwcfLM3dOXbvzanSYgm1AG8rAMeieY5YIbh3vIy1aC84iI+p5V+0L0KsdnxpR7CVFgP7It6PwgZYFxNqUpfabGxp8W2uSRtz+v2xO6vSuOTSNvuWRVySKwbeqiTpENKAwUvaDUxHDNrNuzSbJoU6ixcwmr/fQ/eEzuALW4H2owhVTgxsN1z9whK/YMS0gDl6ncPTkJSb6dwJYQemWTe5g5EMlD/YtEG3SSz5bOz2EHMbWt830QYLFZl+KpVbR3Fydr6KdpO0kniOtqvZso5mOTGwWZ5uZtqDth0IO6W1Y7DVS7uZ7GIwPy78KKEZmcOfobEH+oJinvbr7EY62qaip8NCsIJAZcocrKYsg2qtfB196+b/0H5lospJOrC+TZeVS2E/t5gAMyEph+KOOTZu1k05o0wXriJn7U+MbI41EM6yUA5qd+94kPOmAXF3t+/vw1wofqFZKRU6ZjmkA2sNa8HtG/f72mXvV0zyWgtxl9ePSWMd21MYywCNQztL3ZhMX4voB3GPsMTK4rfgVKAtsTYW+OSeTgc21zFxwn9++J+vrK+zhFth09230CnHwR3awPbhvDPW5Uqz9UhzAttSTz+qpW7UGu9zPgPbGuPRYs/UCGyLhfLcG50BAAD//7TozeIAAAAGSURBVAMAD7S/LQrUw/YAAAAASUVORK5CYII=>

[image34]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAFYAAAAWCAYAAABaDmubAAAEMklEQVR4AeyYV8gVRxiGN70nJCE9pJJCII30HtIhgVRIhVyEdJKQQhBFURBFRcXeEBtW7AUbItgL6IUNCxZEsV2o2PvzgPu7DHvO2f/o7rk5P++z3+w3szu735n5Zva/OKr/5RKBemBzCWsU1QNbD2xOEcjptskRewN9/AYd4E+4AyrpSxq0hlrqSjqfDPdCqIdwNIf24LNeii1EcWAfobeZcAmshx9B+wm2lO6kohf48JiaqRU9fwjXQFLPctIHlsMYeBXmwLWQu+LA+gA96K0b9IXX4CgMhVsgTbZ1lKfVZfENz9KoQpvnqf8dQl2EYyR8Co7mxdg/YA/8DLnLwDpKX6KnAeAoxER7oyiaCFfDxxDqOxyrwOBjqtJtVV117qIrKJq2emND3YPjPrgOknIW3p905FU2sCe5eX+YCrsh1qGzhXCK3Y7fVHG+udW+uVXVasGVzrRd2FD7cJyCWfAiKAeJKWOUJxn4izbfQ1WKX85Fy06PJ+7iNPN0rocEXSj/B8fgfOR0rfb6p7nwURgGaXLG+ZwPUzkfLI/Dmu7MsxRLKl7gnqDF46Au99AY4sCG17yHw+RvelhGOdYXFDbDUqiVLqPjTmDOxJTU/9QMAt/RXc5TlFdDOf1K5Rp4DnbCDngdNsBXkFl2Gja+HkdXGA+/QKybKfgyLbGNkauwuTvEURD6PL+xws0N2GDabIdy+pZKR90H2IVwK5ju3sCW0hAq+oG7iHexDiR9HSlPgMwKA+s0cDWdxx28aXK6e/Nm+A9DY/Q5jb025MESfnMbVal6DO8LMBDKyRHn4DCo02noVutfrHnXXQ/FVB3A2xnagD+KuA/uznmj3jsZWHOei4H7PhcnFzVv/BY3VS9zcPu1CbsRTAlXYc3Nnn9NOU1OR+tCnHKhz/NyM+JNOngS7Ns+xR8bVzSDwyJQPv9YCvHCZkDj9GHevYm6NDma11Hhx4Q/gFtKt3OmkGfwZ1YysG603Y405erToD7iED+ED+TXjduVB/DHHU2h7PmF2Jdyq7LqSa3PIPYppgXcketCvANwK6YvxIXMkbc/rDh7fgTr6HwH68ByZ+Rod4YkZy/V5RUH9iea/Q3vg1uU2Vgfwny2lnKazJH6XUy0tSLuP7Y+x2gOn4GDANOgHyg5g05g0+SHhCnLoLqmOKjcKbWl8QrILAPrdHYkuMg41Zz6Wqe+G2xXxPCGC3C4M/CXf5uyI91pTLEwfUNP/uhOW59jGucOBkw0iYMfD0uw7aAJmCruwrpVxFSUM9j0UbFhWgMD69Rw0TLHhvhVZn14rUG/G6eftOL/C4pIBXTZIPew/o/DXYTP4D+NXmmojSIXILdYrhlb8f8DbpkOYrPIAbUlS8O0NgY2zV+Ez9U373620cEIcNFdiS1MtQys++TCXrTojmoZ2KLftdD+6oHNKdxnAAAA//8RSMv0AAAABklEQVQDAGiNui366CYWAAAAAElFTkSuQmCC>

[image35]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAFYAAAAWCAYAAABaDmubAAAEhUlEQVR4AeyYZ6gVRxiGNyG9EJKQhCSQ3kMaqSQhPSEQAmmQ9iOEkEZ6IURF0T+KvYsFrFixK3YFFbGh/rBhwYJd7L3j8xx35Ljuue4R91yQc3nffWe+mTmz++3MN9/eS6PqXy4eqDo2F7dGUdWxVcfm5IGcfrZ4xV7HHD/AFvAveB9Mw2sYG8X8AL0E1iauYvLR8G6YxIMY6sNm8HN4GawIgmPvYLax8AQcAh+Fi+GXsBg6/XsMy+ENcCScCK+GtQVfsi/42sQNPEe9C1wAfaZX0WnQBYTki+DY/5gmOHMm5V+hb7cjeg0Ub3J5F/4C+8I/YUP4NvThkLLQv6ze6Z1fwOz9IGfAXTQQy8fQ1Twb/Q1ugz/C3BEce5SZboYPQHGEy2F4I7wSile4PAndVkgBvQvXKPoq1nLktnI6p/T1vppj7wyTuAvDPfB6WIwVVO6FuSM49n9mehj2gcKyW8vVu1MDHA/nQBUp4EDhGkX2jYuZJcydeUCiYwPqbvWtaBK7MRjWJqMvQeHOM2QMspKBf9DnG3heCA93nNHGTSS6hUtruB5+CwPmUngRDoMB1i1P91Im3a5lDjnd/RlKj8B+MA27MLaFD8EZ0LL3bWgzzmIqCUOgje7OJyzAK2BZCI4Ng9xWE6gYu4xFyyiXgo6pQ+NeqCIVweXM0goaM5GS8NzoRavP+Dv6NFwCa8LPNC6Fz8MtcDM0C1qJfgEzw0mLO/9ExdVgNuAb7kC9FMwOfKsf0cEMAkmFp7BZR5KugqTNunE99Ydiow4ztm+M66Xkaxq8v/dRQ9qtqJnP62gpGAq70WgW4UH9GWVtLdERMDOSjg0DTaHmUfHE/RRNwgzBGPcWDVNgTXC8N5bk/QxK2qwb22hKxWNYDT890ZrgimtHB53qmWCq9Q91425XtBT20WAYbIz6UqR5sAvsILbMCI71YUyxigeGMKDziu1O1gaDduMuxcjxahrdju6AJN1ySZt1U7i039H2Bpen4Bq4KmY9VBjCZlmA7qahaDjYdGgIH8bdm2hLg6vZs8aPCV9Aezq5uAwhz1LODB1rWqKj/BG3YhgcUpXtwYCaxtj3Q8reABK5pc8n3XJsuezEAL+wpF+G0rCAOXqPS8gATMWongUPMlfenrNaThkOIa7Od1APdLMeV7s7xBQUczboWAO0ibMJ+6Z4mHHxZco7YA8ojH3GKGOVNlOZqTTMh2YQSK3Aw8yJg1oezOUTmMxZv8PmDjqGpsEPCcORTjWvd2Wb4zeh80KYGTrWt+QW9G27av9ltDHWH/fNraYutBvjHqdiGJCemNZD2KCpYnCXOK/b1hU4jpldkUg0iosfD+bdTSmbpxsq7qTscyDnhF+Tho9zdkzroGO1T+Kig8agrlIPJreZ39mYCjCWmWKlsW6hR2Uv5rB+yLiT/L/F7Uzv1yFSgAeQKZbPsA7L39CUaT+aBaZYa7N0TOsTHGubsUfHdqfiinULUMwNnr65/Xj8wxvQAdD/bSxCK4Zix1Zs0nii4bFelFKbjr0oHRoequrY4IkLrCcBAAD//w/9OSEAAAAGSURBVAMAAYPLLYB8+yIAAAAASUVORK5CYII=>

[image36]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAFYAAAAWCAYAAABaDmubAAAD6klEQVR4AeyYZ6gUVxiGNz2kEJJAQhJIJYVAGqmQkALpyY9U0khCCEkINlARQRRFsKJixQJiwYoVBQuooIgFQVBRrCiiqNixN3we2SPrcWbv2cvuvf7Yy/uc77SZ+fab0+beXKj/1SQC9cDWJKyFQj2w9cDWKAI1um3eiL2T582FJyDW01S0hB7wNTS3yvn6LM51hj7wE9wKTaK8wHbj6V/B3VCqjygshr0wGf6FKXATNJfyfH0Dh0bAWpgO78FSuAdqrqzAvsVTW0As3/Z4KofADFgHf8EX8AdUqkmVXpDRP89XX7Qv/FuuceatwraCg/Af1FxxYO/giX1hOMT6korHYAkEHSJjgH/HVqqHK70g6l/O18fp+yTcC6XaSuEpqLniwHbhiU6fA9hYnxcrDhdtMJadZreFikQbPzvxsqvdyvl6jF6XYBG8A+ouEpe3qdgUtaHTn9Aolf6417jDCzARsuQosP6sSQmWHT0PlNSlZJ2uKf2y+jTk61EuGgjPwXIwPxM7FFxnMblyybPxZZKXQN1uUgkhsI62/lzoOoTJlG/chosmJTgyLFYaWK9pDCm+et8OJGPB39ga+ypshHL6n8ZN8Cbsh33wPmyDnyFZPtTOOjGOjLs9JlPnirV5Iy0EuNjtqnEXfpRSjKMgrrN8P33LKcVXr/+NxFHnEraC/EMwDz6APLk5j6LRU8Qn2B/Aun7Y2ZAsA/sivd+GMVBO7qi232JSQiiH9pKmK9nvSXUs5pmcetc2mjKV6qsjbhB3MKgLsO4B7bC+/JHYPJ2gYQB4RveliOdgT0KnqU+Wgf2Q3q/ATthRpBNWLSRZCWqPCcRnW0fkKeqPQJacjr/QEOOUi+ssd6VvnlJ9/YcbeCQMm7ABDUud627esuVo3sK1fkz4AgaT9+jpEvI6+WQZ2GH09gtL/KoSlwWqC5+ShF3VaUSx4HTVBh4h46jQebI1VaqvbqZZjriROfKOZzVSdwYcnR9j3UscMI52Z3NYCmlqWAY2q5cbhPXBml9Gsh2+gaDnyTg9R2ObS8HHYPVjGsl3EJ9Z/6bOGXQBmyU/JFyyDOqDdHBkn8f2hPWQrDiwv3LlZnAq+Fbnk/ctYwo+zJ3xRwrdwa8tf0Av8n7dYJpU5Xydgyd+6KzG9oaO4LLmB0578inyU9nlI6XvdX3iwHqGdRS6M99Hb6f5u9igNWRs9/vb8+tnlF3cMU2uhnx1A/KIpa+78a4tODBOYlPkEWtXSsesPnFgs/rEde6cbgx+i5c7nsXXxWV337iu2mU3XP9ZNIEbb4AmU2MCWy3nZlXrRjfifZozsDdiPKrmUz2wVQvltTe6DAAA//9Dsx69AAAABklEQVQDAM+duS0dX/cZAAAAAElFTkSuQmCC>

[image37]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAFYAAAAWCAYAAABaDmubAAADkUlEQVR4AeyYWchNaxjH9zmdeeh0zqkzIGOGlCljCGVIuTKUsVxIklBISkSJEDJPN4aMGUOGcqPMFy5MGTIkQi6QecrvV5Y+y1prr71Ze9/sr/9vPe9a77Pe91nPXu+wvm9zlb9MMlBJbCZpzeUqia0kNqMMZNRs3Bv7E/3thVqQpP5UzoByKinW+gQ2BeaAsX6HLYniEjud3nvBrxCnalQsB4PHlE1xsbYiopVwBrZDRzgCv0HmikpsG3odBfm0GIc/oFhtKvbGKvfFxfoNPlugNzjyTmJHwwMYAZkrnNgf6XEurIAkDaHyPLyEYvVvsTd+uC8p1pr41IbfoaqucFIHMlc4sVPp0eFzHxun/6gYDl86t4b7psmClBTrI1p6B4ehHahfODi9bcWm0VichkJRqvpwLWihEWyEJC2kcgK8gi+Rw7XY+/PF+pCGjbMB9ihY3oldCs6zmFgFC1xTPJqA+sFDIQSJ/Z6b5oPzECZW/ai5AaehXEob60QCXAs+4xhsc7gASRpJ5UVoDffgLnSCqzAAUstOdTaIdRTuQJz+psLET8MWIldhdxBhfAvC1zz/M0/jaWK1icEcfOt6Yo/DP7AfOkOc1lOxGtxFdMf6InltHuXdkFomtjHebWENJMnGJ+PwHApRX5y9N0y9mOvObVRFKm2svnGLaMGkHsS61RqPdd5dhY3TEyoWwEzwRxH3wUs4L+i5TWwXbmoGDvFrWDGBFHOHOJwA1Z7DBrgO+uj/M2UXBM8HUo6Sw9G6MA658DXPk0ZE2lhdXHcQTLAIm9BgqnPe/Yu6KPk2X6bCjwl/ALeUbj2dQlpyPbVM7DK8/cKSupTFaYFirgeHYFU1IH3crugTdLQPH8+/xr6UphKVNla3YlENuZD55j2OquTaC/Dt7IZ9C8/At93RXNBibWK59zO5QHgxsJbDOEd6LcnH+qwJ+g+s/W3j0Ad8CTAfNYySI+gNNkp+SDhlmVTXFN/s1zjOgrOQWuHEDuLOS+BQ8Fc9QNlfGfOJjnHmzkCfrpTdeDuMKZZMSbHuIQo/dE5hZ8MkcFqrjnWriMkrP5WdPvI6RjmEE+setiGOrsx+rv5PuQOE5Xxbg4v6iP8vKMVUQJcflS9WFyC3WP6v4BZ3jQO3TE+xaeQW62YaxyifcGKjfLK65uqbVdtBu7cpbAYX3XPYkqmcid1VsqcsQ0flTGwZHrd0XVYSm1Gu3wMAAP//uxkMAQAAAAZJREFUAwCGAqgtXtU8cwAAAABJRU5ErkJggg==>

[image38]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAFYAAAAWCAYAAABaDmubAAADGElEQVR4AeyYWahNURjHN5kyJBShjBlSpoxFeEDKk6FMDx4kSSgkJeKFEDJmeDFkzBhlKC9KhhcPRIZEIuQBmTLc7u9fd91O6+597lr73LXPedi3/29/a69hr29/Z+1vr30bR/lfkAjkgQ0S1ijKA5sHNlAEAl02acW2YL6r0B1s9aFiHWyFWdAEyqmK9DUpsBuJ1FRoBYUazslBeAjnYSzchtZQLlWkr3GBHUmEloCtRlScgWmg1XwfuxQ+wyLw1SnfATH9s/I1ZuriVXZgm9N9GxwAW92o6AFtoFAvOOkJvurkO8Dqn6Wv1tT1n9qBXc8QPeqfsLa+UlEFt2A0SC05KGWcxfrKntt3fGhfl+PQfEilwpsbyhX6w0mI0xcqd0FfuAMqX8TuA+VZjJeUWrwGFHQO6at5GQ9ivoEgNdPBBxPYpgzaAcqZmEStpuUoaNwy7BB4AlkqpK+LuZGnMAI+wgcYBy9hNjhLAVJnBewYhfdQTPNo1C85BXsXOsI1GA9J0o6hC402WgV2nc7b0beYQvp6nIkPg3Y8k7AzQXXbsZfBWQrsAHqPgiNQTPoVd9NBQb2B1VZrJVZ59xA2STNokGM2vRPqldtoilVoX78z607YBFpAQnv2vZz/AmcpsBPoPRhew6sa1mKlmxzugbSQwwUwLzYF1KQP5d32tMVJqWMODTZ65Ow6nW+gb5JC+6on7zmT68NHi2UPZW09le6GUXaWAruf3vrCEr0oC6UFitFkDmYHoO0Np3WkF5l+zW91Whq+IrSvv3FZq3Mi9j/8BD2Zepr/UHaWAhvXWS8I1Rur8jkO08Hesy6gTqvyH7YcMj4aKx/S+qqPHqUsBbUDF9JT+Be7GR6Bs+zAzmXkM9CjoBV4nbJWJCa6wkEfDw+wW2ANKFV0xa6CrBXaV30qK9Wlui87sNrD9uNKejO3xXaGMWCkpK4tlv5X8JbKFaBtyA9s1grtq7ZYb9LelB1Yl+u8o9NpOAGPIa309k071nVcQ/nqOl9tvzSBrR1cYuFSieMreng5A1vRgSnVuTywpUYwYXw1AAAA//9Jr6K9AAAABklEQVQDAG7+wS1F/w/+AAAAAElFTkSuQmCC>

[image39]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAFYAAAAWCAYAAABaDmubAAAEhElEQVR4AeyYV8gdRRSA1947KCrYG4q9gr0iimADG+qDiIpYUBELthfFnl4f0kglvZAeSK8kgTRSSe8P6Qnp33dzB/bf7N5/b8j+P4R7Od+emTOzO7tnZ86cvSdHtV8hHqg5thC3RlHNsTXHFuSBgi4bZuzVXP9juA5OhfPhMXgHkqL9N4zyIvokaEw5k8EHg8+AqiM3UvsJ/oI3wGdDFS/BsTq0NcMthb2wFYbAJojLP1Q+hEVwAQyEkXAWNJaEF3xO4gbuo94WZkEfeATGwblQuATHHmKkNTAdJsG/cBuMgCBPUngWPoWu8CX8Ck+DD4eqSrpX1Tu98wOYvR9UHXEV9cTyCjibp6I/g83wERQucceOYjRv1Df7DeWVEJeHqdwBLitUSTqXjlH0dllXoy6rpnNK3zOw/Q1tIClXYbgGzoO4LKZyLRQuccfWN9hwOkwDNaoku0rHKEouw7K5ogpjV+xUofFn2lzqG9FJMZQdxDgaHgLlbA7uCb3QeeQLOr0PxyTh4QwFF3GF5mDMNBy4dFxSmEpimHiQUj8IYt3yeA9VEr92ladGd3PCLdAN0mQLxqZwE0wEy953S8rGWVSmhA3O1Xl7udfpZZ1bBcce4IxHoRMYR41Nv1B2qaFSRcd8T8t2UKMaRE5jlP/AF4/KlG9p8Xl8xs8p3wXzoZJ8QuMCuB82wHowC1qCfhNyi4Pa2Z3zHgozQPGigyi4Qd2AThOzA9/qyzTOgyxxF76CxiTOgqTNuiuH7pmiw4ztazN7HGkwVfT+nqc6GS6FofA4ZEkXGtqDWYQT7HXK2tzMB1DOLcGxuzljBcTFGz8Fg28MVUfMEIxxT2EdA5XkNRq9sSTXZ9iNbTSlyq1YDT8d0ZXEGdeMDjrVPcEN+Wvqxt126CzZQcP/8Dv4UsQ8uAV1fYTKJ8GxE+huDA11qpHhQW3QVwccrAkVneo5FKNKznA5vkWnJC65pM26KRzdU+UJrHfCclhW5ke0Ymo4xQK4mvqiw8amQ0P4MO5eTFuaOJvN0f2Y8AW455jOGULuTTshy6YjnZUm0y5Z66GvS8fybA9lTGN06kvUvQFU5JI+lnTLc6ulFSf4hSV+1IhhAXP0HIeQAZiKUT1K3MiceduOajli2INydj6DdmKZ9TjbXSF+OGHOJzrSC5hEf8Up+0G5kMML4CzwZihGxj5jlA7vgMFUZix6JqyGxhI3M8cO2nJvDq9CMmf9AJsrKDwn1Trih4QhS59cQoszex/6D5gDuUXH2tkd1ljimzEbMCWZS8O7YCqGivxoMMb5RWYYEOOv9YV2aGBcJY7rsnUGDmP8MAnceM1ozLv/xP4dOEmuRPscqHrFr0nDR70d0zoEx66j0XSrB9rY9R7aZDrEKKqRscwUK40f7NDAmMPezJiuJP+3uJyyX4eokrgBmWKZ8azC4oo0ZdpJOY+YYiU39DznlfoEx1pxefjWTS+Mq2Gm2lYE7r5FXDd+Tf//cLL434YrMN5WaDnu2EIHSrl4/xTbCWNqTMeeME5Me5CaY9O8chxshwEAAP//C9rtCwAAAAZJREFUAwC0hs4t0WxzJAAAAABJRU5ErkJggg==>

[image40]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAFYAAAAWCAYAAABaDmubAAAEnklEQVR4AeyYZ6gVRxTHNz2kF0hIAumNhPQKqYQ0ki+ppCckISQhpJCEkJBOIKJi74pib1hRsSOIXVFBsXex+0HFhv33uzq67rvr23t17wO5j/9/z5kzM1vOnDlz7jszqv7l4oGqY3NxaxRVHVt1bE4eyOm2IWJv4P5fwZvh2fAS+DT8ABaD436jowF8AdYlzufhQ6HfgDgOt9H6E/qe7yD9NkT+CI7VUW143FK4B26Fw+AmmMTXGMbBDXA0bAvfhnWFf3nwq/BCGMfDNNrBWbA/fBKOhxfB3BEce5AnrYHT4STYCN4NR8E43qXRDD4HO0EXwUUpJ2p7Mf9k8Sg3+AYmcQaGPvB1aDRPRX4LN8MvYe6IO3YMT/NFXdmf0VfBONxyOnUgRiMbEc3k0hAatYiScHVJo2sOPg9T2rOvp+9GeDGMYzGNm2DuiDu2toe9xICr4GToPF98J/ovUAcjSoL3KGlCYvBftN3qG5FJmMoOYBwLH4fiAi6mjL7ILPieQZ/AshA+zlRwOXdoAc2bpgO3jlsKUwEeZipXcOkO7Z+L/AOWg/i9S53/ABPuhD1hMWzB6O66HTkRqrvTWqGbZxGpCAfcvYy4B4pzvZTC4Nj9THoKdoHmS3PT3+huNUQB1xSuUWSe/Qz9J+ih9R/yU1gpnMODGkMXFpEKd5Lf4zd+x6j74Tx4Ingwz2fAI9DDeT3SgFqC9LsR2eBDHenJ+SDKDCi86RCUH+CtUPhByq5cdkNhxHrouS1tF6On8LV0JGkUJG223TkMT4UO8x3Wpo443GGpaNS9TNP0ZRobjv4MTEM3OjpAqwgD7C10bR7mg9EzIzh2FzNWwjh88bMwuGKIKOSyZTZiNM+ab33xmPmo+iaaL5bkLSl2cxtdRXEX1sdgZ3giGHHNGaBTRyI9kN1h5t32tNOwnY4m8H/ookjr4Ja09REiG4JjJzDcUiu0aUamB6VJX7ncCwzRilqA+VklPtd2oNvxPRpJuuWSNtv/MDYNz9JxH1wBXWD5O7qwNJyiAr+AA2AIBh0a0od513OC7howmhdh9ceEC+CZYzlnCnkIe2boDKPSYtotaztMDhE4+4jBelA1+VI63nQQPsIxebE1N/YXlrR+lqYFzNGLXEIFYClGswY8yIy8bTV6DhsMGqPzeZoGlrvRaHeHWLNjzgYd6Q102o9M2QfFZVxegUaBL4MaLeBi+eLBhlqAPxmvQ6sPjQpExRFyf5C+QD8ub8Bkzfo5NndQ+E6ax8EfEqYsfXIlPQbRXmQ9OAdmho51sCesucSVsRqwJPFg+ojOsNVRow+5GC2WLr+i+7O3KdJVRlQU7/O0hdBtawSOQA9B4MFrRTMNm4vuuxokBoE/fjDXCn8qmz5qHVhsQHDsOjott3ojzVsfIy2mk9vb8sPazv8r+H+E1xhnpMedj6kisIa9gydZRVyKtBx8AhngAWSJZcWzGqPvacm0Az0LLLGSB3qWeYUxwbE23B6uuuWFeTXNWdpd/Y5MMqkjyoKnb1kTS5hk7jdYejDHHYioDOKOrcwTjz1l0DH19NPq0rGnnzdjX1R1bMwZp1I9BAAA//9Cb3rVAAAABklEQVQDAMin3C2x/jAEAAAAAElFTkSuQmCC>

[image41]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAFYAAAAWCAYAAABaDmubAAAEdUlEQVR4AeyXV6hcVRSGxy72AoqKvfdewPqgIooPFrDrg4qKFRURxPaiqJiQXh9SSO8kIT0PIT2BVBLSG+mBFNL79yWzJ3tO5sycGzJ3IMzl/+5au5zZ56yzyzqn5+p/VYlAPbBVCWsuVw9sPbBVikCVfjbM2Ov5/c/hJjgTLoJn4D2I1ZfCm/Aw3Af3RFyLXwudy6BDwGfAFOlWSr/Cv/AW+GyY6isE1oC2YbglsBe2wlDYCEE+wGsU+sB0mAVzIn7Br4X+ZNBX4HyI9QiFdjAD+sFTMA4ugKorBPYQI62GaTAR/oe7YSQE3YKzBjpCK2iepwd2LTgzMJnldZk7p3R8jPovIanTqOgFTgRn8xT8r2ETfAZVVxzY0Yzmjfpmf8RfCbFup2AwP8V+Bd/Cd3AhvA/x7KZYUVdW7FG+wzk0/wdtIanrqLgBvDdMQYvwboSqKw5spcEW0ME9FlOQs2A2pbHQUIWxG3pd6P8bjkt9AzYpt7KDVI6BJ0Cdxz+3jN7YLHLifJSlY6k+4eHcCi6lQwsYBW4HBs0lRfGI5vJ/GQTdifMJ/A4novi3G3r9g1xwB3SHUtpCZTO4DSaA/gCsW5j7LG6qwgHn4XxvvtfZeZvZhMAe4IqnoTO8AO5NBsylRrGkPGk70LIfGlNnMVgT8MVjUvUTLT6Pz/gN/gMwD8rpCxrnw6OwHtaB2dFi7NuQWQ5qZ0/Oh3A87TE5f3QwjnuohxZuke6i5LLqj60kT+Gr6ZTEWZCss+zKoXuqDFgXWj1IMakyVXTWvUSPSXAFDINnIU1daXCymEU4wUwtrfMwH0RbZoXA7uKKFRDLGz+DCt8YpkjuP+5jZhJFDSUKb1DnjSW5OaXe36appHyhj9PSCcrJGedBa1BH0NED+Qes+257bJq209AU/gJfipjttKRsjDDZFAI7nu6mWqFMMef2oHXT18b4Nj1h47o03+X4Do1JXHLJOst/0DdNz9FwPyyHpXlC/mxqOJk6ZebiagoHmwEN24f77mV2KoGzeSH1fkz4AjxzTOfcQvwooimbDKSz0mTaJWs5XOnS0Z/pv4ir8E1ZNmMbW60Z0C8s8aNG3Baozr3Iv5ABmIpRPE4eZM68bce1HK3YjXF2Po91Yu3EOttdIX44UcwmA+kPmER/zyXhILoE/2VwFngzuAWFk3JPoaa2joeZdxCsvmnh6zhOAExBH+O5gsJzUiySHxJuWcbkclqc2fuwf4NfmZhsMrD29IR1L/HNmA2YkphefUCjqRimoB15zz0279bEvMuo5tYuW2fgcMphEnjwmtFMpe4f+BmcJNdg/fjBVJSfym4fFTuW6hAC6yep6VZPOrl3fYj11A97FMWCPGFfpeRhgKmZzGH9GjSLuJi7cIt6EhvkAWSKZcazikpXpClTmBhUlZUpVvJAL3tB3BgCa53Lw7dueuG+mpyp9hEPAreOUkG3PSuevln7nmg/sxYnSzd+wBWIaRzFgW2cEY+NMvCYe+p5tQzsqRfN6InqgY2CcTLdwwAAAP///ePJ8gAAAAZJREFUAwBqQ9ItZvS0eAAAAABJRU5ErkJggg==>

[image42]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAFYAAAAWCAYAAABaDmubAAAD7UlEQVR4AeyYR8gUSRiGZ/OyOcAuuwubE7tsjrDxoCJ6MoAJ9SCiIgZURBDTRVFRMaeLASNGVMwXMSsoKIoRA2YPKibMz6OWtO0//tPtTM9lft6nv6rqquqaryt8/T+dq/yVxAMVx5bErblcxbEVx5bIAyXqNszYj+i/LXwKz8Jr8C80g7i+oKAXDIJGYH1M2fQiT14M/gbMQyrbWINjdehYhnQArsF5WAJnIKpfyYyHbTAX/oY18AqUS/14cF14GaIq61iDY28zomOwBdbDEPgWVkDQUyRmQT1whmzCdoCz0AaSakbSBlXU/52y9hBXscca77/afNSxq6jtQJ2F3Ugfgag+JPMxvApR7SPzCSTVu0kbxOq/QH4wjIO4ij3WeP/V5qOOra6y28MtKq2GP0G9xMVlOBubVOHZSduF+r1JuC2dxsZVjLF2otOWkErhx7kVvEkPI2EluB24zF1SZO/qHNfh8CWsA9PzsaPBfRaTSNG+EzWk8k/wNUyHqvQkYw2H8fd0/B2o570kITj2Jo3+gclQE9xH+2BdapgH6k7KOrbrSPpH2AVZ6jkeNhR88Zi8SjPWdvS2G36DU3ASjI72YxtDwdJBVvaU/5nEVlB2uohEZ/gcggy/fJO1KdgA78BS+A/yyYjhfW7GcRbEy8y7cqieVzpsCnePw+OUZqxT6XAiGPE4wRqStszDfCHpghUce4UWhyEqB/4MBb4xTM63OIKETl2O9ZDrinXfnYDNpwbccGBxPstT7t7GrSr1DaV/wCR4nNKO9SKdDoP+4AQSY/ZR5PURpjAFx66luqFWyJPNuT1oPaC0rbnMg3BY6NCwJN133+JeVXLraMKNOC65eJn5vtTNp/+58QMcgoP36YlVhoYbTUDasbry9tLeDx8ni2eO4Zzb3S+UFywd6aw0mHbJmg+NXeamt3sBwxvMI/Ig821eeORO8QvG0KVfWOJHjbgtUJyrxSVEK2nHepU+nJ01sE6sy1hXpivEDyeyhUlH2oEBfxea3AD1Bpc64CzQcSRzc7jUh3jM2ooyZ2VoSzZTeZj5wGBNpx2rHz1uWfrkbTpyFV7HDoAdULB0rJU9Yd1LfDNGA4ZPO7nRHAzFMDkPM6OEzWQGQg/Q8R9g/aDAZKqmPG0PuGxdLctIh0lQjLH6qexWR7fJFRx7gqaGWzOx7l0tsAb+YT8le1du6oZYRhFHKXGWG4ZcIp21jGG/4qFGEa9j34O/IOhJx2qIFT/QQ9/V2uBYK7qUfeuGF+6rYaZ6L4r/U/AFTKPQWY1JJU/fVA0TNCrWWBM88l7VqGPvlWR3XZDdo7J/Ujkdm/2vzfCJFceWyNl3AAAA//+JXZ9GAAAABklEQVQDAKOp3i1lcQ+OAAAAAElFTkSuQmCC>

[image43]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAFYAAAAWCAYAAABaDmubAAAEqUlEQVR4AeyYV6gdVRSGJ3bsDUUFe0OxV7A+qIjigwV7F1ERu4ggthdFRcXeHuwtpBfSK+kJJJCQkEoK6SG99++7OQtOJjM5Z06YXALn8v9n7bL27Jm111577btf0vwrxQJNw5Zi1iRpGrZp2JIsUNJjw2NP4/nPwzPhAfBIeCN8BKah7us0fg7VQbQqDmH2btD3QuyEc6i9Cz+FD0C/DVE+wrAa9Aemmw43whWwO1wMq3EfleFwCewCfeEvka2JD5n8TngYrMaVVH6CY2F7eD0cDA+HpSMMu42Z5sLRcBjUGy9E9oaBCyj8DX+Ff8BB8HH4KvTDEIXwbyHtbOWraX4RptGGhv/h3VBvHol8CeoQzyFLR7Vh+zKbL+rKvkl5NqzG/VQOgmNgYAqFpfBRWBQnFh2Q0j+Y+mfwR5jGqTScDo+A1ZhK5QxYOqoNW2uy8yoK6ysyxCoKt8CiiLmLjgv99yi41Rch0zCUbaWxH7wWikP5cWe1RdaDV1B6AjaE+DhDwTE84RvYBxoO3DpuKaotWNnymyT7V2QIY9txVA6ERdCmiHJK9zLq58N/YBaW0/gVPBcOhZY7Ir+DxllELuKAuxiNi6BwpyrrZhh2CyNugL/DW6Gx6X2kWw3RAl/QwvH+VHgSUqNqJCXV0uECfsEsLjwiF2/R4/f4jS9TvhROhLvDC3ROglfBhXABNPOZhnwQ1g0nVdmT83IKET99aFfqHkxnI8Vf/JgRPIWMcb7wWup6/DJkFjyFT6YjTb0g3WbdnYN6LjSYh+e8XI0dHaaKet3tVH3vE5A94E0wD3/S8Qs0i9DBzIJs8zDvTHvdCAOtY8QsWA1f3G3vitluzLqNgilZf6SxyixiDWXj3AZkFu6l0RdL86ycdmMbXZkwM7mGnt/g7qDHfY2CRu2F9EB+A+k3/IzMw2o6TB8/Qroo0jz4W+raCFEfwrBDUNdIUaeaGB6UBn2ldOKnKdwMzRI6IQ0BESao7gK340O0pumWS7dZ/wDdPDjvJXTOhDMqfAcpTA1HWIDPwg7QBUckGjTCh3H3WBszqDeb6XiZcAE8c0znDCFXZOjnNmlIvdJk2i1rPZTdOpbH+QO94XgpeJJyQG92/PfRULJ0Hm9Y0kuNNCw4rbspMgBTMdvS1AH0vDiI0/1mPHqnWY6OZZjT290hXpzS+rl1DekDTKK9pm6uaB6NvAPqBb4MxcTc8C4KfgCiJTt4m0JPaGhAtAo8zJw4pOV2/NwD0znrM7S5g+I7qe4ELxKGLG3iTtSzN6HxMRwP64aGVdkT1ljiypgNmJJMoOMx6MGESDwZB1AwlroIAyk7qadl6NC01/AwM02Gbls90AUOJ/DgNaMZRf8nUAfQSU6h7OUHURNelQ0fNRWzFMKw8+k03foPaezyqmoyHTGK5sQ45Ulp7mgG8BqNerDJOMW9Dt/DS4tZxFHMbup3HTLgAWSKZcYzh0adQSfwsKVaEzpS+kCvOSgUwrDW3R6uuumFcTXLC90iXiD8f0GkZo5thJ6+jYwrMsb/f+gs/o/DHVhk7B7pVht2jx7UwGAzigaG7RtDWtOw+4aFGnzLpmEbNFytYdsBAAD//xQStS8AAAAGSURBVAMAU7bfLe12zCUAAAAASUVORK5CYII=>

[image44]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAFYAAAAWCAYAAABaDmubAAAEkUlEQVR4AeyXBagcVxRAp+5ONVB3qFGFlgrUW0pdqVHaUqrUKJSWlkJdaBtPCBGiRElCBOKEKAkREqJEiBInbuScz7wwmZ3dzIbMfgj7uWfuffe9+W/2vvvs6Kj+V0gE6oEtJKxRVA9sPbAFRaCgf5vO2GPo50X4Hb6CsyEtl+P4CH6GJ6Gx5UQ+YABcAmm5Csd34O95CX0s1ESSgb2AHifA4zAEzoGRkGzzAOXhsBy6wXvQHY6CxpIf6fgJOAWSchuFVjAVesE9MBpOhcIlBO04ehoK0+AtGAZ3wg1gwFGRo90Joyn0hunwNjwGb0C10rXaFzLa34HvQ0iLA+2AP0OF2WzCfIy9Bt6HwiUE1qltEP9M9PgX9vdgdqIiM7kJxggIshbDAL+OrlbOr/aFVPsTKP8BLSEtF+O4FE6DpMyjcBkULiGwBmYjvc2GM+FccKR/Qgd5NDbWxTooy04zsz748ujQd562WW0cdKf66oxKf8te/M68u9DKyTxcMnqg88inNHoTDkn8cafz5i2wAgzkD+jWMAmuhCBmgfYOHwksmz1ZG12iWYnpdC1x5nT4vdfStgtkyQac/8LVMBa0+6Cbgessqqy45Fl5Iw9nMSo63kc1GNgL4xfcQZdgfwauTYvRA8GgoSJHXL3HRwIzw2K1gfWdQ8GZ8TcvumaiysrX1HQAf+Mn6JthFlSSD6h01t6OXgUr4V6YDy9DbrHTMEIGrF3iTU8Gjnj4hzvjunKZFgIcN9uv3IUvopTGLEj7LJ9F20piwDrSIKz9mJnyGl6zziVsHPZ5MAjug3Li5tyGSk8RD6GfB33uN/2wc4uBDWvUIt4yuKgG2dLwjCJPB5ruqGrPuupAKIf64A/6OQw/LM0VZfyubVRlyvV4/Z726Epixv1HA4NqgrgHfEHZwXeZw8yUzXj/Ac/oDop4DvYktA1/bjGw7uybeGM7ZIlt9C/zAenzohm5Ff96yBKn4ytUpHHKpX2WXeNpnin3470JTIKFaPkWrXhcHK8B74JHwpA0BjQsH87CcsuW2TyXd71MOAD/Y3uccwm5FTu3GDQ7dYp4IUi+eFJcmBJr22g6XdUB12izwv8TfEXp5vxjb1jiDVBcFnBHD/MIJ4CwL+A6QNzIzDwT6YCKuGBymZ0PUnb2mjBmuzMkLIVUHVwMrK1a8DBAHrgxG8RblpnhDUvHGB4L4GkIcg2G0zO5NuOqqbiZ2WHQ2j15PAvpM+s7+JxBu9FZ4kXCJcugmmhm9i4a/gIzILeEwI7iDTcFg+gVsS1lR+opdBhdO3MjewGfxzJvW/6AXyl75kXVVF6ltzngtPUbB2ObkaioPw8vDxPRv8E34FLRBP0l5BHj4PKRp21JmxBYKxypuzE8Zhmo67DTozQZn1nq/dvz6yOUXdxRNRfPsH6Lp4gz6N0Z5/djNogbkEcsv3Upns/BxAibMsWK4hHLWFRsVK4yGVjbeElwWvel4FqEKhF3TjcG7+IHO/KUvJxwuPsmioWYbrjOws7895lQM0kHtmYd05GDhzoypTEDe2RGNP5V9cDGgTjcah8AAAD///t7ehwAAAAGSURBVAMAQvfRLeoINqYAAAAASUVORK5CYII=>

[image45]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAFYAAAAWCAYAAABaDmubAAADyklEQVR4AeyYV6gVVxSGb0IaISEkgYQkpJOEBBJCCvggCqIo+GIvKIiKiIgKNhRUFEFRsSs2FCsWrKiIigiCiIL6oNgLIoINUbFh/z6ZwePc2efO3Os5ipzL/83abWavu2bNnj3n7arKX0kiUAlsScJaVVUJbCWwJYpAiS6blrHfMVcXCOkXOobDeGgP78CrUk2+6tdPHIaC/jbBlkVxYP9gtkGwAk5CO0jTfzTOgYOwBurDLvgIyqWsvupPLw474RJsh9nQFkquOLAG5hqzTYCQ3qJjJbSETbAX+sBV6Al5tTzvCdH4LL46tAOHqdAIFsB9MHvLkrVxYPcx6XzYDyH52P1A58dQKDP8x8KGjOUvM45LDsvi6wecZFDXYU+DOsDBxDFrKZZWcWCzzHKDQY9hB9QD9SGH5rAK8irP3Hmv3ZQTvoA94DwmxB3Kg8EAY2pUP0YUe9fQHZaThntf7LlO1Sz4FbsbLJsRMym7zmJyyaUl1wk5BjeIxn6GXQouWYexw6AmxS/jvxj4J6j3POQhT2C9rnd8EQXP64v9G47A66avIodcZ7tRHgC+tEZju0JIvuyO0vk/+MK7iPUmncJ6LUw2GaC0kaFs6sRg72QzrI+Zj9sWyg0hJF82X9OZxCxItln/lLF5lObru9EFFmPvgTJjL1AYASEtoWMeuOPxJdeGsm0TsRsgs0KBTbuAd3EaHQZ1K9atlpngujuXekit6dCxJD8H2l3b6KqTLkdnn4lsbFxnXW9NiLit0N6iMhnGgAkk7tlnUL8LmRUKbFoW9OCqayF22oBOou765brreka1mlw6OtKaxEcu2WZ9JGPzKM3Xs9EF4myNqlVPokLo//bJO8EYP3xMlumUe4PL3b/YzApNkObs+4Gr+iLzbt4M9Je6Oc1X99nOm7zZ7mJcDuLkcEwh3gizszGNj8AM98lcSNl9MCabkoF1bdLRtCCu5pKtILln7U6bWfkQW04V8/UYjrgt9GOG4jP5Kf4NpXHg04apJj96XLIM6uf0emMeYMfCIcisOLDuRX00XZPMvn+4guXj2E9AbeTgBtsNus4Nob4NdHYgtlzK4qu+dObwPbgl1NfNlKeAGYmpUaMY4VKHya84sE76O6d/CwZS/Pz7jbofBphnclF3i+VvBedp6Q9uQ25jy6WsvrpVch86C8euQAvQ33idpVpUbrHOFR1RpDMObJEh1bpco/yxZhk9bmEwtZJv31qdmOMkg+hT5ee6L6Acp9ZtaG0CW7cZn5+9/nnxzSu9ysC+edEs+I8qgS0IxsssPgUAAP//EXcYEQAAAAZJREFUAwB7ZK0tG/Sx3gAAAABJRU5ErkJggg==>

[image46]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAFYAAAAWCAYAAABaDmubAAAEWElEQVR4AeyYV8gcVRSAx94VFRUVC4qIgj7YQLFjV1CxgwUFxS4qioqKIlixd8WuqGBHkSQkeUhCSEiBJKQX8pCQXiCkkvJ9yz1hWGZ2d5J/9s/D/pxvzrll5t49c+fcc/+ds95fLR7oObYWt2ZZz7E9x9bkgZoem1+xBzDGg/AWPAqHQ5EcR+XD8CpcA/0pRzP4XdBKnO+zdHgTLoWuSDj2REYbBLvADLgX1Neh83IRhSEwH36B++BX2Am6JScz0FPg+M7xZuwyeYCGobAQ/H2foW+C2iUc+zkjfQwfwhdwHqyDn+AQUHbl8gN8BH/ABLgbroQ7oar8XPWG1H9f9DLwy0KVyq20vA8Xw9ewHly9XVm1OtZVejaDfgNHgLKCyz+wN1wLylVcjgRXAKohS7nq4DvQVeWwqjek/qPRX8FYKJM9adCpf6JngTKOiy/DVYtZr+jYjQzhRP9HL4aQ1cnYJ+krkna1JLOhLJ+LtRtUEceu0r9K38vpfCiMBMc5Fu3veRqtg1Ft5TF6tIvfdCkWB7XFTetqjA0QclYyhiXtRqFpiFAHlvegcBBUkTrj8vlpIs7pR+xHYBI8D+3EkGefU7mcAsruXqoQjm2+5zIqzgDDQ7xhwwJVmStcHWxKhj8imf2uIqMxzt7DbJ4EN61X0O4LqEJxs5tCy5nghrcA7UuaifZZqM6kyLH7c+sH8BfcDyEGf+2ylRYOtk8eNxtjdzOuguY6ywfmb+7ALppPhKXvuX8tKK7YeRgvQpm4OX9J4+/gJncj2rq30X9Dx9LsWD8D06fhPMGHhjMpZku8gJsdaqtEOdq3NiTjBrQTa+b4knpjG03bJYvS3bOTDmWcNd4af6Mur1dReBfM0Q0F8gJlM6E16I4l71jfvGnXeO42j/WT98GmK1Rlvm11bGba4op0wsstFPAddbcV4CdXVP8SfauI827uPydVxGpNxWxzMvK/O1U11AVcp8MtYNpp+vkQ9mQ4HTqW/AAvc5cJ93PomIAnq4idZg00ZX6u6sB4NoBCWSigqVYpcuy/acSYeypm7hMukFjRUR/aF+HqvIQKF5YLxoznW8r5r5diawnHeoJ6nK6mKYPR5qoj0KYn09CK2YE5Yf405onNk5AJuH26iXFUp5qRNI87lQp/x/XokBMwzMPfQJctglG0GbJ06sHYvhgzpdewJ0LHomP3ovcn4Cd9IdpPX30O9n7gjohqZAPujLG7etr6jYbXIVYIZu1iWmgYMX4a905jRG0XgP/voNiQ27keAx4SnkH/B++BKxLVVvyC32nbq6SDjnVyblq+/WbcmGyP28dguEqNw+avrnCDO9VdEx10EqMdBTpSPKo6r5XUhZgqmYd+SoUHH7+0J7AjzGG2FBfU3JY9WjTq2BbNhU3unP6vwOzBf8YUduqg0t23g27b1UUnDuQJnizdgDC7I9vi2L6amXlyXz1rh3tOfzp2h3NGX06o59i+9GbuWVsAAAD//8OX8d4AAAAGSURBVAMAfRbALbm5R9YAAAAASUVORK5CYII=>

[image47]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAFYAAAAWCAYAAABaDmubAAAEQElEQVR4AeyYacgVVRjHp30vKioqWigiKupDK+17faioaI8gCooW2hfaKYKifV9U3BX1g7igiIqKqIiK+sF9R1BwAVEUV1x+v8s5Os5759656tzrh/vy/8//Oc85Z865z5w555n3yKT9V0oE2oEtJaxJ0g5sO7AlRaCk26ZX7GmM8Qb8Cb4Nz4XVcAfObwIfQo+ArcKFDPwirIVLqPwU/gjvh01BDOzljDYaHgUXwVeg+hiaxs8UrFuI+iCGovY7AW0WrmSgj2B/6ByfRvPwOhXj4GroPP9Hn4KlIwa2EyP9A/+CneHtcBvsC8+C4m4uPvE3Uf3vol/De6ErGGkI/Rpqva/xyZjroG8WkotnqfkD3gO7we3Q1etvwCwXBtZVejPDdIfnQbGei6vxRPRRKG7lcg30lUIq6FW5JsnzQRuRcxppnGo7FbsrnA7zcDwVBnUQugSKGVx8GK5azHJhYHcyhBMdga6FEZuDcVLQkag/SsWsINum4ix4ceyCTRtu9iA9zoaToeNcjDrXj1EDjNTFO7Sot3/TpDoc1BoPLQ+iHRYCbww6Ieg09CboKkAqsKwR22gXZZmHnges8ziDSx/4FpwNv4D1cHRo4Nt5dbCPDVpYYmCzHR7AcT10e8h7wgbG03Yj7VTksEHMaNxnX2ZWH0APrW/Rl2AePOzmUXkD9MBbhfqQFqPeCymGaoE9la5/wsHwNZgHswOfqpnDnLxG+D1s3LuzdBVkfZZPp08j8AFn2x8THJ4BW4Ptil2J/RXMQ28qusCB0EPuSVTfL+gQWBjZwPoaDKD3ROhNPUkxO8AMwQl64o7tULu/4wmKTizLS3P87m1UHRTWhN5Lg0Zxn3W/df+NvrRuovAb/A66aOSX2H/DLbAw0oH1yZt2zaS3q9FDzRsbPFx7oe93SvrddzGTWsHoSYPnqtBXrprfFI7mheG8s42XBUdcraGY7A5G+ncHV0Xu5GqO/gxq2mn6aXo5l/J1sDDSA5iLmnB/Ru84gYexPQCQCvzSMaiPUHICSOIrfSDpln0PBasFdli4cXruukwf3Q7iitaXpg/C1XkfTheWK/w27B4w7+2lqiNiYF+l6j1omjIG9WtlEmp6sgAV7n2mZL5GHmq2G0+Fh9sKtNlwHzWox1UZeD4+5/c4GnEZxvnwB7gLVsMUnG5ZBvVMbB+MmdL32LNgYRhYP0f/pYeHzF2or7h6C/Yp0BMRST7k4ufkVahtpCem5Rh8qkqHaaHbiPun+961jKjtHPzMpljBC1wvgqaHn6DDoW+bKxKzLnyDf63bKqeBgXVyHlo+/Sz9KrPe7p9zydbHstsH1U2BAbqCkS6ABlL6qer/OzbgizBVMg/9D4cfPmYv72PHbQ6zJlxQy2u2qFFpYGtUl1rl6VvqANzcII5C/bL0AMJsDloZWPPk5vzKFozSysC24Oc2b8h2YEuK9R4AAAD//yNwecoAAAAGSURBVAMALVS4LeZM4iQAAAAASUVORK5CYII=>

[image48]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAFYAAAAWCAYAAABaDmubAAADq0lEQVR4AeyYWahNURjH9zXPQggZIoniwVRkSoYHCplLiSJD3BAhRIqQeSYz4UGGSJE8IFF4IPOQB2UoUTJm+P333Sunba/r7HX2Oec+nNv/t761117Dd7699lpr33Je4S8rESgENith9bxCYAuBzVIEstRt6oytzRjTYA3MhEZgU0tuLIDV0B/ypWYMPB5KU158NYFtg2cXoTw8gUkgOxQb1lQKLsMbUJsd2JGQK7VjoLlwDOTjKKxNefPVBHYnnm2FzbALesI3OAL1wWgMmY3QF/bCd9CMcJm1R2nroho0eg96szBWJemrdRDbDQVWs7QbFfZBY5A+kJyBajAEpCokCupJ7DOQbpPoB2rWko2lhrFq/618k+weuAU2Je2rbRxruQL7k7ty9Dz2HRh9DjLVAzsQ2wCug9q1wKrOPKwCjIkl9RGrQYzKSfhazHj/W7+pEi3z47RpDaLKDzDqGmSuBLZXYOtiD8MMuAeLwEVFLo3SbJOJrxWCMTpg24NUSUkcTGDDbQZQ0Bm0PJjZaE4JWrsmcm8OaNNajp0AZUmuvmqze8AP6QLanF9j9ZCeYvW7MekpKrC1aLoJTsEUMKoYZA5iv4KkGfuKzBKwSZuN1u4wmgXhMl3XsXVkKY+a+a6+HmKM3XACtCGPwKpsLfY0pK1wYPUaHKf1VVCn2vXJ+nrrp573PLDGaJ3Veqv115Sl2uFcyLEwrSzlxZRnKldfPzHwelgBWgrEYvJb4AukrdTA6snr2HWH1jrHalNTxzpaUeS9UAJmtpL19dtPPevn8QHuj41Ar1xU+VLqxlFRRGVXX3vT12MYDTp26vg5nfx96ARpKzWwy2ilA/dCrAnWYPLarDDeWSVgrsn60pFMy4GZJX5hDpOowLr6qkmj2dkP/zWx9Db2IL8fUt9eLkuXCexkqs0CHVMuYfVldQ2ro9QjrPSQRPeGYY1ak2kCq+AX5FJaRxXUyhGDuvp6g760ZCmo9chrEumktJL8XUhbCmxVam8DbTJ9sHr1ZbuTrwnaETG+xpE2B30kzMeegw2gp4zJiXQs1DKitV7rXkdGVV4TQP/v4NJXpr7qDV7n9+SQKLByTpuWnn4YfZXpvulaxw+d7bZToI8J/S9hNnmzdJDNuvQw2zJKU1AghT6r9f+Oj5QZZeqrJtRL01lcq8DGbaMgXqCRvta0qJN1knZfp4YxGiXla4whS6q6BLakZeapzsmZ91JGe8hnYMtoSJJxqxDYZOL4Ty9/AAAA///x0gaZAAAABklEQVQDAEF1xi0fj9IwAAAAAElFTkSuQmCC>

[image49]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACMAAAAXCAYAAACBMvbiAAACUklEQVR4AeyVO2hUQRSGr4/Ct6hYaGGliIgvEEVREBFFVBS0EQQRUVRQsbEQEURE8IUoKipiZSFYiI2gmBRJikBISCCEPLoUSUiKNHk/v2+5c7NZciFZuCFFlv+bc+bOXebfmTmzC6M59MnKzGl+41O4AsshaAnJTXgAu2GSsjBziRnOwGPYBX8g6CdJHbyEVzDJUBZmNjLJFhiEJjgAi2EnbIYKcExjt8kT5ZtZzdNb8ALuwAYoRs/50lFQx2i+wDAcgm4IMt8fOsZgZiudf7AImuEaGM8Ri9E2vvQVVsFdUGtoNEXIyXxdLoubYOYT/ffwDj7DYRiA77AelBM8JEljB2NBDSRX4RdUwgrohwUQZD4UOkbNuBru6zceuN+EyCX8HUXRMjgLqpHGg5dGPePKStpuAiWwB05CG1hNhJzM23NZ3GhmhNwl9dR3kgf1xkkozVH6/ro0HOeV6CPNdVCeQ6MH+T+JP9Y5SaNNNH8hURjw4J7iaf6y7aOvymxmwDPe1dh5onfNE2ItdIDF4VG4SO7hfkNMFMwkD+LkOHEvuHXVxJnoAy97rtyCy+SPIOg1ieYsDs100U80lRkr4C1vePhuEItRD1/yPmklFkqTVTy0mggTKjTj5fSD4XK4AF5OhNlRvhlLzRKvYWrvGQ+2t2a4wHicrfLN+F/iXvonNhZPa5mujfPMQzBjKd5jthNgCZYS3fP7RO8XQvbSzFKmsQK8JY+Quy3Gg+QroQVmRZrpYyYPrmemEG9nx3kle2km+1mmOcO8mbSFml+ZtJUZBwAA///JhCXgAAAABklEQVQDAD3Hbi9wbLCnAAAAAElFTkSuQmCC>

[image50]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACMAAAAXCAYAAACBMvbiAAACT0lEQVR4AeyVOWhUURSGn0vhLioWCgqCIgqKhSiKO6KFihYiKIKNigoKNhZioYiV+woqYiUoWIiNG2Khdi6gWEhSJUUSshAI2dfvS+ZMJiETMoE3pEj4v3vOve++nPPOXWZiMob+0khmJd93FrbAQTgGoSk4p+EirIEBSiOZZUS4C+/hBHyB0GucP3ADbsKAhNJIposg+2EW7IYyUKtplsJ3aAMTs4K4fcpNZjZDZ+A6nIMFMBp189J0OAQ7YAKoTTT1ENJfHx1tJLOczieYBCVgebUH8AtVVOYnL26HB6Dm0HRASH9edLSRzGM6D+E+PIHN0AovYD6oFTSXhmEVz9QHmqPwH56CG3YJtgWiSriJfrtOYDJWYwMDz2EhKEv4FmcauP6YxH/uxsvHPyeBJ2UfVjXQGHQxtgI8TZhe6Vf2epnGZDrxn8E7qIZQU8Zx/XUtv1+XD587byuNczDJIppG+AufwY81Jm5igh91gnjgxt3DYG7Z1tFXX20K4BpzrcwR7G04DnVQBR4Ot8Jh/J1wB7KKZLIDGWcXdi24dL+whch75TIvlIMn6iU2dAvnKng4TKYGP6uhkvF+uMeMN3AKRiOX24rWDvGy++QH454mTL8GJzOZR6/gG3iVeznhFke5ybjrPeK/Ce0948b21vTiYih95SZzhXCupUfTW5RuspdmLhRFkcxJop0Hf0s8gm5Cf0MuMOb9gklfJjOVMI9gBmwDl0W7EX8mlEJRZDLNRHLjumcG4+3sc6akL5NJP8oII4wnk69Q45XJV5keAAAA//87iDfHAAAABklEQVQDAHWqcS+jmZaYAAAAAElFTkSuQmCC>

[image51]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACMAAAAXCAYAAACBMvbiAAACN0lEQVR4AeyVSUhVURyHX9OiOaIWRVSroqBWFRREw6IWRQUNUJsKKqIgiigoImjZsGmESnHlwpXiRkRFRF2JulFQFF0quBEFRxy+7+F53Pf0iYr34UL5fef3v+ce7/mf8a1NrKC/uJK5wRi/wVPYCEG/CO6B76/jsgtPKo5kXvLlKfgMF6Ec1sAWeAhf4Dv8gP+wHpKKIxlHfoGv98FHOAsn4RA8gn1wAN6Bz714UtFktlPzDL7CC9gDS9Eb/ikP1AYLmIA2KAZ1kOIYlEJKIZnD1FTAOuiAx6C7toSLUg2tW0A9oKiERhiCEVAulctknCIk85ea3/AT/oFTO4oXwm5QRyg+zIMj5XVK54isu4lH5Xdcqp5opbHJOBuneSiAvaD6KZzCTbg7Hku0U3hCstHK+yA7vM/DNXD59+NBdwicdSxdJuN65lNdBm46LCmn1WCzBUyC05wN39Mk4YA+EfyBo/AcosfbgTtYqtNlMta4ca8QjEPQqZmgdsYXai7tbRo3gHvlNd4FQTsIBmGWQjKZLy5RcQJcuiZ8MfJYe68EPFHRQd7lY25gLF1zJbONJu70EtwbFFtWdfO1AZilzGS8DYtoVQe3YAxypmgyTqtHvJnevWfc2MeJvdKx+BVNxhPgkXtPt/62YImrFDshJwrJPKG3V3AZqqAa6uEteL9g8ctkvAO8E/xVPU+XLot+hngrdEJOZDLD9OTGdc9k4u3se5rEL5OJv5cF9rCaTLaJWp2ZbDMzDQAA//9Ye7HJAAAABklEQVQDAE9kZC+Qi9MDAAAAAElFTkSuQmCC>

[image52]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACMAAAAXCAYAAACBMvbiAAACLUlEQVR4AeyVyUtVURzHb4NBMwUtahG0ioJqU0FBNCwqKCoaNi0qiKKZIgqKCFpGbZoHFVcu3Ii4EVERUVeibnThgP+AC9044/D5PDxy33s+UeE+XPj4fs7vd865l9/v/s7w1kYr6JdUMtf4xq/wCDZCpjYw8A3SlEQyL4kwDZ/hHFTDGojrPZ3rkKYkkrlNhLPQDx/hFByDoCM4+yBL8WS2M/sEvsAL2A3L0RteKgJVYAOToNbT3Id/kKWQzH5mamAd9MAD0Lr2uEtSA093gLpHUwutoJ7T/IQpyFJIxkx/MfsD/oOlHcOWwi5QB2g+LMAh5uI6TcexG1jl+1ao2858mIzVOMFkCewBNUhTCZvgKqguGk9ILjqZDzLwXTpXwOXfi70D7pe/2HewA/Q3Y1MyGbMtplcFbjpMSsOpNorCw5Z2lLFcOM905Ad9wvkNB+EpeLxNwP3icS9kbAD0h7ApmYyOG/cSzgQEHZ91GmftYo1Le4uHW8C98hrbB0Ee6Wd0tsAfCB8bhWQYS9N5ekfBpWvDLkUea++VQAEvxz+ynP5FcJkeY7Mqw9ictuF9hwqwjJj8KLMy3gNlhG6CmzAOeVM8GcvqEW8nuveMG/swvlc6JnnFk/EEeNH5v+F/i9Ev0+yEvCgk85Bor+AC1EE9NMNb8H7BJC+T8Q7wTvConSGky6I9ib8VeiEvMpkRIrlx3TOZeDs7zyPJy2SSj7LICKvJ5CrUamVyVWYGAAD//0I4U0cAAAAGSURBVAMAtFthL5OsFE0AAAAASUVORK5CYII=>

[image53]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABgAAAAXCAYAAAARIY8tAAABnUlEQVR4AeyUuy8EURTGZ1F4S4QCjUY0ohKCiEdBQUKhJRqPeEaj0KlVngmJqBDRiEYhokBEQy38BxqVZ4Tft5mbzN4h7J1st5vvN+fcO/eeb3LuzGZ4Kf65GDTxTI1gq4SJQUhQMgbt7FyCA6gBo2ySVdiDUUhQMgZn7JyBewjqlcEk7EJIQYMi7o7DIkxDGUSWMaim0glkgp5w2I99xEgyBhtUWYMV2IQWeIMdKAVbMXvCH4fmZaCn1luxzaJykJ64HEEu9IKtUCF7gRnL4JPBFhzDIxg9+0meH4PhN4PQvAy0UYfbTfIBRvV+cu7HBqLaWEUcALXTFFQ+xFwlaI06Qup5xiA+CFw6yetAbbshStdcJqACmmEKvkBS3kqiN09rrsjj+smgkDvLcAhjEEm2QRbV9uEC+uEdIiloEKOSXtdbor4DHX4teQc4K2iwQBV9ZPNE09se8mJwljEYocIsdMEp6H/nkjgHd+AsGeSwex3yoQ3UEkX9LRcwfgBnyeCF3TpcnYGNvnLdZ4mbZOC285+70gZ/NirlLfoGAAD//1rgKYcAAAAGSURBVAMA4BU6L/SIqO0AAAAASUVORK5CYII=>

[image54]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABgAAAAXCAYAAAARIY8tAAABwUlEQVR4AeyUyysFURzH70XKO8oCO5GNrEReeRQKxcLCgo28Iq+ShZ2NjYVXhMjKQkqysZAssLAhS/EfsLAiJD7faeZ27phy7+ju3L6f+f7uOXPmO3POmYkLxPjnJ6CSe6oAL2XSOAchRRNQz6gl2Idi8NICjTUQUjQBZ4wah3vwUguNiRAmMyCDnmGYhzHIgUilsbWcfARhcgKKaD2BeNAd9tvegUeiKU7SjWHhcgI2aF6FFdgEzeMbvgvZ4FbQaGigvoUn+CEF6K61K3bozQXpmYMeNxlvB7fMgG46G2EdBqAAFsGSAj6ptuEYHsHRi12k2G6aGdBLxyAMwQE8wARYUoAKLW4rxQc4KrOLc9vLcU1jId4Dmk4zqI+2LsgHbVcsEHACrD/GoYm6FDRt17h0xWEE8qAKRuELHG1RVIP6J3FLXgHp9CzDIeixMf9yByRwqT24gE54hz/JDAhyJW3XG1zvgRa/hFrbEPMnM2CWS+glm8GduW2jzgLfcgK0f7UwzVzpFPTducSn4Q58SwFJjF6DVKgDTYlcn+U0/mtfY/6kgFeGanG1Bm70lqufU/xJAf5GRjjqP+DXiYr5FH0DAAD//5pI8uoAAAAGSURBVAMA4TdAL6ItzHoAAAAASUVORK5CYII=>

[image55]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABgAAAAXCAYAAAARIY8tAAAB6ElEQVR4AeyUPShGURjHXx+L71IUyiaLDBIhhcJAMcigZJCPCFkkg1JiUPIdSiwGWSRFCYOPspAJMdoYlBASv/+pq+Om3ve9snn7/87znHvuef/nPufcG+r7458Xg3zWlAdu5XBhEOogDIyCMShmxjisQgbYaqDTAkOgvJZoFIzBHjO64ApsJdIZhR54gg04BSPbII4rbTACnZAEgaiKm+5ApeslHsEFGDkG6fS2QbXTCpvIFauJ/pTGDSnwCCrhLDELjByDOXrTMAnzUAgvsAwJ4FaIdeGDXE+wS3yGM+gAIxlo1ToVi1xJBumeZh0iQSUgfJNtcMOIDAhGr7SpYCSDd7IF2IRbcKQNUx6lxoVtsMWYNtq5Fk//GIxkoESbW0HyBo50rpXvq4FcUBlV83pylVN/qr1aoj8GjSCzYaKRY2A6VlNGng0q2wlR0qraSbShBUTVWfUn9fXTTME5lMIDGP1kEMvIBKxBKwQqPYmOqEr+NcdtEM7IChxADWjDCN5lG6ieOq56C/UeaCWZ/HUJeJZtMMC/6DH7iE5tK8l1Kgje5Bg0M70bymEH9N05JOr7ckn0LBlEMHsGoqEIVBJFfVti6F+DZ8lAr7c2V3vgRm+5xn9l4HlyIBP1BIHc5/mefwO/pfsEAAD//1UQ8igAAAAGSURBVAMArotRL/7HoHUAAAAASUVORK5CYII=>