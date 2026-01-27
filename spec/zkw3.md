# III. 

CASBIN Protocol 

3.1 CASBIN Protocol Features 

The Zkw receiver uses a custom standard interface protocol (CSIP, ZKW Standard Interface Protocol) to send data to the host. Data is transmitted via asynchronous serial mode. 

3.2 CASBIN Protocol Framework 

CSIP Data Packet Structure: 

| Field 1 | Field 2 | Field 3 | Field 4 | Field 5 | Field 6 |
| --- | --- | --- | --- | --- | --- |
| **Header** | **Payload Length** | **Message Class** | **Message ID** | **Payload** | **Checksum** |
| `0xBA`, `0xCE` | Unsigned Short (2 Bytes) | 1 Byte | 1 Byte | < 2k Bytes | Unsigned Int (4 Bytes) |



1)  **Field 1: Message Header (0xBA, 0xCE)** Two hexadecimal characters serve as the message start delimiter (message header), occupying two bytes. 

2)  **Field 2: Payload Length (len)** 
Message length (two bytes) indicates the number of bytes occupied by the valid payload (Field 5). This does not include the message header, message class, message ID, length, or checksum fields. 

3)  **Field 3: Message Class (class)** Occupies one byte, indicating the basic subset to which the current message belongs. 

4)  **Field 4: Message ID (id)** Follows the message class and is a one-byte message identifier. 

5)  **Field 5: Payload** 
The payload is the specific content transmitted by the data packet. Its length (number of bytes) is variable and is an integer multiple of 4. 

6)  **Field 6: Checksum (ckSum)** 
The checksum is the cumulative sum of all data from Field 2 to Field 5 (inclusive), calculated word-by-word (1 word includes 4 bytes). It occupies 4 bytes. 

```
[cite_start]The checksum calculation follows this algorithm: [cite: 323]
```c
ckSum = (id << 24) + (class << 16) + len;
for (i = 0; i < (len / 4); i++)
{
    ckSum = ckSum + payload[i];
}
```
[cite_start]In the formula, `payload` contains all information from Field 5. During calculation, Field 2 through Field 4 are first assembled (4 bytes form one word), and then the data in Field 5 is accumulated in order of 4-byte groups (first received is low order). [cite: 329, 330]

```

3.3 CASBIN Types and IDs 

Each category of interaction messages for the CASBIN receiver is a collection of related messages. 

| Name | Class | Description |
| --- | --- | --- |
| **NAV2** | `0x11` | Navigation results: Position, Velocity, Time |
| **TIM2** | `0x12` | Timing product proprietary information: Time pulse output, time system information |
| **RXM2** | `0x13` | Receiver output measurement information (pseudorange, carrier phase, etc.) |
| **ACK** | `0x05` | ACK/NAK messages: Response messages to CFG messages |
| **CFG** | `0x06` | Input configuration messages: Configure navigation mode, baud rate, etc. |
| **MSG** | `0x08` | Satellite navigation data information input as auxiliary information |
| **MON** | `0x0A` | Monitoring messages: Communication status, CPU load, stack usage, etc. |
| **AID** | `0x0B` | Auxiliary messages: Ephemeris, Almanac, and other A-GPS data |
| **INS2** | `0x14` | Integrated navigation product proprietary information |



3.4 CASBIN Payload Definition Rules 

3.4.1 Data Encapsulation 

To facilitate structured data encapsulation, data in the payload section is arranged in a specific way: data within each message category is packed tightly. 2-byte values are placed at offset addresses that are multiples of 2, and 4-byte values are placed at offset addresses that are multiples of 4. 

3.4.2 Message Naming 

Message names consist of a structure like "Message Type + Message Name". For example: the configuration message for configuring PPS is named `CFG-PPS`. 

3.4.3 Data Types 

Unless otherwise defined, all multi-byte numerical values are arranged in Little-Endian format. All floating-point values are transmitted according to IEEE754 single-precision and double-precision standards. 

| Abbreviation | Type | Bytes | Remarks |
| --- | --- | --- | --- |
| **U1** | Unsigned Char | 1 |  |
| **I1** | Signed Char | 1 | Two's complement |
| **U2** | Unsigned Short | 2 |  |
| **I2** | Signed Short | 2 | Two's complement |
| **U4** | Unsigned Long | 4 |  |
| **I4** | Signed Long | 4 | Two's complement |
| **R4** | IEEE754 Single Precision | 4 |  |
| **R8** | IEEE754 Double Precision | 8 |  |



3.5 CASBIN Message Interaction 

Defines the mechanism for receiver message input and output. When the receiver receives a `CFG` type message, it must reply with an `ACK-ACK` or `ACK-NACK` message based on whether the configuration message was processed correctly. The sender must not send a second `CFG` message until the receiver has replied to the received `CFG` message. Other messages received by the receiver do not require a reply. 

3.6 CASBIN Message Overview 

| Message Name | Class/ID | Length | Type | Description |
| --- | --- | --- | --- | --- |
| **Class NAV2** |  |  |  | **NAV Navigation Results** |
| NAV2-STATUS | 0x11 0x00 | 48 | Periodic/Query* | Receiver navigation message status |
| NAV2-DOP | 0x11 0x01 | 28 | Periodic/Query* | Dilution of Precision |
| NAV2-SOL | 0x11 0x02 | 80 | Periodic/Query | ECEF format Position/Velocity |
| NAV2-PVH | 0x11 0x03 | 80 | Periodic/Query | LLA format Position, ENU format Velocity |
| NAV2-SAT | 0x11 0x04 | 12+12*N | Periodic/Query | Satellite information received by receiver |
| NAV2-TIMEUTC | 0x11 0x05 | 20 | Periodic/Query | UTC time information |
| NAV2-SIG | 0x11 0x06 | 8+16*N | Periodic/Query | Satellite signal information received by receiver |
| NAV2-CLK | 0x11 0x07 | 20 | Periodic/Query | Receiver time bias, frequency bias |
| NAV2-RVT | 0x11 0x08 | 44 | Periodic/Query | Receiver raw time information |
| NAV2-RTC | 0x11 0x09 | 32 | Periodic/Query | Receiver RTC time information |
| **Class TIM2** |  |  |  | **TIM Time Messages (Timing Version Only)** |
| TIM2-TPX | 0x12 0x00 | 24 | Periodic/Query | Timing pulse information |
| TIM2-TIMEGPS | 0x12 0x01 | 36 | Periodic/Query | GPS time information output |
| TIM2-TIMEBDS | 0x12 0x02 | 36 | Periodic/Query | BDS time information output |
| TIM2-TIMEGLN | 0x12 0x03 | 36 | Periodic/Query | GLN time information output |
| TIM2-TIMEGAL | 0x12 0x04 | 36 | Periodic/Query | GAL time information output |
| TIM2-TIMEIRN | 0x12 0x05 | 36 | Periodic/Query | IRN time information output |
| TIM2-TIMEPOS | 0x12 0x06 | 64 | Periodic/Query | Timing engine position status |
| TIM2-LS | 0x12 0x07 | 16 | Periodic/Query | GNSS system UTC information exception alarm |
| TIM2-LY | 0x12 0x08 | 16 | Periodic/Query | GNSS system time leap year alarm |
| TIM2-TCXO | 0x12 0x09 | 20 | Periodic/Query | TCXO crystal frequency offset information |
| **Class RXM2** |  |  |  | **RXM Receiver Measurement Information** |
| RXM2-MEASX | 0x13 0x00 | 16+32*N | Periodic | Pseudorange, carrier phase raw measurement info |
| RXM2-SVPOS | 0x13 0x01 | 16+56*N | Periodic | Satellite position information (all satellites) |
| RXM2-SFRBX | 0x13 0x06 | 16+4*N | Periodic | Satellite raw navigation message information |
| RXM2-SVP | 0x13 0x0A | 60 | Periodic | Satellite position information (single satellite) |
| **Class ACK** |  |  |  | **ACK/NACK Messages** |
| ACK-NACK | 0x05 0x00 | 4 | Response | Reply indicating message was not correctly received |
| ACK-ACK | 0x05 0x01 | 4 | Response | Reply indicating message was correctly received |
| **Class CFG** |  |  |  | **CFG Input Configuration Messages** |
| CFG-PRT | 0x06 0x00 | 0/8 | Query/Set | Query/Configure UART working mode |
| CFG-MSG | 0x06 0x01 | 0/4 | Query/Set | Query/Configure information transmission frequency |
| CFG-RST | 0x06 0x02 | 4 | Set | Restart receiver / Clear saved data structures |
| CFG-TP | 0x06 0x03 | 0/16 | Query/Set | Query/Configure receiver PPS related parameters |
| CFG-RATE | 0x06 0x04 | 0/4 | Query/Set | Query/Configure receiver navigation rate |
| CFG-CFG | 0x06 0x05 | 4 | Set | Clear, save, and load configuration information |
| CFG-NAVLIMIT | 0x06 0x0A | 0/8 | Query/Set | Query/Set filtering rules for satellites used in navigation |
| CFG-NAVMODE | 0x06 0x0B | 0/16 | Query/Set | Query/Set navigation mode information |
| CFG-NAVFLT | 0x06 0x0C | 0/20 | Query/Set | Query/Set navigation threshold information |
| CFG-WNREF | 0x06 0x0D | 0/4 | Query/Set | Query/Set GPS week number reference value |
| CFG-INS | 0x06 0x0E | 0/4 | Query/Set | Query/Set INS installation mode |
| CFG-NAVBAND | 0x06 0x0F | 0/12 | Query/Set | Query/Set available satellite systems and signals |
| CFG-JSM | 0x06 0x10 | 0/4 | Query/Set | Query/Set current anti-jamming/anti-spoofing mode |
| CFG-CWI | 0x06 0x11 | 0/4 | Query/Set | Query/Set current anti-jamming mode and RF parameters |
| CFG-NMEA | 0x06 0x12 | 0/8 | Query/Set | Query/Set NMEA protocol sentence output configuration |
| CFGRTCM | 0x06 0x14 | 0/16 | Query/Set | Query/Set RTCM protocol sentence output configuration |
| CFG-TMODE2 | 0x06 0x16 | 0/28 | Query/Set | Query/Set receiver PPS timing mode |
| CFG-SATMASK | 0x06 0x21 | 0/56 | Query/Set | Query/Set whether satellites participate in positioning |
| CFG-TGDU | 0x06 0x22 | 0/48 | Query/Set | Query/Set hardware delay for each signal frequency band |
| CFG-SBAS | 0x06 0x23 | 0/16 | Query/Set | Query/Set SBAS satellite reception configuration info |
| **Class MSG** |  |  |  | **Receiver Auxiliary Information** |
| MSG-BDSUTC | 0x08 0x00 | 20 | Input | BDS System UTC Information |
| MSG-BDSION | 0x08 0x01 | 16 | Input | BDS System Ionosphere Information |
| MSG-BDSEPH | 0x08 0x02 | 92 | Input | BDS System Ephemeris Information |
| MSG-BD3ION | 0x08 0x03 | 16 | Input | BD3 System 9-parameter Ionosphere Information |
| MSG-BD3EPH | 0x08 0x04 | 92 | Input | BD3 System Ephemeris Information |
| MSG-GPSUTC | 0x08 0x05 | 20 | Input | GPS System UTC Information |
| MSG-GPSION | 0x08 0x06 | 16 | Input | GPS System Ionosphere Information |
| MSG-GPSEPH | 0x08 0x07 | 72 | Input | GPS System Ephemeris Information |
| MSG-GLNEPH | 0x08 0x08 | 68 | Input | GLN System Ephemeris Information |
| MSG-GALUTC | 0x08 0x09 | 20 | Input | GAL System UTC Information |
| MSG-GALEPH | 0x08 0x0B | 76 | Input | GAL System Ephemeris Information |
| MSG-QZSUTC | 0x08 0x0C | 20 | Input | QZSS System UTC Information |
| MSG-QZSION | 0x08 0x0D | 16 | Input | QZSS System Ionosphere Information |
| MSG-QZSEPH | 0x08 0x0E | 72 | Input | QZSS System Ephemeris Information |
| MSG-IRNEPH | 0x08 0x11 | 88 | Input | IRN System Ephemeris Information |
| MSG-IGP | 0x08 0x17 | 16+2*N | Input | Grid Ionosphere Data |
| **Class MON** |  |  |  | **MON Monitoring Messages** |
| MON-CWI | 0x0A 0x00 | 4+8*N | Response Query | Interference signal output |
| MON-RFE | 0x0A 0x01 | 8+8*4 | Response Query | RF Gain Query |
| MON-HIST | 0x0A 0x02 | 4+2*512 | Periodic/Query | Histogram statistics of IF data |
| MON-VER | 0x0A 0x04 | 64 | Response Query | Output version information |
| MON-CPU | 0x0A 0x05 | 16 | Response Query | Baseband processor information |
| MON-ICV | 0x0A 0x06 | 64 | Response Query | Chip version information |
| MON-MOD | 0x0A 0x07 | 64 | Response Query | Module version information |
| MON-HW | 0x0A 0x09 | 56 | Periodic/Query | Various hardware configuration statuses |
| MON-JSM | 0x0A 0x0A | 8+4*N | Periodic/Query | Anti-jamming/anti-spoofing information output |
| MON-SEC | 0x0A 0x0B | 4 | Periodic/Query | Intuitive anti-jamming/anti-spoofing information |
| **Class AID** |  |  |  | **AID Auxiliary Messages** |
| AID-INI | 0x0B 0x01 | 56 | Query/Input | Assist position, time, frequency, clock bias info |
| **Class INS2** |  |  |  | **Integrated Navigation Information** |
| INS2-ATT | 0x14 0x00 | 32 | Periodic/Query | Attitude of IMU frame relative to local nav frame (NED) |
| INS2-IMU | 0x14 0x01 | 8+24*N | Periodic/Query | Sensor information |
| **Class RTCM** |  |  |  | **RTCM Output Information** |
| RTCM_1005 | 0x15 0x00 |  | Periodic | RTK Station info, ARP info |
| RTCM_1019 | 0x15 0x02 |  | Periodic | GPS L1C/A Ephemeris |
| RTCM_1042 | 0x15 0x03 |  | Periodic | BDS B1I Ephemeris |
| RTCM_1044 | 0x15 0x04 |  | Periodic | QZSS L1C/A Ephemeris |
| RTCM_1045 | 0x15 0x05 |  | Periodic | GALILEO FNAV Ephemeris |
| RTCM_1046 | 0x15 0x06 |  | Periodic | GALILEO INAV Ephemeris |
| RTCM_107x | 0x15 0x0D |  | Periodic | GPS MSM format measurements |
| RTCM_109x | 0x15 0x11 |  | Periodic | GALILEO MSM format measurements |
| RTCM_111x | 0x15 0x13 |  | Periodic | QZSS MSM format measurements |
| RTCM_112x | 0x15 0x15 |  | Periodic | BDS MSM format measurements |

