# Hardware Integration of PPG and ECG for Wearable Devices

## 1. Feasibility of Modifying the Movesense Sensor
Movesense devices (such as the Movesense HR+ and MD) are highly integrated units optimized specifically for single-channel ECG and 9-axis IMU tracking.

*   **Hardware Architecture limitations:** Movesense devices do not possess built-in optical components (LEDs and photodiodes) required for Photoplethysmography (PPG). 
*   **Expansion & Pinouts:** The external interface of the Movesense is a proprietary snap connector. This connector only exposes the ECG electrode contacts and power/data interfaces primarily intended for the **Programming and Debugging Jig**. The jig provides a UART/SWD connection and power (+5V) via pogo pins to the sensor's underside.
*   **I/O Accessibility:** The internal microcontroller (an nRF52 series chip) uses a 1.8V logic level. However, generic I/O buses like I2C or SPI (which would be required to interface with an external PPG module) are not routed to the external snap connectors. 
*   **Conclusion on Movesense:** Adding a PPG sensor to an off-the-shelf Movesense would require destructive hardware hacking (delidding the potting compound, micro-soldering to internal MCU traces) and writing custom lower-level drivers outside the provided Movesense Device API. It is fundamentally impractical.

## 2. Alternative Single-Chip Solution: Maxim MAX86150
For projects requiring simultaneous ECG and PPG (such as continuous non-invasive blood pressure estimation), building custom hardware around a dedicated dual-modality biosensor is the standard approach. The **Maxim Integrated MAX86150** is highly recommended for this architecture.

*   **Integrated Design:** The MAX86150 combines an ECG analog front-end (AFE) and a PPG sensor (pulse oximeter/heart rate) in a miniature 3.3mm x 5.6mm x 1.3mm package.
*   **Synchronized Sampling:** Crucially, it allows for simultaneous and synchronized sampling of both ECG (18-bit ADC) and PPG (19-bit ADC). This synchronization is vital for calculating **Pulse Transit Time (PTT)**, the foundation for cuffless blood pressure measurement.
*   **Wearable-Friendly:** The ECG portion is optimized for **dry electrodes**, mirroring the comfort of a standard Movesense chest strap (no conductive gel needed).
*   **Interfacing:** The module communicates via a standard I2C interface and operates on 1.8V logic, making it electrically compatible with modern low-power microcontrollers like the Nordic nRF52 family.

## 3. Recommended Development Pathway
Rather than attempting to hack a Movesense, the optimal path is to design a custom PCB utilizing an nRF52-series Bluetooth SoC (the same family used inside Movesense) paired with the MAX86150. 
*   **Prototyping:** Development can be fast-tracked using the official **MAX86150 Evaluation System** (which includes a sensor board with dry electrodes and an ARM-based microcontroller board). Alternatively, breakout boards from vendors like ProtoCentral or MikroE can be wired directly to an nRF52 development kit to replicate a Movesense-like BLE streaming architecture.