Remark*: Except for CFG class messages, for messages containing "Query" in the type, their query function is implemented through the CFG-MSG statement. Refer to section 3.13.2 for implementation method. *Remark**: For the lengths of RTCM protocol statements, refer to the RTCM output protocol document.* 

3.7 CASBIN Information Flags 

3.7.1 PVT Valid Flag 

In the CASBIN protocol, the receiver's position, velocity, time (Time of Week), and frequency validity use a unified validity flag.

| Value | Description |
| --- | --- |
| 0 | Invalid value |
| 1 | External input value, source such as AGNSS, RTC/FLASH saved history, etc. |
| 2 | Rough estimate value |
| 3 | Hold value / Timing interruption |
| 4 | Dead reckoning value / Dead reckoning timing result |
| 5 | Result of quick positioning mode |
| 6 | Result of 2D positioning mode |
| 7 | Result of 3D positioning mode / Reliable timing result |
| 8 | Result of DGPS (Differential GPS) |
| 9 | Result of RTK Float solution |
| 10 | Result of RTK Fixed solution |
| 15 | Receiver's timing position is fixed |



3.7.2 Measurement Quality Indicator Flag 

Measurements include pseudorange, carrier phase, and satellite information. Bits are used to identify the validity of each measurement.

| Bit | Description |
| --- | --- |
| B0 | 1 = Code phase valid, can be used for pseudorange positioning |
| B1 | 1 = Carrier phase valid, can be used for RTK/PPP positioning |
| B2 | 1 = Carrier phase half-cycle ambiguity determined (inverse PI correction valid) |
| B3 | 1 = Carrier phase has half-cycle error, has been subtracted |
| B4 | 1 = Pseudorange has no integer millisecond ambiguity |
| B5 | Reserved |
| B6 | 1 = Satellite position valid |
| B7 | 1 = Satellite elevation too low, or in an invisible position |



3.7.3 Comprehensive Time Flag 

The comprehensive time flag is used to indicate the validity and reliability of time. Bits are used to identify the validity of various time information.

| Bit | Description |
| --- | --- |
| B0 | 1 = Time of Week valid |
| B1 | 1 = Week Number valid |
| B2 | 1 = UTC leap second information valid |
| B3 | 1 = Time (Week Number and Time of Week) reliable |
| B4-B7 | Reserved |



3.7.4 Satellite System Time Source 

Each satellite system's time is relatively independent, and there are system time offsets. The output time information generally selects one of the systems.

| Value | Description |
| --- | --- |
| 0 | GPS System Time |
| 1 | BDS System Time |
| 2 | GLONASS System Time |
| 3 | GALILEO System Time |
| 4 | IRNSS System Time |



3.7.5 Week Number Time Validity Flag 

The receiver's week number time is generally obtained via navigation messages.

| Value | Description |
| --- | --- |
| 0 | Week number invalid |
| 1 | Week number is external input (RTC or AGNSS) |
| 2 | Week number comes from GNSS message |
| 3 | Week number comes from GNSS message, accurate and reliable |



3.7.6 Timing Exception Alarm Flag 

Timing series products feature timing exception alarm functions. For UTC leap second exceptions and message week number exceptions, alarms can be raised promptly, and erroneous information and corresponding satellite PRNs are output.

| Value | Description |
| --- | --- |
| 0 | No alarm information |
| 1 | No leap second information |
| 2 | Leap second information exists and is normal |
| 3 | Leap second information exists but is abnormal |
| 4 | Week number normal |
| 5 | Week number abnormal |



3.8 CASBIN Protocol Functional Features 

3.8.1 Raw Message Data RXM2-SFRBX Structure 

3.8.1.1 GPS 

**3.8.1.1.1 GPS L1C/A** 
The GPS L1C/A signal sends 1 subframe each time, containing 300 bits of valid data. Each subframe is loaded into 10 Words. The high 2 bits of each Word are padding fields, and the low 30 bits store valid data, as shown below: 

| Word | MSB | ... | LSB |
| --- | --- | --- | --- |
| **Word1~10** | 2bit Pad | 24bit Data | 6bit Parity |



**3.8.1.1.2 GPS L2C** 
The GPS L2C signal sends 1 Message each time, containing 300 bits of valid data. Each Message is loaded into 10 Words (referenced as Bytes in source but shown as Words). The first 9 Words use bits 31~0, and the 10th Word uses bits 31~20 for valid data. Bits 19~0 of the 10th Word store padding data. 

| Word | MSB | ... | ... | LSB |
| --- | --- | --- | --- | --- |
| **Word1** | 8bit Preamble | 6bit PRN | 6bit Message Type | 12bit Message Tow (12MSB) |
| **Word2** | 5bit Message Tow (5LSB) | 1bit Aflag | 26bit DATA |  |
| **Word3~8** |  | 32bit DATA |  |  |
| **Word9** |  | 32bit DATA |  |  |
| **Word10** | 20bit DATA | 12bit CRC(12MSB) |  |  |
| *(Note: Source description for Word10 in 403 differs slightly from diagram 420-425. Diagram shows: 20bit DATA, 12bit CRC. Text says bit31-20 valid, 19-0 Pad. This suggests a total of 10 Words of 32 bits)* |  |  |  |  |



**3.8.1.1.3 GPS L5** 
The GPS L5 signal sends 1 Message each time, containing 300 bits of valid data. The frame structure of GPS L5 is the same as GPS L2C, so please refer to 3.8.1.1.2 GPS L2C for its data structure. 

3.8.1.2 QZSS 

QZSS system messages include QZSS L1C/A, QZSS L2C, and QZSS L5. Their frame structures are identical to GPS L1C/A, GPS L2C, and GPS L5 respectively. Please refer to 3.8.1.1 GPS. 

3.8.1.3 BDS 

**3.8.1.3.1 BDS D1** 
BDS D1 messages are used to transmit BDS B1M/B2M/B3M navigation signals. Their frame structure is the same as GPS L1C/A, so please refer to 3.8.1.1.1 GPS L1C/A. 

**3.8.1.3.2 BDS D2** 
BDS D2 messages are used to transmit BDS B1G/B2G/B3G navigation signals. One page of a subframe is sent each time:

1. For pages of Subframes 2~5, the storage method is consistent with BDS D1 messages, so refer to 3.8.1.3.1 BDS D1.
2. For pages of Subframe 1, each page contains 150 bits of valid data. Each page is loaded by 10 words. Words 1-5 use bits 29-0 to store valid data. Words 6-10 send padding data (specifically `0x1555554B`, `0x15555548`, `0x1555554B`, `0x1555554B`, `0x1555554B`). 



Structure for Subframe 1:
| Word | MSB | ... | LSB |
| :--- | :--- | :--- | :--- |
| **Word1~5** | 2bit Pad | 24bit Data | 6bit Parity |
| **Word6~10** | Padding (0x15555548/4B) | | |



**3.8.1.3.3 BDS B2A** 
BDS B2A messages send 1 frame each time, containing 288 bits of valid data. Each subframe is loaded by 9 words. All words use bits 31-0 to store valid data, with no padding. 

| Word | MSB | ... | ... | ... | LSB |
| --- | --- | --- | --- | --- | --- |
| **Word1** | 6bit PRN | 6bit Reserved | 6bit Message Type | 18bit SOW |  |
| **Word2~8** |  |  | 32bit Data |  |  |
| **Word9** |  |  | 8bit Data | 24bit CRC |  |



**3.8.1.3.4 BDS B1C** TBD 

3.8.1.4 GLONASS 

**3.8.1.4.1 GLN R1F** 
GLN R1F messages send 1 string each time, containing 85 bits of valid data. Each string is loaded by 3 words. Words 1-2 use bits 29~0, and Word 3 uses bits 24-0 for valid data. Bits 31-25 of Word 3 store the "Time within day (half-hour)" count for the string. 

| Word | MSB | ... | ... | LSB |
| --- | --- | --- | --- | --- |
| **Word1** | 1bit 0 | 1bit invalid | 4bit String Idx | 26bit Data |
| **Word2** | 2bit res |  | 30bit Data |  |
| **Word3** | 7bit tk in day (30min) |  | 25bit Data |  |



**3.8.1.4.2 GLN R2F** GLN R2F messages are the same as GLN R1F, so please refer to 3.8.1.4.1 GLN R1F. 

3.8.1.5 GALILEO 

**3.8.1.5.1 GAL E1B/C** 
GAL E1B/C messages send 1 "normal" page each time. Each normal page consists of 1 odd page and 1 even page, each containing 120 bits of FEC decoded valid data. Each odd/even page is loaded into 4 words. Words 1-3 use bits 31-0, and Word 4 uses bits 31-8 for valid data. Word 4 bits 7-0 are padding. 

*(Structure Diagram Representation)* 

| Word | MSB | ... | ... | LSB |
| --- | --- | --- | --- | --- |
| **Word1** | 1bit E/O (0) | 1bit Page Type | 6bit Word Type | 24bit Data |
| **Word2** |  |  | 32bit Data |  |
| **Word3** |  |  | 32bit Data |  |
| **Word4** |  | 18bit Data | 6bit Tail | 8bit Pad |
| **Word5** | 1bit E/O (1) | 1bit Page Type | 16bit Data | 14bit Reserved 1 (MSB) |
| **Word6** |  | 26bit Reserved 1 (LSB) | 6bit SAR (MSB) |  |
| **Word7** |  | 16bit SAR (LSB) | 2bit Spare | 14bit CRC (MSB) |
| **Word8** |  | 10bit CRC (LSB) | 8bit Reserved 2 | 6bit Tail |

**3.8.1.5.2 GAL E5B** GAL E5B messages are the same as GAL E1B/C, so please refer to 3.8.1.5.1 GAL E1B/C. 

**3.8.1.5.3 GAL E5A** 
GAL E5A messages send 1 page each time, containing 244 bits of FEC decoded valid data. Each page is loaded into 8 words. Words 1-7 use bits 31~0, and Word 8 uses bits 31-12 for valid data. Word 8 bits 11-0 are padding. 

| Word | MSB | ... | LSB |
| --- | --- | --- | --- |
| **Word1** | 6bit Word Type | 26bit Data |  |
| **Word2~6** |  | 32bit Data |  |
| **Word7** | 22bit Data | 10bit CRC (MSB) |  |
| **Word8** | 14bit CRC (LSB) | 6bit Tail | 12bit Pad |



3.8.1.6 IRNSS 

**3.8.1.6.1 IRN L51** 
IRN L51 messages send 1 subframe each time, containing 292 bits of valid data. Each subframe is loaded into 10 words. Words 1-9 use bits 31-0, and Word 10 uses bits 31-28 for valid data. Word 10 bits 27~0 are padding. Subframes 1~2 and 3~4 have slightly different structures. 

(1) Subframe 1~2 
| Word | MSB | ... | ... | ... | ... | ... | LSB |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Word1** | 8bit TLM | 17bit TOW | 1bit Alert | 1bit Auto Nav | 2bit Subframe ID | 1bit Spare | 2bit DATA |
| **Word2~8** | | | 32bit DATA | | | | |
| **Word9** | | 6bit DATA | 24bit CRC | | | 2bit Tail(MSB) | |
| **Word10** | | 4bit Tail(LSB) | 28bit Pad | | | | |



(2) Subframe 3~4 
| Word | MSB | ... | ... | ... | ... | ... | LSB |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Word1** | 8bit TLM | 17bit TOW | 1bit Alert | 1bit Auto Nav | 2bit Subframe ID | 1bit Spare | 2bit Message ID (MSB) |
| **Word2** | 4bit Message ID (LSB) | 28bit DATA | | | | | |
| **Word3~8** | | | 32bit DATA | | | | |
| **Word9** | | 6bit PRN ID | 24bit CRC | | | 2bit Tail (MSB) | |
| **Word10** | | 4bit Tail (LSB) | 28bit Pad | | | | |



3.8.1.7 SBAS 

**3.8.1.7.1 SBAS L1** 
SBAS L1 messages send 1 Message each time, containing 250 bits of valid data. Each subframe is loaded into 8 words. Words 1-7 use bits 31-0, and Word 8 uses bits 31~6 for valid data. Word 8 bits 5-0 are padding. 

| Word | MSB | ... | ... | LSB |
| --- | --- | --- | --- | --- |
| **Word1** | 8bit Preamble | 6bit Message Type ID | 18bit Data |  |
| **Word2~7** |  |  | 32bit Data |  |
| **Word8** |  | 2bit Data | 24bit CRC | 6bit Pad |



3.9 NAV2 (0x11) 

3.9.1 NAV2-STATUS (0x11 0x00) 

| Message | NAV2-STATUS |
| --- | --- |
| **Description** | Receiver navigation message status |
| **Type** | Periodic/Query |
| **Structure** | Header: `0xBA 0xCE`, Length: 48, ID: `0x11 0x00`, Payload: See below, Checksum: 4 Bytes |

**Payload Content:**

| Offset | Type | Scale | Name | Unit | Description |
| --- | --- | --- | --- | --- | --- |
| 0 | U1 |  | ephNumGps |  | Number of valid GPS ephemerides |
| 1 | U1 |  | ephNumGln |  | Number of valid GLONASS ephemerides |
| 2 | U1 |  | ephNumGal |  | Number of valid GALILEO ephemerides |
| 3 | U1 |  | ephNumBds |  | Number of valid BDS ephemerides |
| 4 | U1 |  | ephNumQzs |  | Number of valid QZSS ephemerides |
| 5 | U1 |  | ephNumIrn |  | Number of valid IRNSS ephemerides |
| 6 | U2 |  | res1 |  | Reserved |
| 8 | U4 |  | ephPrnMaskGps |  | Valid GPS ephemeris PRN bit mask. BIT0=1 means PRN1 valid, etc. |
| 12 | U4 |  | ephPrnMaskGln |  | Valid GLONASS ephemeris PRN bit mask |
| 16 | U8 |  | ephPrnMaskGal |  | Valid GALILEO ephemeris PRN bit mask |
| 24 | U8 |  | ephPrnMaskBds |  | Valid BDS ephemeris PRN bit mask |
| 32 | U4 |  | ephPrnMaskQzs |  | Valid QZSS ephemeris PRN bit mask |
| 36 | U4 |  | ephPrnMaskIrn |  | Valid IRNSS ephemeris PRN bit mask |
| 40 | U1 |  | utcIonFlagGps |  | Validity flag for GPS UTC and Ionosphere info [1] |
| 41 | U1 |  | utcIonFlagGal |  | Validity flag for GALILEO UTC and Ionosphere info [1] |
| 42 | U1 |  | utcIonFlagBds |  | Validity flag for BDS UTC and Ionosphere info [1] |
| 43 | U1 |  | utcIonFlagQzs |  | Validity flag for QZSS UTC and Ionosphere info [1] |
| 44 | U4 |  | res2 |  | Reserved |

**Remark [1]: Message Validity Flag**
High 4 bits indicate UTC parameter validity; Low 4 bits indicate Ionosphere parameter validity.

* 0: Missing
* 1: Unhealthy
* 2: Expired
* 3: Valid




3.9.2 NAV2-DOP (0x11 0x01) 

| Message | NAV2-DOP |
| --- | --- |
| **Description** | Dilution of Precision |
| **Type** | Periodic/Query |
| **Structure** | Header: `0xBA 0xCE`, Length: 24, ID: `0x11 0x01`, Payload: See below, Checksum: 4 Bytes |

**Payload Content:**

| Offset | Type | Scale | Name | Unit | Description |
| --- | --- | --- | --- | --- | --- |
| 0 | R4 |  | pDop |  | Position DOP |
| 4 | R4 |  | hDop |  | Horizontal DOP |
| 8 | R4 |  | vDop |  | Vertical DOP |
| 12 | R4 |  | nDop |  | North DOP |
| 16 | R4 |  | eDop |  | East DOP |
| 20 | R4 |  | tDop |  | Time DOP |



3.9.3 NAV2-SOL (0x11 0x02) 

| Message | NAV-SOL |
| --- | --- |
| **Description** | PVT navigation information in ECEF frame |
| **Type** | Periodic/Query |
| **Structure** | Header: `0xBA 0xCE`, Length: 72, ID: `0x11 0x02`, Payload: See below, Checksum: 4 Bytes |

**Payload Content:**

| Offset | Type | Scale | Name | Unit | Description |
| --- | --- | --- | --- | --- | --- |
| 0 | I4 |  | tow | ms | GPS Time of Week |
| 4 | U2 |  | wn |  | GPS Week Number |
| 6 | U2 |  | res1 |  | Reserved |
| 8 | U1 |  | fixFlags |  | Position validity flag, see 3.7.1 PVT Valid Flag |
| 9 | U1 |  | velFlags |  | Velocity validity flag, see 3.7.1 PVT Valid Flag |
| 10 | U1 |  | res2 |  | Reserved |
| 11 | U1 |  | fixGnssMask |  | Positioning satellite system mask.<br>

<br>BIT0=1: GPS used<br>

<br>BIT1=1: BDS used<br>

<br>BIT2=1: GLONASS used<br>

<br>BIT3=1: GALILEO used<br>

<br>BIT4=1: QZSS used<br>

<br>BIT5=1: SBAS used<br>

<br>BIT6=1: IRNSS used |
| 12 | U1 |  | numFixTot |  | Total satellites used in solution |
| 13 | U1 |  | numFixGps |  | GPS satellites used |
| 14 | U1 |  | numFixBds |  | BDS satellites used |
| 15 | U1 |  | numFixGln |  | GLONASS satellites used |
| 16 | U1 |  | numFixGal |  | GALILEO satellites used |
| 17 | U1 |  | numFixQzs |  | QZSS satellites used |
| 18 | U1 |  | numFixSbs |  | SBAS satellites used |
| 19 | U1 |  | numFixIrn |  | IRNSS satellites used |
| 20 | U4 |  | res3 |  | Reserved |
| 24 | R8 |  | x | m | ECEF X coordinate |
| 32 | R8 |  | y | m | ECEF Y coordinate |
| 40 | R8 |  | z | m | ECEF Z coordinate |
| 48 | R4 |  | pAcc | m | 3D Position accuracy estimate |
| 52 | R4 |  | vx | m/s | ECEF X velocity |
| 56 | R4 |  | vy | m/s | ECEF Y velocity |
| 60 | R4 |  | vz | m/s | ECEF Z velocity |
| 64 | R4 |  | sAcc | m/s | 3D Speed accuracy estimate |
| 68 | R4 |  | pDop |  | Position DOP |



3.9.4 NAV2-PVH (0x11 0x03) 

| Message | NAV2-PVH |
| --- | --- |
| **Description** | Position and Velocity information in Geodetic Frame |
| **Type** | Periodic/Query |
| **Structure** | Header: `0xBA 0xCE`, Length: 88, ID: `0x11 0x03`, Payload: See below, Checksum: 4 Bytes |

**Payload Content:**

| Offset | Type | Scale | Name | Unit | Description |
| --- | --- | --- | --- | --- | --- |
| 0 | I4 |  | tow | ms | GPS Time of Week |
| 4 | U2 |  | wn |  | GPS Week Number |
| 6 | U2 |  | res1 |  | Reserved |
| 8 | U1 |  | fixFlags |  | Position validity flag, see 3.7.1 PVT Valid Flag |
| 9 | U1 |  | velFlags |  | Velocity validity flag, see 3.7.1 PVT Valid Flag |
| 10 | U1 |  | res2 |  | Reserved |
| 11 | U1 |  | fixGnssMask |  | Positioning satellite system mask.<br>

<br>BIT0=1: GPS; BIT1=1: BDS; BIT2=1: GLONASS; BIT3=1: GALILEO; BIT4=1: QZSS; BIT5=1: SBAS; BIT6=1: IRNSS |
| 12 | U1 |  | numFixTot |  | Total satellites used in solution |
| 13 | U1 |  | numFixGps |  | GPS satellites used |
| 14 | U1 |  | numFixBds |  | BDS satellites used |
| 15 | U1 |  | numFixGln |  | GLONASS satellites used |
| 16 | U1 |  | numFixGal |  | GALILEO satellites used |
| 17 | U1 |  | numFixQzs |  | QZSS satellites used |
| 18 | U1 |  | numFixSbs |  | SBAS satellites used |
| 19 | U1 |  | numFixIrn |  | IRNSS satellites used |
| 20 | U4 |  | res3 |  | Reserved |
| 24 | R8 |  | lon |  | Longitude |
| 32 | R8 |  | lat |  | Latitude |
| 40 | R4 |  | height | m | Geodetic height (Ellipsoidal) |
| 44 | R4 |  | sepGeoid | m | Geoid separation (Difference between Geodetic and MSL) |
| 48 | R4 |  | velE | m/s | East velocity in ENU |
| 52 | R4 |  | velN | m/s | North velocity in ENU |
| 56 | R4 |  | velU | m/s | Up velocity in ENU |
| 60 | R4 |  | speed3D | m/s | 3D speed |
| 64 | R4 |  | speed2D | m/s | 2D ground speed |
| 68 | R4 |  | heading |  | Heading |
| 72 | R4 |  | hAcc | m | Horizontal position accuracy estimate |
| 76 | R4 |  | vAcc | m | Vertical position accuracy estimate |
| 80 | R4 |  | sAcc | m/s | 3D speed accuracy estimate |
| 84 | R4 |  | cAcc |  | Heading accuracy estimate |



3.9.5 NAV2-SAT (0x11 0x04) 

| Message | NAV2-SAT |
| --- | --- |
| **Description** | Satellite information received by receiver |
| **Type** | Periodic/Query |
| **Structure** | Header: `0xBA 0xCE`, Length: 12 + 12*N, ID: `0x11 0x04`, Payload: See below, Checksum: 4 Bytes |

**Payload Content:**

| Offset | Type | Scale | Name | Unit | Description |
| --- | --- | --- | --- | --- | --- |
| 0 | U4 |  | tow | ms | GPS Time of Week |
| 4 | U1 |  | numViewTot |  | Total satellites visible |
| 5 | U1 |  | numFixTot |  | Total satellites used for positioning |
| 6 | U1 |  | res1 |  | Reserved |
| 7 | U1 |  | res2 |  | Reserved |
| 8 | U4 |  | res3 |  | Reserved |
| **Repeat Block (N=0 to numViewTot-1)** |  |  |  |  |  |
| 12+12*N | U1 |  | chn |  | Tracking channel number |
| 13+12*N | U1 |  | svid |  | Satellite ID |
| 14+12*N | U1 |  | gnssid |  | Satellite system ID (see 1.4) |
| 15+12*N | U1 |  | flagx |  | Satellite status flag [1] |
| 16+12*N | U1 |  | quality |  | Signal quality (see 3.7.2) |
| 17+12*N | U1 |  | cn0 | dBHz | Carrier-to-Noise ratio |
| 18+12*N | U1 |  | sigid |  | Signal ID (see 1.4) |
| 19+12*N | U1 |  | elevation | deg | Elevation |
| 20+12*N | U2 |  | azimuth | deg | Azimuth |
| 22+12*N | I2 |  | prResi | dm | Pseudorange residual |
| **End Repeat** |  |  |  |  |  |

**Remark [1]: Satellite Status Flag**

* **B0:** 1 = Satellite used in solution
* **B1-B3:** Reserved
* **B7-B4:**
* 0 = Satellite disabled
* 1 = No prediction info
* 2/3 = Low elevation/invisible
* 4 = Visible, Almanac prediction
* 5 = Visible, Ephemeris prediction (Long term)
* 6 = Visible, AGNSS prediction
* 7 = Visible, Ephemeris prediction





3.9.6 NAV2-TIMEUTC (0x11 0x05) 

| Message | NAV2-TIMEUTC |
| --- | --- |
| **Description** | UTC Time Information |
| **Type** | Periodic/Query |
| **Structure** | Header: `0xBA 0xCE`, Length: 20, ID: `0x11 0x05`, Payload: See below, Checksum: 4 Bytes |

**Payload Content:**

| Offset | Type | Scale | Name | Unit | Description |
| --- | --- | --- | --- | --- | --- |
| 0 | R4 |  | tAcc | ns | Receiver time error estimate |
| 4 | I4 | 2^-30 | subms | ms | Fractional millisecond part (-0.5ms ~ 0.5ms) |
| 8 | I1 |  | subcs | ms | Centisecond error (-5ms ~ 5ms) |
| 9 | U1 |  | cs | cs | Integer centisecond (0-99). Full fractional second = (cs*10 + subcs + subms*2^-30) ms |
| 10 | U2 |  | year |  | Year |
| 12 | U1 |  | month |  | Month |
| 13 | U1 |  | day |  | Day |
| 14 | U1 |  | hour |  | Hour |
| 15 | U1 |  | minute |  | Minute |
| 16 | U1 |  | second |  | Second |
| 17 | U1 |  | tFlagx |  | Comprehensive time flag (see 3.7.3) |
| 18 | U1 |  | tSrc |  | Time source system (see 3.7.4) |
| 19 | I1 |  | leapSec | s | Current leap seconds |



3.9.7 NAV2-SIG (0x11 0x06) 

| Message | NAV2-SIG |
| --- | --- |
| **Description** | Satellite signal information received by receiver |
| **Type** | Periodic/Query |
| **Structure** | Header: `0xBA 0xCE`, Length: 8+16*N, ID: `0x11 0x06`, Payload: See below, Checksum: 4 Bytes |

**Payload Content:**

| Offset | Type | Scale | Name | Unit | Description |
| --- | --- | --- | --- | --- | --- |
| 0 | U4 |  | tow | ms | GPS Time of Week |
| 4 | U1 |  | res1 |  | Reserved |
| 5 | U1 |  | numTrkTot |  | Total signals tracked |
| 6 | U1 |  | numFixTot |  | Total signals used for positioning |
| 7 | U1 |  | res2 |  | Reserved |
| **Repeat Block (N=0 to numTrkTot-1)** |  |  |  |  |  |
| 8+16*N | U1 |  | gnssid |  | System ID (see 1.4) |
| 9+16*N | U1 |  | svid |  | Satellite ID |
| 10+16*N | U1 |  | sigid |  | Signal ID (see 1.4) |
| 11+16*N | U1 |  | freqid |  | GLONASS Freq ID |
| 12+16*N | I2 |  | prResi | dm | Pseudorange residual |
| 14+16*N | U1 |  | cn0 | dBHz | Carrier-to-Noise ratio |
| 15+16*N | U1 |  | trkind |  | Signal quality (see 3.7.2) |
| 16+16*N | U1 |  | corFlagx |  | **Signal Correction Flag**<br>

<br>BIT[6:4] Ionosphere model: 0=NULL; 1=GPS; 2=SBAS; 3=BD2; 4=GAL; 5=BD3; 7=Dual Freq<br>

<br>BIT[2:0] Correction Source: 0=NULL; 1=SBAS; 2=BDS; 3=RTCM2; 4=OSR; 5=SSR |
| 17+16*N | U1 |  | solFlagx |  | **Signal Solution Flag**<br>

<br>BIT0=1: Pseudorange used<br>

<br>BIT1=1: Carrier Phase used<br>

<br>BIT2=1: Doppler used<br>

<br>BIT3=1: Pseudorange smoothing<br>

<br>BIT[7:4] Sat Solution Status: 0=DISABLE; 1=NULL; 2/3=INVISIBLE; 4=ALM; 5=LTE; 6=AGNSS; 7=EPH |
| 18+16*N | U1 |  | chn |  | Tracking channel number |
| 19+16*N | U1 |  | eleDeg | deg | Elevation |
| 20+16*N | U2 |  | aziDeg | deg | Azimuth |
| 22+16*N | I2 |  | ionoDelay | dm | Ionosphere delay correction |
| **End Repeat** |  |  |  |  |  |



3.9.8 NAV2-CLK (0x11 0x07) 

| Message | NAV2-CLK |
| --- | --- |
| **Description** | Receiver time bias and frequency bias |
| **Type** | Periodic/Query |
| **Structure** | Header: `0xBA 0xCE`, Length: 20, ID: `0x11 0x07`, Payload: See below, Checksum: 4 Bytes |

**Payload Content:**

| Offset | Type | Scale | Name | Unit | Description |
| --- | --- | --- | --- | --- | --- |
| 0 | U1 |  | tSrc |  | Satellite system time source (see 3.7.4) |
| 1 | U1 |  | res1 |  | Reserved |
| 2 | U1 |  | towFlag |  | Receiver time valid flag (see 3.7.1) |
| 3 | U1 |  | frqFlag |  | Receiver frequency bias valid flag (see 3.7.1) |
| 4 | I4 |  | clkBias | ns | Current receiver time bias |
| 8 | R4 |  | dfxTcxo | s/s | Receiver TCXO relative frequency bias |
| 12 | R4 |  | tAcc | ns | Receiver time accuracy |
| 16 | R4 |  | fAcc | ppb | Receiver frequency accuracy |



3.9.9 NAV2-RVT (0x11 0x08) 

| Message | NAV2-RVT |
| --- | --- |
| **Description** | Receiver Raw Time Information |
| **Type** | Periodic/Query |
| **Structure** | Header: `0xBA 0xCE`, Length: 52, ID: `0x11 0x08`, Payload: See below, Checksum: 4 Bytes |

**Payload Content:**

| Offset | Type | Scale | Name | Unit | Description |
| --- | --- | --- | --- | --- | --- |
| 0 | I4 |  | rawTow | ms | Raw receiver time (Integer ms of GPS TOW), uncorrected based on TCXO. Accumulates error up to ~10ms, may have ms jumps. |
| 4 | I4 | 2^-30 | rawTowSubms | ms | Fractional ms of raw receiver time. Full time = `rawTow + rawTowSubms*2^-30` ms. |
| 8 | I4 |  | dtuTow | ms | Integer ms of raw receiver time error |
| 12 | I4 | 2^-30 | dtuTowSubms | ms | Fractional ms of raw receiver time error |
| 16 | I2 |  | wn |  | Raw receiver time GPS Week Number |
| 18 | U1 |  | towFlag |  | Time valid flag (see 3.7.1) |
| 19 | U1 |  | wnFlag |  | Week number valid flag (see 3.7.5) |
| 20 | U1 |  | res1 |  | Reserved |
| 21 | U1 |  | ambFlag |  | Receiver integer ms ambiguity flag. 0=No ambiguity. |
| 22 | U1 |  | dtuFlag |  | Receiver time error valid flag |
| 23 | U1 |  | rvtRstTag |  | Receiver clock reset counter |
| 24 | I4 |  | rvtRst | ms | Receiver clock adjustment amount |
| 28 | R4 |  | tAcc | ns | Receiver time accuracy |
| 32 | I4 |  | res5 |  | Reserved |
| 36 | I4 |  | res6 |  | Reserved |
| 40 | R4 |  | dtMeas | s | Time interval from last measurement |
| 44 | I1 |  | res2 |  | Reserved |
| 45 | I1 |  | dtsBds2Gps | s | Integer second offset: BDS to GPS |
| 46 | I1 |  | dtsGln2Gps | s | Integer second offset: GLONASS to GPS |
| 47 | I1 |  | dtsGal2Gps | s | Integer second offset: GALILEO to GPS |
| 48 | I1 |  | dtsIrn2Gps | s | Integer second offset: IRNSS to GPS |
| 49 | U1 |  | res3 |  | Reserved |
| 50 | U2 |  | res4 |  | Reserved |



3.9.10 NAV2-RTC (0x11 0x09) 

| Message | NAV2-RTC |
| --- | --- |
| **Description** | Receiver RTC Time Information |
| **Type** | Periodic/Query |
| **Structure** | Header: `0xBA 0xCE`, Length: 32, ID: `0x11 0x09`, Payload: See below, Checksum: 4 Bytes |

**Payload Content:**

| Offset | Type | Scale | Name | Unit | Description |
| --- | --- | --- | --- | --- | --- |
| 0 | I4 |  | dtRtcTow | ms | RTC Time error, Integer ms |
| 4 | I4 | 2^-30 | dtRtcTowSubms | ms | RTC Time error, Fractional ms |
| 8 | I4 |  | rtcTow | ms | RTC Time, Integer ms |
| 12 | I4 | 2^-30 | rtcTowSubms | ms | RTC Time, Fractional ms |
| 16 | I2 |  | wn |  | RTC Time, GPS Week Number |
| 18 | U1 |  | res1 |  | Reserved |
| 19 | I1 |  | leapSec | s | GPS Leap Seconds |
| 20 | I4 | 2^-16 | dfRtc | Hz | RTC Crystal frequency offset |
| 24 | U1 |  | dfRtcFlag |  | RTC Freq offset calculation valid flag |
| 25 | U1 |  | rtcSrc |  | Source of RTC calibration |
| 26 | I2 |  | res2 |  | Reserved |
| 28 | I4 |  | res3 |  | Reserved |



3.10 TIM2 (0x12) 

Timing product specific messages, containing timing pulse and time system information. 

3.10.1 TIM2-TPX (0x12 0x00) 

| Message | TIM2-TPX |
| --- | --- |
| **Description** | Timing pulse information |
| **Type** | Periodic/Query |
| **Structure** | Header: `0xBA 0xCE`, Length: 24, ID: `0x12 0x00`, Payload: See below, Checksum: 4 Bytes |

**Payload Content:**

| Offset | Type | Scale | Name | Unit | Description |
| --- | --- | --- | --- | --- | --- |
| 0 | U4 |  | tow | ms | GNSS System Time, Integer ms of TOW |
| 4 | I4 | 2^-30 | towSubms | ms | GNSS System Time, Fractional ms of TOW. Current PPS corresponds to `(tow + towSubms*2^-30)` ms |
| 8 | U2 |  | wn |  | GNSS System Time, Week Number |
| 10 | U1 |  | ppsFlagx |  | PPS Pulse Reliability Indicator [1] |
| 11 | U1 |  | tBase |  | **PPS Reference Base**<br>

<br>0=GNSS System<br>

<br>1=UTC |
| 12 | U1 |  | tSrc |  | Receiver timing source (see 3.7.4) |
| 13 | U1 |  | res1 |  | Reserved |
| 14 | U2 |  | res2 |  | Reserved |
| 16 | U2 |  | res3 |  | Reserved |
| 18 | I1 |  | leapSec | s | Current system leap seconds |
| 19 | I1 | 0.1 | quanErr | ns | Current PPS hardware quantization error. Positive means PPS leads integer second. |
| 20 | I2 | 0.1 | tAcc | ns | Current time error estimate |
| 22 | I2 | 0.1 | dt2Utc | ns | Satellite time offset to UTC |

**Remark [1]: PPS Pulse Reliability Indicator**

* **B0:** 1 = TOW available
* **B1:** 1 = Week Number valid
* **B2:** 1 = Leap second info valid
* **B3:** 1 = Time valid
* **B4-B5:** Reserved
* **B6:** 1 = PPS Pulse valid
* **B7:** Reserved




3.10.2 TIM2-TIMEGPS (0x12 0x01) 

| Message | TIM2-TIMEGPS |
| --- | --- |
| **Description** | GPS System Time Information Output |
| **Type** | Periodic/Query |
| **Structure** | Header: `0xBA 0xCE`, Length: 36, ID: `0x12 0x01`, Payload: See below, Checksum: 4 Bytes |

**Payload Content:**

| Offset | Type | Scale | Name | Unit | Description |
| --- | --- | --- | --- | --- | --- |
| 0 | U4 |  | tow | ms | GPS TOW, Integer ms |
| 4 | I4 | 2^-30 | towSubms | ms | GPS TOW, Fractional ms |
| 8 | U2 |  | wn |  | GPS Week Number |
| 10 | U1 |  | towFlag |  | GPS TOW valid flag (see 3.7.1) |
| 11 | U1 |  | wnFlag |  | GPS Week Number valid flag (see 3.7.5) |
| 12 | U4 |  | totSec | s | Total GPS seconds |
| 16 | R4 |  | tAcc | ns | GPS Time error estimate |
| 20 | R4 |  | dt2Utc | ns | Offset between GPS and UTC |
| 24 | I4 |  | dtLsfUtc | s | Time until leap second event |
| 28 | I1 |  | ls | s | Current leap seconds |
| 29 | I1 |  | lsf | s | Forecast leap seconds |
| 30 | U1 |  | tFlagx |  | Time status flag (see 3.7.3) |
| 31 | U1 |  | tSrc |  | Receiver timing source (see 3.7.4) |
| 32 | U1 |  | utcFlag |  | UTC Parameter Valid Flag [1] |
| 33 | U1 |  | lsFlag |  | Leap Second Event Valid Flag [2] |
| 34 | U2 |  | lsYear |  | Leap second event time. BIT[15:1]=Year; BIT0=0 (Jun 30), BIT0=1 (Dec 31) |

**Remark [1]: UTC Parameter Flag**

* 0: No UTC info
* 1: UTC info autonomously updated
* 2: UTC info expired
* 3: UTC info is auxiliary data

**Remark [2]: Leap Second Event Flag**

* 0: No new leap second info
* 1: No leap second event
* 2: Leap second event exists, value normal
* 3: Leap second event exists, value abnormal




3.10.3 TIM2-TIMEBDS (0x12 0x02) 

Same structure as TIM2-TIMEGPS, but for BDS system time.

| Message | TIM2-TIMEBDS |
| --- | --- |
| **Structure** | Header: `0xBA 0xCE`, Length: 36, ID: `0x12 0x02`, Checksum: 4 Bytes |

Payload is identical to 3.10.2, referring to BDS Time/Week. 

3.10.4 TIM2-TIMEGLN (0x12 0x03) 

Same structure as TIM2-TIMEGPS, but for GLONASS system time.

| Message | TIM2-TIMEGLN |
| --- | --- |
| **Structure** | Header: `0xBA 0xCE`, Length: 36, ID: `0x12 0x03`, Checksum: 4 Bytes |

Payload is identical to 3.10.2, referring to GLONASS Time/Week. 

3.10.5 TIM2-TIMEGAL (0x12 0x04) 

Same structure as TIM2-TIMEGPS, but for GALILEO system time.

| Message | TIM2-TIMEGAL |
| --- | --- |
| **Structure** | Header: `0xBA 0xCE`, Length: 36, ID: `0x12 0x04`, Checksum: 4 Bytes |

Payload is identical to 3.10.2, referring to GALILEO Time/Week. 

3.10.6 TIM2-TIMEIRN (0x12 0x05) 

Same structure as TIM2-TIMEGPS, but for IRNSS system time.

| Message | TIM2-TIMEIRN |
| --- | --- |
| **Structure** | Header: `0xBA 0xCE`, Length: 36, ID: `0x12 0x05`, Checksum: 4 Bytes |

Payload is identical to 3.10.2, referring to IRNSS Time/Week. 

3.10.7 TIM2-TIMEPOS (0x12 0x06) 

| Message | TIM2-TIMEPOS |
| --- | --- |
| **Description** | Timing Engine Position Status |
| **Type** | Periodic/Query |
| **Structure** | Header: `0xBA 0xCE`, Length: 64, ID: `0x12 0x06`, Payload: See below, Checksum: 4 Bytes |

**Payload Content:**

| Offset | Type | Scale | Name | Unit | Description |
| --- | --- | --- | --- | --- | --- |
| 0 | R8 |  | xTim | m | Timing engine fixed position X |
| 8 | R8 |  | yTim | m | Timing engine fixed position Y |
| 16 | R8 |  | zTim | m | Timing engine fixed position Z |
| 24 | R8 |  | xFix | m | Positioning engine real-time position X |
| 32 | R8 |  | yFix | m | Positioning engine real-time position Y |
| 40 | R8 |  | zFix | m | Positioning engine real-time position Z |
| 48 | U4 |  | surTimer | s | Self-survey mode running time |
| 52 | R4 |  | surPacc | m | Self-survey position current accuracy |
| 56 | U1 |  | fixFlag |  | Position validity flag (see 3.7.1) |
| 57 | U1 |  | timFixMode |  | Timing Position Fix Mode [1] |
| 58 | U2 |  | prResiRms | m | Pseudorange residual RMS |
| 60 | U2 |  | posBias | m | Deviation between timing position and real-time position |
| 62 | U1 | 0.1 | pdop |  | Position DOP |
| 63 | U1 |  | res |  | Reserved |

**Remark [1]: Timing Position Fix Mode**

* 1: Autonomous Fix Mode
* 2: External Input Position
* 3: Position from Positioning Engine Real-time Position




3.10.8 TIM2-LS (0x12 0x07) 

| Message | TIM2-LS |
| --- | --- |
| **Description** | GNSS Time System UTC Error Information Alarm |
| **Type** | Periodic/Query |
| **Structure** | Header: `0xBA 0xCE`, Length: 16, ID: `0x12 0x07`, Payload: See below, Checksum: 4 Bytes |

**Payload Content:**

| Offset | Type | Scale | Name | Unit | Description |
| --- | --- | --- | --- | --- | --- |
| 0 | U8 |  | utcExpPrnMask |  | UTC Leap Second Exception Satellite PRN Mask. BIT0=PRN1, etc. |
| 8 | U1 |  | gnssid |  | System ID (see 1.4) |
| 9 | U1 |  | sigid |  | Signal ID (see 1.4) |
| 10 | U1 |  | svid |  | Satellite ID |
| 11 | U1 |  | raimType |  | Alarm type (see 3.7.6) |
| 12 | U1 |  | wnlsf |  | Week number of leap second event |
| 13 | U1 |  | dn |  | Day number of leap second event |
| 14 | I1 |  | dtls |  | Leap second value before event |
| 15 | I1 |  | dtlsf |  | Leap second value after event |



3.10.9 TIM2-LY (0x12 0x08) 

| Message | TIM2-LY |
| --- | --- |
| **Description** | GNSS Time System Leap Year Alarm |
| **Type** | Periodic/Query |
| **Structure** | Header: `0xBA 0xCE`, Length: 16, ID: `0x12 0x08`, Payload: See below, Checksum: 4 Bytes |

**Payload Content:**

| Offset | Type | Scale | Name | Unit | Description |
| --- | --- | --- | --- | --- | --- |
| 0 | U8 |  | wntExpPrnMask |  | Leap Year Alarm Mask. BIT0=PRN1... |
| 8 | U1 |  | gnssid |  | System ID (see 1.4) |
| 9 | U1 |  | sigid |  | Signal ID (see 1.4) |
| 10 | U1 |  | svid |  | Satellite ID |
| 11 | U1 |  | raimType |  | Alarm type (see 3.7.6) |
| 12 | I2 |  | wnBias |  | Bias between wrong week number and correct week number |
| 14 | U2 |  | res |  | Reserved |



3.10.10 TIM2-TCXO (0x12 0x09) 

| Message | TIM2-TCXO |
| --- | --- |
| **Description** | TCXO Crystal Frequency Offset Info |
| **Type** | Periodic/Query |
| **Structure** | Header: `0xBA 0xCE`, Length: 20, ID: `0x12 0x09`, Payload: See below, Checksum: 4 Bytes |

**Payload Content:**

| Offset | Type | Scale | Name | Unit | Description |
| --- | --- | --- | --- | --- | --- |
| 0 | R4 |  | dfu_ratio |  | Relative frequency offset of receiver sampling clock |
| 4 | R4 |  | dfu2tcxo |  | Difference between sampling clock and TCXO offset |
| 8 | R4 |  | dfx_ratio |  | TCXO frequency offset. `dfx_ratio = dfu_ratio + dfu2tcxo` |
| 12 | I4 | 2^-28 | vcBias |  | VCTCXO voltage control offset |
| 16 | U1 |  | frqFlag |  | Frequency valid flag (see 3.7.1) |
| 17 | U1 |  | Tcxo_do_cnt |  | VCTCXO taming convergence count |
| 18 | U2 |  | res |  | Reserved |



3.11 RXM2 (0x13) 

Raw observation data including satellite tracking raw measurements, satellite position/velocity, and raw messages.

3.11.1 RXM2-MEASX (0x13 0x00) 

| Message | RXM2-MEASX |
| --- | --- |
| **Description** | Pseudorange, carrier phase raw measurements |
| **Type** | Periodic |
| **Structure** | Header: `0xBA 0xCE`, Length: 16+32*N, ID: `0x13 0x00`, Payload: See below, Checksum: 4 Bytes |

**Payload Content:**

| Offset | Type | Scale | Name | Unit | Description |
| --- | --- | --- | --- | --- | --- |
| 0 | U4 |  | rawTow | ms | Raw receiver time (Integer ms) |
| 4 | I4 | 2^-30 | rawTowSubms | ms | Raw receiver time (Fractional ms) |
| 8 | U2 |  | wn |  | Raw receiver time GPS Week |
| 10 | I1 |  | leapS | s | GPS Leap Seconds |
| 11 | U1 |  | numMeas |  | Total measurements |
| 12 | U1 |  | rvtFlagx |  | Receiver time status flag [1] |
| 13 | U1 |  | tSrc |  | Receiver time source (see 3.7.4) |
| 14 | U1 |  | res1 |  | Reserved |
| 15 | U1 |  | res2 |  | Reserved |
| **Repeat Block (N=0 to numMeas)** |  |  |  |  |  |
| 16+32*N | R8 |  | prMes | m | Pseudorange measurement |
| 24+32*N | R8 |  | cpMes | m | Carrier phase measurement |
| 32+32*N | R4 |  | cpRateMes | m/s | Carrier phase rate measurement |
| 36+32*N | U1 |  | gnssid |  | System ID (see 1.4) |
| 37+32*N | U1 |  | svid |  | Satellite ID |
| 38+32*N | U1 |  | sigid |  | Signal ID (see 1.4) |
| 39+32*N | U1 |  | freqid |  | GLONASS Freq ID [-7, +6] mapped to [1, 14] |
| 40+32*N | U2 |  | cpLockTime | ms | Carrier phase lock time (max 65535) |
| 42+32*N | U1 |  | cn0 | dBHz | Carrier-to-Noise ratio |
| 43+32*N | U1 |  | prRms | m | Pseudorange tracking error |
| 44+32*N | U1 |  | doRms | dm/s | Doppler tracking error |
| 45+32*N | U1 |  | res3 |  | Reserved |
| 46+32*N | U1 |  | trkind |  | Satellite tracking status indicator [2] |
| 47+32*N | U1 |  | chn |  | Tracking channel number |
| **End Repeat** |  |  |  |  |  |

**Remark [1]: Receiver Time Status Flag**

* **B0:** 1 = Receiver TOW available
* **B1:** 1 = Receiver Week valid
* **B2:** 1 = Leap second valid
* **B3:** 1 = Receiver time valid and reliable
* **B4:** 1 = Receiver clock jump occurred (rawTow integer ms jump)

**Remark [2]: Satellite Tracking Status Indicator**

* **B0:** 1 = Pseudorange valid
* **B1:** 1 = Carrier phase valid
* **B2:** 1 = Half-cycle ambiguity resolved
* **B3:** 1 = Half-cycle ambiguity exists and subtracted
* **B4:** 1 = No integer ms ambiguity in pseudorange
* **B5:** 1 = Satellite ephemeris/position valid
* **B6:** 1 = Satellite elevation low




3.11.2 RXM2-SVPOS (0x13 0x01) 

| Message | RXM2-SVPOS |
| --- | --- |
| **Description** | Satellite position information (all satellites) |
| **Type** | Periodic |
| **Structure** | Header: `0xBA 0xCE`, Length: 16+56*numSat, ID: `0x13 0x01`, Payload: See below, Checksum: 4 Bytes |

**Payload Content:**

| Offset | Type | Scale | Name | Unit | Description |
| --- | --- | --- | --- | --- | --- |
| 0 | U4 |  | rawTow | ms | Raw receiver time (Integer ms) |
| 4 | I4 | 2^-30 | rawTowSubms | ms | Raw receiver time (Fractional ms) |
| 8 | U2 |  | wn |  | Raw receiver time GPS Week |
| 10 | U1 |  | numSat |  | Number of satellites |
| 11 | U1 |  | res1 |  | Reserved |
| 12 | U4 |  | res2 |  | Reserved |
| **Repeat Block (N=0 to numSat-1)** |  |  |  |  |  |
| 16+56*N | R8 |  | x | m | Sat ECEF-X |
| 24+56*N | R8 |  | y | m | Sat ECEF-Y |
| 32+56*N | R8 |  | z | m | Sat ECEF-Z |
| 40+56*N | R4 |  | vx | m/s | Sat Velocity ECEF-X |
| 44+56*N | R4 |  | vy | m/s | Sat Velocity ECEF-Y |
| 48+56*N | R4 |  | vz | m/s | Sat Velocity ECEF-Z |
| 52+56*N | R4 |  | svdf | m/s | Satellite frequency bias |
| 56+56*N | R8 |  | svdt | m | Satellite clock bias |
| 64+56*N | U1 |  | gnssid |  | System ID (see 1.4) |
| 65+56*N | U1 |  | svid |  | Satellite ID |
| 66+56*N | U1 |  | sigid |  | Signal ID (see 1.4) |
| 67+56*N | U1 |  | glnFreqid |  | GLONASS Freq ID |
| 68+56*N | U2 |  | iode |  | Ephemeris Age |
| 70+56*N | U1 |  | res3 |  | Reserved |
| 71+56*N | U1 |  | svpFlagx |  | Validity flag. BIT6=1 (Valid), BIT7=1 (Valid & SSR corrected) |
| **End Repeat** |  |  |  |  |  |



3.11.3 RXM2-SFRBX (0x13 0x06) 

| Message | RXM2-SFRBX |
| --- | --- |
| **Description** | Raw satellite message (decoded complete subframe/message) |
| **Type** | Periodic |
| **Structure** | Header: `0xBA 0xCE`, Length: 8+4*numWords, ID: `0x13 0x06`, Payload: See below, Checksum: 4 Bytes |

**Payload Content:**

| Offset | Type | Scale | Name | Unit | Description |
| --- | --- | --- | --- | --- | --- |
| 0 | U1 |  | gnssid |  | System ID |
| 1 | U1 |  | svid |  | Satellite ID |
| 2 | U1 |  | sigid |  | Signal ID |
| 3 | U1 |  | freqid |  | GLONASS Freq ID |
| 4 | U1 |  | numWords |  | Number of words in frame |
| 5 | U1 |  | chn |  | Tracking channel |
| 6 | U1 |  | res2 |  | Reserved |
| 7 | U1 |  | sfid |  | Current subframe ID |
| **Repeat Block (N=0 to numWords-1)** |  |  |  |  |  |
| 8+N*4 | U4 |  | words |  | Message data words |



3.11.4 RXM2-SVP (0x13 0x0A) 

| Message | RXM2-SVP |
| --- | --- |
| **Description** | Satellite position information (single satellite) |
| **Type** | Periodic |
| **Structure** | Header: `0xBA 0xCE`, Length: 60, ID: `0x13 0x0A`, Payload: See below, Checksum: 4 Bytes |

**Payload Content:**

| Offset | Type | Scale | Name | Unit | Description |
| --- | --- | --- | --- | --- | --- |
| 0 | U4 |  | svpTow | ms | Receiver TOW (Reference time for info) |
| 4 | I2 |  | wn |  | Receiver Week Number |
| 6 | U1 |  | gnssid |  | System ID |
| 7 | U1 |  | svid |  | Satellite ID |
| 8 | R8 |  | x | m | Sat ECEF-X |
| 16 | R8 |  | y | m | Sat ECEF-Y |
| 24 | R8 |  | z | m | Sat ECEF-Z |
| 32 | R4 |  | vx | m/s | Sat Velocity ECEF-X |
| 36 | R4 |  | vy | m/s | Sat Velocity ECEF-Y |
| 40 | R4 |  | vz | m/s | Sat Velocity ECEF-Z |
| 48 | R4 |  | svdf | m/s | Sat Frequency bias |
| 52 | R8 |  | svdt | m | Sat Clock bias |



3.12 ACK (0x05) 

ACK and NACK messages used to reply to received CFG messages.

3.12.1 ACK-NACK (0x05 0x00) 

| Message | ACK-NACK |
| --- | --- |
| **Description** | Response for incorrectly received message |
| **Type** | Response |
| **Structure** | Header: `0xBA 0xCE`, Length: 4, ID: `0x05 0x00`, Payload: See below, Checksum: 4 Bytes |

**Payload Content:**

| Offset | Type | Scale | Name | Unit | Description |
| --- | --- | --- | --- | --- | --- |
| 0 | U1 |  | clsID |  | Class ID of the rejected message |
| 1 | U1 |  | msgID |  | Message ID of the rejected message |
| 2 | U2 |  | res |  | Reserved |



3.12.2 ACK-ACK (0x05 0x01) 

| Message | ACK-ACK |
| --- | --- |
| **Description** | Response for correctly received message |
| **Type** | Response |
| **Structure** | Header: `0xBA 0xCE`, Length: 4, ID: `0x05 0x01`, Payload: See below, Checksum: 4 Bytes |

**Payload Content:**

| Offset | Type | Scale | Name | Unit | Description |
| --- | --- | --- | --- | --- | --- |
| 0 | U1 |  | clsID |  | Class ID of the accepted message |
| 1 | U1 |  | msgID |  | Message ID of the accepted message |
| 2 | U2 |  | res |  | Reserved |



3.13 CFG (0x06) 

Configuration messages. When length is 0, it represents a query.

3.13.1 CFG-PRT (0x06 0x00) 

| Message | CFG-PRT |
| --- | --- |
| **Description** | Query/Set UART working mode |
| **Type** | Set/Response Query |
| **Structure (Query)** | Header: `0xBA 0xCE`, Length: 0, ID: `0x06 0x00` |
| **Structure (Set/Resp)** | Header: `0xBA 0xCE`, Length: 8, ID: `0x06 0x00`, Payload: See below |

**Payload Content:**

| Offset | Type | Scale | Name | Unit | Description |
| --- | --- | --- | --- | --- | --- |
| 0 | U1 |  | portID |  | Port ID (0=UART0, 1=UART1, 0xFF=Current) |
| 1 | U1 |  | protoMask |  | Protocol Control Mask [1] |
| 2 | U2 |  | mode |  | UART Mode Mask [2] |
| 4 | U4 |  | baudRate | bps | Baud Rate |

**Remark [1]: Protocol Control Mask**

* B0: 1=CASBIN Input
* B1: 1=NMEA Input
* B3: 1=RTCM Input
* B4: 1=CASBIN Output
* B5: 1=NMEA Output
* B7: 1=RTCM Output

**Remark [2]: UART Mode Mask**

* **B7:B6:** Data Bits. `00`=5, `01`=6, `10`=7, `11`=8
* **B11:B9:** Parity. `10x`=None, `001`=Odd, `000`=Even
* **B13:B12:** Stop Bits. `00`=1, `01`=1.5, `10`=2




3.13.2 CFG-MSG (0x06 0x01) 

| Message | CFG-MSG |
| --- | --- |
| **Description** | Query/Set message transmission frequency |
| **Type** | Set/Query |
| **Structure (Query)** | Header: `0xBA 0xCE`, Length: 0, ID: `0x06 0x01` |
| **Structure (Set)** | Header: `0xBA 0xCE`, Length: 4, ID: `0x06 0x01`, Payload: See below |

**Payload Content:**

| Offset | Type | Scale | Name | Unit | Description |
| --- | --- | --- | --- | --- | --- |
| 0 | U1 |  | clsID |  | Message Class |
| 1 | U1 |  | msgID |  | Message ID |
| 2 | U2 |  | rate |  | **Output Rate:**<br>

<br>0: Do not output<br>

<br>1: Output once per positioning<br>

<br>N: Output once per N positioning<br>

<br>0xFFFF: Output immediately once (Query) |



3.13.3 CFG-RST (0x06 0x02) 

| Message | CFG-RST |
| --- | --- |
| **Description** | Restart receiver / Clear data |
| **Type** | Set |
| **Structure** | Header: `0xBA 0xCE`, Length: 4, ID: `0x06 0x02`, Payload: See below |

**Payload Content:**

| Offset | Type | Scale | Name | Unit | Description |
| --- | --- | --- | --- | --- | --- |
| 0 | U2 |  | res1 |  | Reserved |
| 2 | U1 |  | res2 |  | Reserved |
| 3 | U1 |  | resetMode |  | **Reset Mode:**<br>

<br>0: Hot start<br>

<br>1: Warm start<br>

<br>2: Cold start<br>

<br>3: Factory reset |



3.13.4 CFG-TP (0x06 0x03) 

| Message | CFG-TP |
| --- | --- |
| **Description** | Query/Set Time Pulse Parameters |
| **Type** | Query/Set |
| **Structure (Query)** | Header: `0xBA 0xCE`, Length: 0, ID: `0x06 0x03` |
| **Structure (Set)** | Header: `0xBA 0xCE`, Length: 16, ID: `0x06 0x03`, Payload: See below |

**Payload Content:**

| Offset | Type | Scale | Name | Unit | Description |
| --- | --- | --- | --- | --- | --- |
| 0 | U4 |  | ppsInterval | us | PPS Interval (Period) |
| 4 | U4 |  | ppsWidth | us | PPS Width |
| 8 | U1 |  | ppsOutMode |  | PPS Output Mode [1] |
| 9 | U1 |  | polar |  | PPS Polarity: 0=Rising edge align, 1=Falling edge align |
| 10 | U1 |  | tBase |  | PPS Base: 0=GNSS, 1=UTC |
| 11 | U1 |  | tSrcMode |  | Time Source Selection Mode [2] |
| 12 | R4 |  | userDelay | s | User time delay |

**Remark [1]: PPS Output Mode**

* 0: Always Off
* 1: Time PPS (Output if time not null, accuracy not guaranteed)
* 2: Satellite PPS (Sync with satellite signal, error < 10ms)
* 3: Position PPS (Output if pos/time valid)
* 5: Timing PPS (Output if pos/time valid & reliable)
* 7: Always On

**Remark [2]: Time Source Selection Mode**

* 0-3: Force GPS/BDS/GLN/GAL
* 4-8: Primary BDS/GPS/GLN/GAL/IRN (Auto switch if unavailable)
* 9: Auto select




3.13.5 CFG-RATE (0x06 0x04) 

| Message | CFG-RATE |
| --- | --- |
| **Description** | Query/Set positioning interval |
| **Type** | Query/Set |
| **Structure (Query)** | Header: `0xBA 0xCE`, Length: 0, ID: `0x06 0x04` |
| **Structure (Set)** | Header: `0xBA 0xCE`, Length: 4, ID: `0x06 0x04`, Payload: See below |

**Payload Content:**

| Offset | Type | Scale | Name | Unit | Description |
| --- | --- | --- | --- | --- | --- |
| 0 | U2 |  | fixIntervalMs | ms | Interval (e.g., 1000=1Hz, 200=5Hz) |
| 2 | U1 |  | fixRateHz |  | Rate (e.g., 1=1Hz, 10=10Hz) |
| 3 | U1 |  | res |  | Reserved |



3.13.6 CFG-CFG (0x06 0x05) 

| Message | CFG-CFG |
| --- | --- |
| **Description** | Clear, Save, Load Configuration |
| **Type** | Set |
| **Structure** | Header: `0xBA 0xCE`, Length: 4, ID: `0x06 0x05`, Payload: See below |

**Payload Content:**

| Offset | Type | Scale | Name | Unit | Description |
| --- | --- | --- | --- | --- | --- |
| 0 | U2 |  | res1 |  | Reserved |
| 2 | U1 |  | opMode |  | **Operation Mode:**<br>

<br>0: Clear Flash config<br>

<br>1: Save current to Flash<br>

<br>2: Load Flash to current |
| 3 | U1 |  | res2 |  | Reserved |



3.13.7 CFG-NAVLIMIT (0x06 0x0A) 

| Message | CFG-NAVLIMIT |
| --- | --- |
| **Description** | Query/Set satellite filtering rules for navigation |
| **Type** | Query/Set |
| **Structure (Query)** | Header: `0xBA 0xCE`, Length: 0, ID: `0x06 0x0A` |
| **Structure (Set)** | Header: `0xBA 0xCE`, Length: 8, ID: `0x06 0x0A`, Payload: See below |

**Payload Content:**

| Offset | Type | Scale | Name | Unit | Description |
| --- | --- | --- | --- | --- | --- |
| 0 | U1 |  | minSVs |  | Min satellites for positioning |
| 1 | U1 |  | maxSVs |  | Max satellites for positioning |
| 2 | U1 |  | minCNO |  | Min C/N0 for positioning |
| 3 | I1 |  | minEle | deg | Min Elevation for positioning |
| 4 | U4 |  | res |  | Reserved |



3.13.8 CFG-NAVMODE (0x06 0x0B) 

| Message | CFG-NAVMODE |
| --- | --- |
| **Description** | Query/Set navigation mode |
| **Type** | Query/Set |
| **Structure (Query)** | Header: `0xBA 0xCE`, Length: 0, ID: `0x06 0x0B` |
| **Structure (Set)** | Header: `0xBA 0xCE`, Length: 16, ID: `0x06 0x0B`, Payload: See below |

**Payload Content:**

| Offset | Type | Scale | Name | Unit | Description |
| --- | --- | --- | --- | --- | --- |
| 0 | U1 |  | dynamic |  | **Dynamic Mode:**<br>

<br>0=Portable, 1=Static, 2=Pedestrian, 3=Automotive, 4=Sea, 5=Air <1g, 6=Air <2g, 7=Air <4g |
| 1 | U1 |  | fixMode |  | **Fix Mode:** 0=Reserved, 1=2D, 2=3D, 3=Auto 2D/3D |
| 2 | U1 |  | initFix3D |  | Initial fix must be 3D? (1=Yes, 0=No/2D allowed) |
| 3 | U1 |  | drLimit | s | Max DR duration without satellites (x1200s?? text says "drTh*1200s" in CFG-INS, here just says "duration") |
| 4 | R4 |  | fixedAlt | m | Fixed altitude for 2D mode |
| 8 | R4 |  | fixedAltAcc | m | Altitude error for 2D mode |
| 12 | U1 |  | altAidEn |  | Altitude Aiding (0=Off, 1=On) |
| 13 | U1 |  | res1 |  | Reserved |
| 14 | U2 |  | res2 |  | Reserved |



3.13.9 CFG-NAVFLT (0x06 0x0C) 

| Message | CFG-NAVFLT |
| --- | --- |
| **Description** | Query/Set navigation thresholds |
| **Type** | Query/Set |
| **Structure (Query)** | Header: `0xBA 0xCE`, Length: 0, ID: `0x06 0x0C` |
| **Structure (Set)** | Header: `0xBA 0xCE`, Length: 20, ID: `0x06 0x0C`, Payload: See below |

**Payload Content:**

| Offset | Type | Scale | Name | Unit | Description |
| --- | --- | --- | --- | --- | --- |
| 0 | R4 |  | maxPdop |  | Max allowed PDOP |
| 1 | R4 |  | maxTdop |  | Max allowed TDOP |
| 2 | R4 |  | maxPacc | m | Max allowed Position Accuracy |
| 3 | R4 |  | maxTacc | m | Max allowed Time Accuracy |
| 4 | R4 |  | staticSpdTh | m/s | Static speed threshold |



3.13.10 CFG-WNREF (0x06 0x0D) 

| Message | CFG-WNREF |
| --- | --- |
| **Description** | Query/Set GPS Week Reference |
| **Type** | Query/Set |
| **Structure (Query)** | Header: `0xBA 0xCE`, Length: 0, ID: `0x06 0x0D` |
| **Structure (Set)** | Header: `0xBA 0xCE`, Length: 4, ID: `0x06 0x0D`, Payload: See below |

**Payload Content:**

| Offset | Type | Scale | Name | Unit | Description |
| --- | --- | --- | --- | --- | --- |
| 0 | U2 |  | wnGpsRef | week | GPS Week Ref. Used to resolve 1024 week ambiguity. Valid range +/- 512 weeks from this ref. |
| 2 | U2 |  | res |  | Reserved |



3.13.11 CFG-INS (0x06 0x0E) 

| Message | CFG-INS |
| --- | --- |
| **Description** | Query/Set INS installation mode |
| **Type** | Query/Set |
| **Structure (Query)** | Header: `0xBA 0xCE`, Length: 0, ID: `0x06 0x0E` |
| **Structure (Set)** | Header: `0xBA 0xCE`, Length: 4, ID: `0x06 0x0E`, Payload: See below |

**Payload Content:**

| Offset | Type | Scale | Name | Unit | Description |
| --- | --- | --- | --- | --- | --- |
| 0 | U1 |  | insMask |  | BIT0: INS Enable; BIT1: Back RAM Enable; BIT2: IMU Output; BIT3: Back Flash Enable; BIT4-7 Reserved |
| 1 | U1 |  | res1 |  | Reserved |
| 2 | U1 |  | res2 |  | Reserved |
| 3 | U1 |  | drTh |  | DR time threshold. No GNSS max DR time = drTh * 1200 sec |



3.13.12 CFG-NAVBAND (0x06 0x0F) 

| Message | CFG-NAVBAND |
| --- | --- |
| **Description** | Query/Set available satellite systems/signals |
| **Type** | Query/Set |
| **Structure (Query)** | Header: `0xBA 0xCE`, Length: 0, ID: `0x06 0x0F` |
| **Structure (Set)** | Header: `0xBA 0xCE`, Length: 12, ID: `0x06 0x0F`, Payload: See below |

**Payload Content:**

| Offset | Type | Scale | Name | Unit | Description |
| --- | --- | --- | --- | --- | --- |
| 0 | U1 |  | sigBandAuto |  | Auto signal band selection (1=On, 0=Off) |
| 1 | U1 |  | res1 |  | Reserved |
| 2 | U2 |  | res2 |  | Reserved |
| 4 | U4 |  | sigidMaskFix |  | Positioning Signal List (Valid if Auto=0). See 1.4 for BITs. |
| 8 | U4 |  | sigidMask |  | Supported Reception Signal List. See 1.4 for BITs. |



3.13.13 CFG-JSM (0x06 0x10) 

| Message | CFG-JSM |
| --- | --- |
| **Description** | Query/Set Anti-Jamming/Anti-Spoofing Mode |
| **Type** | Query/Set |
| **Structure (Query)** | Header: `0xBA 0xCE`, Length: 0, ID: `0x06 0x10` |
| **Structure (Set)** | Header: `0xBA 0xCE`, Length: 4, ID: `0x06 0x10`, Payload: See below |

**Payload Content:**

| Offset | Type | Scale | Name | Unit | Description |
| --- | --- | --- | --- | --- | --- |
| 0 | U1 |  | spoofEn |  | **Anti-Spoofing Control:**<br>

<br>B7-B4: Spoofing Sat Count Threshold<br>

<br>B3-B2: Mode (0=High Sensitivity, 1=Fast, 2=Standard)<br>

<br>B1-B0: Enable (1=On, 0=Off) |
| 1 | U1 |  | jamEnMask |  | **Jamming Detection Enable Mask:**<br>

<br>B0: RF Channel 0 (1575)<br>

<br>B1: RF Channel 1 (1561)<br>

<br>B2: RF Channel 2 (1602)<br>

<br>B3: RF Channel 3 |
| 2 | U1 |  | jamThres | dB | Jamming power threshold over signal |
| 3 | U1 |  | agcSetMode |  | RF Link Gain Mode (1=Gain Learning Mode - use when antenna changes) |



3.13.14 CFG-CWI (0x06 0x11) 

| Message | CFG-CWI |
| --- | --- |
| **Description** | Query/Set Anti-Jamming Parameters |
| **Type** | Query/Set |
| **Structure (Query)** | Header: `0xBA 0xCE`, Length: 0, ID: `0x06 0x11` |
| **Structure (Set)** | Header: `0xBA 0xCE`, Length: 4, ID: `0x06 0x11`, Payload: See below |

**Payload Content:**

| Offset | Type | Scale | Name | Unit | Description |
| --- | --- | --- | --- | --- | --- |
| 0 | U1 |  | cwiNotchDisable |  | Notch Filter Disable (0=Enable, 1=Disable) |
| 1 | U1 |  | cwiNotchBw |  | Notch Filter Bandwidth Control Word |
| 2 | U1 |  | cwiCN0Th | dB | CN0 Threshold for Jamming Decision |
| 3 | U1 |  | dif_mask |  | Filter Signal Enable Control: B0=GPS L1C/A, B1=BDS B1I |



3.13.15 CFG-NMEA (0x06 0x12) 

| Message | CFG-NMEA |
| --- | --- |
| **Description** | Query/Set NMEA Output Configuration |
| **Type** | Query/Set |
| **Structure (Query)** | Header: `0xBA 0xCE`, Length: 0, ID: `0x06 0x12` |
| **Structure (Set)** | Header: `0xBA 0xCE`, Length: 8, ID: `0x06 0x12`, Payload: See below |

**Payload Content:**

| Offset | Type | Scale | Name | Unit | Description |
| --- | --- | --- | --- | --- | --- |
| 0 | U1 |  | nmeaVer |  | Version: 0=V2.2, 1=V4.0 (compat V2.3), 2=V4.10, 3=V4.11 |
| 1 | U1 |  | latLonReso |  | Lat/Lon Decimal Places |
| 2 | U1 |  | heightReso |  | Height Decimal Places |
| 3 | U1 |  | gsaPlus |  | Max GSA sentences per system |
| 4 | U1 |  | nmeaValidOpen |  | **PVT Output Mode:**<br>

<br>B0=1 (Only valid PVT), B0=0 (Always)<br>

<br>B1=1 (Heading Hold), B1=0 (Only valid Heading) |
| 5 | U1 |  | res |  | Reserved |
| 6 | U2 |  | res2 |  | Reserved |



3.13.16 CFG-RTCM (0x06 0x14) 

| Message | CFG-RTCM |
| --- | --- |
| **Description** | Query/Set RTCM Output Configuration |
| **Type** | Query/Set |
| **Structure (Query)** | Header: `0xBA 0xCE`, Length: 0, ID: `0x06 0x14` |
| **Structure (Set)** | Header: `0xBA 0xCE`, Length: 16, ID: `0x06 0x14`, Payload: See below |

**Payload Content:**

| Offset | Type | Scale | Name | Unit | Description |
| --- | --- | --- | --- | --- | --- |
| 0 | U4 |  | rtcm_msg_en |  | **Message Enable:**<br>

<br>B0=1005, B2=GPS Eph, B3=BDS Eph, B4=QZSS Eph, B5=GAL FNAV, B6=GAL INAV, B13=GPS MSM, B17=GAL MSM, B19=QZSS MSM, B21=BDS MSM |
| 4 | U1 |  | rtcm_msm_ver |  | MSM Version: 4, 5, 6, 7 (other) |
| 5 | U1 |  | res |  | Reserved |
| 6 | U2 |  | res2 |  | Reserved |
| 8 | U4 |  | res3 |  | Reserved |
| 12 | U4 |  | res4 |  | Reserved |



3.13.16 CFG-TMODE2 (0x06 0x16) 

*(Note: Duplicate section number in source, likely should be 3.13.17)*

| Message | CFG-TMODE2 |
| --- | --- |
| **Description** | Query/Set Timing Mode |
| **Type** | Query/Set |
| **Structure (Query)** | Header: `0xBA 0xCE`, Length: 0, ID: `0x06 0x16` |
| **Structure (Set)** | Header: `0xBA 0xCE`, Length: 28, ID: `0x06 0x16`, Payload: See below |

**Payload Content:**

| Offset | Type | Scale | Name | Unit | Description |
| --- | --- | --- | --- | --- | --- |
| 0 | U1 |  | timFixMode |  | **Pos Mode:** 0=Real-time, 1=Optimized (Auto-survey), 2=Fixed Position |
| 1 | U1 |  | bandMode |  | **Band:** 0=L1+B1I, 1=L1, 2=L2, 3=L5, 4=Multi-band |
| 2 | U1 |  | antDetMode |  | Antenna Detect: 0=Internal, 1=External Pin |
| 3 | U1 |  | tsrc_mode |  | **Source:** 0-3 Force Single Sys, 4-7 Priority Sys |
| 4 | I4 | 0.01 | xFixed | m | ECEF X Fixed |
| 8 | I4 | 0.01 | yFixed | m | ECEF Y Fixed |
| 12 | I4 | 0.01 | zFixed | m | ECEF Z Fixed |
| 16 | U4 |  | fixedPacc | mm | Position Accuracy |
| 20 | U4 |  | svinMinDur | s | Min Survey-in Duration |
| 24 | U4 |  | svinPaccLim | mm | Survey-in Accuracy Limit |



3.13.17 CFG-SATMASK (0x06 0x21) 

| Message | CFG-SATMASK |
| --- | --- |
| **Description** | Query/Set Satellite Enable Masks |
| **Type** | Query/Set |
| **Structure (Query)** | Header: `0xBA 0xCE`, Length: 0, ID: `0x06 0x21` |
| **Structure (Set)** | Header: `0xBA 0xCE`, Length: 56, ID: `0x06 0x21`, Payload: See below |

**Payload Content:**

| Offset | Type | Scale | Name | Unit | Description |
| --- | --- | --- | --- | --- | --- |
| 0 | R8 |  | GPSMask |  | BIT0=PRN1... |
| 8 | R8 |  | BDSMask |  |  |
| 16 | R8 |  | GLNMask |  |  |
| 24 | R8 |  | GALMask |  |  |
| 32 | R8 |  | QZSMask |  |  |
| 40 | R8 |  | SBSMask |  |  |
| 48 | R8 |  | IRNMask |  |  |



3.13.18 CFG-TGDU (0x06 0x22) 

| Message | CFG-TGDU |
| --- | --- |
| **Description** | Query/Set Hardware Delay (TGD) |
| **Type** | Query/Set |
| **Structure (Query)** | Header: `0xBA 0xCE`, Length: 0, ID: `0x06 0x22` |
| **Structure (Set)** | Header: `0xBA 0xCE`, Length: 48, ID: `0x06 0x22`, Payload: See below |

**Payload Content:**

| Offset | Type | Scale | Name | Unit | Description |
| --- | --- | --- | --- | --- | --- |
| 0 | I2 |  | gps_l1i_tgd | ns | GPS L1C/A |
| 2 | I2 |  | gps_l2c_tgd | ns | GPS L2C |
| 4 | I2 |  | gps_l5q_tgd | ns | GPS L5Q |
| 6 | I2 |  | sbs_s1i_tgd | ns | SBAS L1 |
| 8 | I2 |  | sbs_s5i_tgd | ns | SBAS L5 |
| 10 | I2 |  | gln_r1f_tgd | ns | GLN L1 |
| 12 | I2 |  | gln_r2f_tgd | ns | GLN L2 |
| 14 | I2 |  | gal_e1i_tgd | ns | GAL E1 |
| 16 | I2 |  | gal_e5a_tgd | ns | GAL E5A |
| 18 | I2 |  | gal_e5b_tgd | ns | GAL E5B |
| 20 | I2 |  | bds_b1g_tgd | ns | BDS B1I GEO |
| 22 | I2 |  | bds_b1m_tgd | ns | BDS B1I MEO |
| 24 | I2 |  | bds_b3g_tgd | ns | BDS B3I GEO |
| 26 | I2 |  | bds_b3m_tgd | ns | BDS B3I MEO |
| 28 | I2 |  | bds_b1c_tgd | ns | BDS B1C |
| 30 | I2 |  | bds_b2a_tgd | ns | BDS B2A |
| 32 | I2 |  | bds_b2b_tgd | ns | BDS B2B |
| 34 | I2 |  | bds_b2g_tgd | ns | BDS B2I GEO |
| 36 | I2 |  | bds_b2m_tgd | ns | BDS B2I MEO |
| 38 | I2 |  | qzs_q1i_tgd | ns | QZSS L1C/A |
| 40 | I2 |  | qzs_q2c_tgd | ns | QZSS L2C |
| 42 | I2 |  | qzs_q5q_tgd | ns | QZSS L5Q |
| 44 | I2 |  | qzs_q1s_tgd | ns | QZSS L1S |



3.13.19 CFG-SBAS (0x06 0x23) 

| Message | CFG-SBAS |
| --- | --- |
| **Description** | Query/Set SBAS Configuration |
| **Type** | Query/Set |
| **Structure (Query)** | Header: `0xBA 0xCE`, Length: 0, ID: `0x06 0x23` |
| **Structure (Set)** | Header: `0xBA 0xCE`, Length: 16, ID: `0x06 0x23`, Payload: See below |

**Payload Content:**

| Offset | Type | Scale | Name | Unit | Description |
| --- | --- | --- | --- | --- | --- |
| 0 | U1 |  | SbasCorrMask |  | BIT0=1 Enable SBAS Grid Correction |
| 1 | U1 |  | Res1 |  | Reserved |
| 2 | U2 |  | Res2 |  | Reserved |
| 4 | U4 |  | Res3 |  | Reserved |
| 8 | U4 |  | Res4 |  | Reserved |
| 12 | U4 |  | Res5 |  | Reserved |



3.14 MSG (0x08) 

Satellite navigation messages, generally used as input protocol for AGNSS services. Message class is 0x08.

3.14.1 MSG-BDSUTC (0x08 0x00) 

| Message | MSG-BDSUTC |
| --- | --- |
| **Description** | BDS UTC Data |
| **Type** | Input |
| **Structure** | Header: `0xBA 0xCE`, Length: 20, ID: `0x08 0x00`, Payload: See below, Checksum: 4 Bytes |

**Payload Content:**

| Offset | Type | Scale | Name | Unit | Description |
| --- | --- | --- | --- | --- | --- |
| 0 | U4 |  | res1 |  | Reserved |
| 4 | I4 | 2^-30 | a0UTC | s | BDT Clock bias relative to UTC |
| 8 | I4 | 2^-50 | a1UTC | s/s | BDT Clock rate relative to UTC |
| 12 | I1 |  | dtls | s | Accumulated leap seconds (before update) |
| 13 | I1 |  | dtlsf | s | Accumulated leap seconds (after update) |
| 14 | U1 |  | res2 |  | Reserved |
| 15 | U1 |  | res3 |  | Reserved |
| 16 | U1 |  | wnlsf | week | Week number of leap second effect |
| 17 | U1 |  | dn | day | Day number of leap second effect |
| 18 | U1 |  | valid |  | Flag: 0=Invalid, 1=Unhealthy, 2=Expired, 3=Valid |
| 19 | U1 |  | res4 |  | Reserved |



3.14.2 MSG-BDSION (0x08 0x01) 

| Message | MSG-BDSION |
| --- | --- |
| **Description** | BDS 8-parameter Ionosphere Data |
| **Type** | Input |
| **Structure** | Header: `0xBA 0xCE`, Length: 16, ID: `0x08 0x01`, Payload: See below, Checksum: 4 Bytes |

**Payload Content:**

| Offset | Type | Scale | Name | Unit | Description |
| --- | --- | --- | --- | --- | --- |
| 0 | U4 |  | res1 |  | Reserved |
| 4 | I1 | 2^-30 | alpha0 | s | Ionosphere Parameter |
| 5 | I1 | 2^-27 | alpha1 | s/pi |  |
| 6 | I1 | 2^-24 | alpha2 | s/pi^2 |  |
| 7 | I1 | 2^-24 | alpha3 | s/pi^3 |  |
| 8 | I1 | 2^11 | beta0 | s |  |
| 9 | I1 | 2^14 | beta1 | s/pi |  |
| 10 | I1 | 2^16 | beta2 | s/pi^2 |  |
| 11 | I1 | 2^16 | beta3 | s/pi^3 |  |
| 12 | U1 |  | valid |  | Flag: 0-3 (see above) |
| 13 | U1 |  | res2 |  | Reserved |
| 14 | U2 |  | res3 |  | Reserved |



3.14.3 MSG-BDSEPH (0x08 0x02) 

| Message | MSG-BDSEPH |
| --- | --- |
| **Description** | BDS Ephemeris |
| **Type** | Input |
| **Structure** | Header: `0xBA 0xCE`, Length: 92, ID: `0x08 0x02`, Payload: See below, Checksum: 4 Bytes |

**Payload Content:**

| Offset | Type | Scale | Name | Unit | Description |
| --- | --- | --- | --- | --- | --- |
| 0 | U4 |  | res1 |  | Reserved |
| 4 | U4 | 2^-19 | sqrtA | m^1/2 | Sqrt Semi-major axis |
| 8 | U4 | 2^-33 | e |  | Eccentricity |
| 12 | I4 | 2^-31 | w | pi | Arg of Perigee |
| 16 | I4 | 2^-31 | M0 | pi | Mean Anomaly at Ref Time |
| 20 | I4 | 2^-31 | i0 | pi | Inclination at Ref Time |
| 24 | I4 | 2^-31 | Omega0 | pi | Longitude of Ascending Node at Ref Time |
| 28 | I4 | 2^-43 | OmegaDot | pi/s | Rate of Right Ascension |
| 32 | I2 | 2^-43 | deltaN | pi/s | Mean Motion Diff |
| 34 | I2 | 2^-43 | IDOT | pi/s | Rate of Inclination |
| 36 | I4 | 2^-31 | cuc | rad | Cosine Harmonic Correction to Arg of Lat |
| 40 | I4 | 2^-31 | cus | rad | Sine Harmonic Correction to Arg of Lat |
| 44 | I4 | 2^-6 | crc | m | Cosine Harmonic Correction to Orbit Radius |
| 48 | I4 | 2^-6 | crs | m | Sine Harmonic Correction to Orbit Radius |
| 52 | I4 | 2^-31 | cic | rad | Cosine Harmonic Correction to Inclination |
| 56 | I4 | 2^-31 | cis | rad | Sine Harmonic Correction to Inclination |
| 60 | U4 | 2^3 | toe | s | Ephemeris Ref Time (BDT) |
| 64 | U2 |  | wne |  | Ref Time Week (BDT) |
| 66 | U2 |  | res2 |  | Reserved |
| 68 | U4 | 2^3 | toc | s | Clock Ref Time (BDT) |
| 72 | I4 | 2^-33 | af0 | s | Clock Bias |
| 76 | I4 | 2^-50 | af1 | s/s | Clock Drift |
| 80 | I2 | 2^-66 | af2 | s/s^2 | Clock Drift Rate |
| 82 | I2 | 0.1 | tgd | ns | TGD |
| 84 | U1 |  | iodc |  | Clock Age |
| 85 | U1 |  | iode |  | Eph Age |
| 86 | U1 |  | ura |  | URA |
| 87 | U1 |  | health |  | Health |
| 88 | U1 |  | svid |  | Satellite ID |
| 89 | U1 |  | valid |  | Validity (0-3) |
| 90 | U2 |  | res3 |  | Reserved |



3.14.4 MSG-BD3ION (0x08 0x03) 

| Message | MSG-BD3ION |
| --- | --- |
| **Description** | BD3 9-parameter Ionosphere Data |
| **Type** | Input |
| **Structure** | Header: `0xBA 0xCE`, Length: 16, ID: `0x08 0x03`, Payload: See below, Checksum: 4 Bytes |

**Payload Content:**

| Offset | Type | Scale | Name | Unit | Description |
| --- | --- | --- | --- | --- | --- |
| 0 | U4 |  | res1 |  | Reserved |
| 4 | U2 | 2^-3 | a1 |  | Iono Param |
| 6 | I1 | 2^-3 | a2 |  | Iono Param |
| 7 | U1 | 2^-3 | a3 |  | Iono Param |
| 8 | U1 | 2^-3 | a4 |  | Iono Param |
| 9 | U1 | 2^-3 | a5 |  | Iono Param |
| 10 | I1 | 2^-3 | a6 |  | Iono Param |
| 11 | I1 | 2^-3 | a7 |  | Iono Param |
| 12 | I1 | 2^-3 | a8 |  | Iono Param |
| 13 | I1 |  | a9 |  | Iono Param |
| 14 | U1 |  | res2 |  | Reserved |
| 15 | U2 |  | res3 |  | Reserved |



3.14.5 MSG-BD3EPH (0x08 0x04) 

| Message | MSG-BD3EPH |
| --- | --- |
| **Description** | BD3 Ephemeris |
| **Type** | Input |
| **Structure** | Header: `0xBA 0xCE`, Length: 92, ID: `0x08 0x04`, Payload: See below, Checksum: 4 Bytes |

**Payload Content:**

| Offset | Type | Scale | Name | Unit | Description |
| --- | --- | --- | --- | --- | --- |
| 0 | U4 |  | res1 |  | Reserved |
| 4 | I4 | 2^-9 | da | m | Semi-major axis deviation |
| 8 | I4 | 2^-21 | adot | m/s | Semi-major axis rate |
| 12 | I4 | 2^-57 | dndot | pi/s^2 | Mean motion rate diff |
| 16 | U4 | 2^-34 | e |  | Eccentricity (High 32) |
| 20 | I4 | 2^-32 | w | pi | Arg Perigee (High 32) |
| 24 | I4 | 2^-32 | M0 | pi | Mean Anomaly (High 32) |
| 28 | I4 | 2^-32 | i0 | pi | Inclination (High 32) |
| 32 | I4 | 2^-32 | Omega0 | pi | RAAN (High 32) |
| 36 | I4 | 2^-44 | Omega | pi/s | RA Rate |
| 40 | I2 | 2^-44 | deltaN | pi/s | Mean Motion Diff (High 16) |
| 42 | I2 | 2^-44 | IDOT | pi/s | Inc Rate |
| 44 | I2 | 2^-30 | cuc | rad | (High 16) |
| 46 | I2 | 2^-30 | cus | rad | (High 16) |
| 48 | I2 | 2^-8 | crc | m | (High 16) |
| 50 | I2 | 2^-8 | crs | m | (High 16) |
| 52 | I2 | 2^-30 | cic | rad |  |
| 54 | I2 | 2^-30 | cis | rad |  |
| 56 | U2 | 300 | toe | s | Time of Ephemeris |
| 58 | U2 |  | wne |  | Week of Ephemeris |
| 60 | U4 |  | kep_f |  | Overflow bits for params (i0, Omega0, w, e, M0, deltaN, cuc, cus, crc, crs) |
| 64 | U4 | 300 | toc | s | Time of Clock |
| 68 | I4 | 2^-34 | af0 | s | Clock Bias |
| 72 | I4 | 2^-50 | af1 | s/s | Clock Drift |
| 76 | I2 | 2^-66 | af2 | s/s^2 | Clock Drift Rate |
| 78 | I2 | 0.1 | tgd | ns | TGD |
| 80 | U2 |  | iodc |  | Clock Age |
| 84 | U1 |  | health |  | Health |
| 85 | U1 |  | satType |  | 1:GEO, 2:IGSO, 3:MEO |
| 86 | U2 |  | res2 |  | Reserved |
| 88 | U1 |  | svid |  | Sat ID |
| 89 | U1 |  | valid |  | Validity |
| 90 | U2 |  | res3 |  | Reserved |



3.14.6 MSG-GPSUTC (0x08 0x05) 

Same structure as MSG-BDSUTC, but for GPS. 

3.14.7 MSG-GPSION (0x08 0x06) 

Same structure as MSG-BDSION, but for GPS. 

3.14.8 MSG-GPSEPH (0x08 0x07) 

Same structure as MSG-BDSEPH but length is 72 bytes.

**Payload Content:**

* Standard GPS Ephemeris parameters (sqra, e, w, M0, i0, Omega0, OmegaDot, deltaN, IDOT, cuc, cus, crc, crs, cic, cis, toe, wne, toc, af0, af1, af2, tgd, iodc, ura, health, svid, valid).
* Differences: `tgd` is I1 (2^-31s). `iode` is at offset 70.




3.14.9 MSG-GLNEPH (0x08 0x08) 

| Message | MSG-GLNEPH |
| --- | --- |
| **Description** | GLONASS Ephemeris |
| **Type** | Input |
| **Structure** | Header: `0xBA 0xCE`, Length: 68, ID: `0x08 0x08` |

**Payload Content:**
Contains GLONASS specific parameters: `taon`, `x,y,z` (PZ-90), `dx,dy,dz`, `taoc`, `taoGPS`, `gammaN`, `tk`, `nt`, `ddx,ddy,ddz`, `dtaon`, `bn`, `tb`, `M`, `P`, `ft`, `en`, `p1`, `p2`, `p3`, `p4`, `ln`, `n4`, `svid`, `nl` (freq num), `valid`.


3.14.10 MSG-GALUTC (0x08 0x09) 

Same structure as MSG-BDSUTC, but for GALILEO. 

3.14.11 MSG-GALEPH (0x08 0x0B) 

Structure similar to MSG-BDSEPH, Length 76.
Includes `tgd_e5b` and `tgd_e5a`. Includes `msgFlag` to indicate source (E1I/E5A/E5B).


3.14.12 MSG-QZSUTC (0x08 0x0C) 

Same structure as MSG-GPSUTC. 

3.14.13 MSG-QZSION (0x08 0x0D) 

Same structure as MSG-GPSION. 

3.14.14 MSG-QZSEPH (0x08 0x0E) 

Same structure as MSG-GPSEPH. 

3.14.15 MSG-IRNEPH (0x08 0x11) 

Structure matching GPS Ephemeris, Length 88. Includes `msgFlag`.


3.14.16 MSG-IGP (0x08 0x17) 

| Message | MSG-IGP |
| --- | --- |
| **Description** | Ionosphere Grid Data |
| **Type** | Output |
| **Structure** | Header: `0xBA 0xCE`, Length: 16+2*igpNum, ID: `0x08 0x17` |

**Payload Content:**
Contains Grid header (`msTow`, `wni`, `valid`, `iodi`, `svid`, `lat0`, `lon0`, `igpQ`, `igpNum`, `IgpNumTot`) and `igp[][]` array data.


3.15 MON (0x0A) 

3.15.1 MON-CWI (0x0A 0x00) 

Output interference signal info.
Payload: `cwi_en`, `cwi_num`, `dif_mask`, and repeated blocks of (`cwi_freq`, `cwi_trked`, `dif_port`, `notch_ch`, `jn0`).


3.15.2 MON-RFE (0x0A 0x01) 

RF Gain Query.
Payload: `antFlag`, `agcMode`, `rfaGainL1/L5`, `lnaGainL1/L5`, and repeated blocks for 4 channels (`fltGain`, `pgaGain`).


3.15.3 MON-HIST (0x0A 0x02) 

IF Data Histogram Statistics.
Payload: `if_freq`, `chn`, `i_q` (0=I, 1=Q), and 512 `data` points (UInt2).


3.15.4 MON-VER (0x0A 0x04) 

Version Info.
Payload: `swVersion` (32 chars), `hwVersion` (32 chars).


3.15.5 MON-CPU (0x0A 0x05) 

Baseband Processor Info.
Payload: `SolDelay`, `TrkLoad`, `Txbuffer0/1`.


3.15.6 MON-ICV (0x0A 0x06) 

Chip Version Info.
Payload: `icVersion` (64 chars).


3.15.7 MON-MOD (0x0A 0x07) 

Module Version Info.
Payload: `modVersion` (64 chars).


3.15.9 MON-HW (0x0A 0x09) 

Hardware Status.
Payload: `noisePerMs0/1/2`, `agcData0/1/2`, `antStatus` (0=Open, 2=OK, 3=Short), `cwiNum`, `cwiFreq[8]`.


3.15.10 MON-JSM (0x0A 0x0A) 

Anti-Jamming/Spoofing Detailed Status.
Payload: `secFlagx` (Spoofing switch/mode, Time state), `spfFlagx` (Spoofing indicator 0-3), `jamDetEn` (Jamming switch), `jamLevel` (0-3), `spfTime`, `RfeChNum`, and repeated blocks per channel (`agcGainNorm`, `agcGain`, `jam2nf`, `jamLevelChn`).


3.15.11 MON-SEC (0x0A 0x0B) 

Simplified Anti-Jamming/Spoofing Info.
Payload: `secFlagx`, `spfFlagx`, `jamDetEn`, `jamLevel`.


3.16 AID (0x0B) 

3.16.1 AID-INI (0x0B 0x01) 

| Message | AID-INI |
| --- | --- |
| **Description** | Auxiliary Position, Time, Frequency, Clock Bias |
| **Type** | Query/Input |
| **Structure** | Header: `0xBA 0xCE`, Length: 56, ID: `0x0B 0x01` |

**Payload Content:**

| Offset | Type | Scale | Name | Unit | Description |
| --- | --- | --- | --- | --- | --- |
| 0 | R8 |  | ecefXOrLat | m/deg | ECEF X or Latitude |
| 8 | R8 |  | ecefYOrLon | m/deg | ECEF Y or Longitude |
| 16 | R8 |  | ecefZOrAlt | m | ECEF Z or Altitude |
| 24 | R8 |  | tow | s | GPS TOW |
| 32 | R4 | 300 | freqBias | ppm | Clock Freq Drift (e.g. 300=1ppm) |
| 36 | R4 |  | pAcc | m^2 | 3D Position Error Variance |
| 40 | R4 | C^2 | tAcc | s^2 | Time Error Variance |
| 44 | R4 | 300^2 | fAcc | ppm^2 | Freq Drift Error Variance |
| 48 | U4 |  | res |  | Reserved |
| 52 | U2 |  | wn |  | GPS Week |
| 54 | U1 |  | timeSource |  | Time Source |
| 55 | U1 |  | flags |  | Flags (B0=Pos Valid, B1=Time Valid, B2=Freq Drift Valid, B4=Freq Valid, B5=LLA Format, B6=Alt Invalid) |



3.17 INS2 (0x14) 

3.17.1 INS2-ATT (0x14 0x00) 

| Message | INS2-ATT |
| --- | --- |
| **Description** | IMU Attitude relative to NED |
| **Type** | Periodic/Query |
| **Structure** | Header: `0xBA 0xCE`, Length: 32, ID: `0x14 0x00`, Payload: See below, Checksum: 4 Bytes |

**Payload Content:**

| Offset | Type | Scale | Name | Unit | Description |
| --- | --- | --- | --- | --- | --- |
| 0 | U4 |  | rawTow | ms | Raw receiver time (Integer ms) |
| 4 | U2 |  | wn | week | Raw receiver time GPS Week |
| 6 | U1 |  | flag |  | Attitude Valid Flag (1=Valid) |
| 7 | U1 |  | res |  | Reserved |
| 8 | I4 | 1e-5 | roll | deg | Roll angle |
| 12 | I4 | 1e-5 | pitch | deg | Pitch angle |
| 16 | I4 | 1e-5 | heading | deg | Heading angle |
| 20 | U4 | 1e-5 | rollAcc | deg | Roll accuracy |
| 24 | U4 | 1e-5 | pitchAcc | deg | Pitch accuracy |
| 28 | U4 | 1e-5 | headingAcc | deg | Heading accuracy |



3.17.2 INS2-IMU (0x14 0x01) 

| Message | INS2-IMU |
| --- | --- |
| **Description** | Acceleration and angular velocity in Vehicle Frame [1] |
| **Type** | Periodic |
| **Structure** | Header: `0xBA 0xCE`, Length: 8+24*N, ID: `0x14 0x01`, Payload: See below, Checksum: 4 Bytes |

**Payload Content:**

| Offset | Type | Scale | Name | Unit | Description |
| --- | --- | --- | --- | --- | --- |
| 0 | U4 |  | tow | ms | GPS Time of Week |
| 4 | U1 |  | imuFlag |  | IMU Data Flag |
| 5 | U1 |  | num |  | Number of samples |
| 6 | I2 | 0.01 | temp | degC | Temperature |
| **Repeat Block (K=0 to num-1)** |  |  |  |  |  |
| 8+24*K | I4 | 0.001 | accX | m/s/s | X-axis Acceleration |
| 12+24*K | I4 | 0.001 | accY | m/s/s | Y-axis Acceleration |
| 16+24*K | I4 | 0.001 | accZ | m/s/s | Z-axis Acceleration |
| 20+24*K | I4 | 0.001 | gyroX | deg/s | X-axis Angular Velocity |
| 24+24*K | I4 | 0.001 | gyroY | deg/s | Y-axis Angular Velocity |
| 28+24*K | I4 | 0.001 | gyroZ | deg/s | Z-axis Angular Velocity |
| **End Repeat** |  |  |  |  |  |

**Remark [1]: Vehicle Coordinate System**
Origin is center of rear axle. Z axis is opposite to gravity (Up). XY axes are horizontal. X axis points to right door. Y axis points to front of vehicle.