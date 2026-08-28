# Hardware Schematic: Smart Strap Bridge

This document details the wiring and logic level requirements for bridging a MAX30102 optical PPG sensor to the Movesense snap connectors using an ATtiny85 microcontroller.

## Components
1. **Movesense Sensor:** Acts as the 1-Wire Master. Powered by an internal CR2025 battery (3.0V). Exposes 1-Wire on its snap connectors.
2. **ATtiny85 Microcontroller (or similar ultra-low power MCU):** Acts as the I2C Master (talking to the PPG) and the 1-Wire Slave (talking to Movesense). 
3. **MAX30102 Pulse Oximeter/Heart Rate Sensor:** High-sensitivity PPG sensor. Requires 1.8V for the internal logic and ~3.3V (or up to 5V) for the LED drivers.

## Wiring Diagram

### ATtiny85 Pinout Reference (8-pin DIP/SOIC)
- Pin 1: PB5 (Reset)
- Pin 2: PB3 (ADC3)
- Pin 3: PB4 (ADC2)
- Pin 4: GND
- Pin 5: PB0 (MOSI / SDA / 1-Wire Data)
- Pin 6: PB1 (MISO)
- Pin 7: PB2 (SCK / SCL)
- Pin 8: VCC

### Connections: ATtiny85 <--> MAX30102 (I2C)
The ATtiny85 must communicate with the MAX30102 using I2C.
- **ATtiny PB0 (SDA)** <---> **MAX30102 SDA**
- **ATtiny PB2 (SCL)** <---> **MAX30102 SCL**
- **ATtiny VCC** <---> **MAX30102 VIN (1.8V / 3.3V logic level shifted breakout)**
- **ATtiny GND** <---> **MAX30102 GND**
*Note: Ensure I2C pull-up resistors (typically 4.7kΩ) are present on the SDA/SCL lines. Most MAX30102 breakout boards include these.*

### Connections: ATtiny85 <--> Movesense (1-Wire)
The Movesense utilizes a 1-Wire protocol over its snap connectors.
- **Movesense Snap 1 (1-Wire Data/Power)** <---> **ATtiny PB1 (1-Wire Slave Pin)**
- **Movesense Snap 2 (GND)** <---> **ATtiny GND**
*Note: The 1-Wire pin on the ATtiny85 can be configured in software. Here we use PB1. A 4.7kΩ pull-up resistor is typically required on the 1-Wire data line to VCC, but the Movesense may provide internal pull-ups.*

## Power and Logic Levels

> [!CAUTION]
> **Voltage Mismatch Risk:** 
> - Movesense runs on a 3.0V coin cell.
> - MAX30102 breakout boards often expect 3.3V or 5V and have onboard regulators stepping down to 1.8V for the sensor core.
> - ATtiny85 can run anywhere from 1.8V to 5.5V.

**Power Strategy:**
To keep the strap completely self-contained and avoid draining the Movesense's small CR2025 battery (1-Wire parasitic power is insufficient for the high-draw LEDs of the MAX30102), the Smart Strap MUST have its own tiny rechargeable LiPo battery (e.g., a 3.7V, 100mAh cell).

1.  **Strap Battery (3.7V LiPo):** Powers the ATtiny85 directly (VCC = 3.7V).
2.  **MAX30102 Power:** The 3.7V powers the MAX30102 breakout board (VIN = 3.7V). The breakout board's internal regulators will drop this to the required 1.8V for the IC and use the 3.7V directly for the LED drivers.
3.  **1-Wire Logic Level:** The ATtiny85 running at 3.7V will output a 3.7V logic HIGH on the 1-Wire line. The Movesense is a 3.0V device. You **must** use a simple logic level shifter or a voltage divider (resistors) on the 1-Wire data line to step the ATtiny's 3.7V TX down to 3.0V to avoid frying the Movesense 1-Wire pin.

## Firmware Flow (ATtiny85)
1. **Initialize:** Set up I2C master and 1-Wire slave libraries.
2. **Loop (High Speed):** 
   - Continuously poll the MAX30102 over I2C at high speed (e.g., 400Hz).
   - Buffer the latest Red and IR raw PPG values in memory.
3. **Interrupt (1-Wire Request):**
   - When the Movesense (Master) sends a 1-Wire read request, an interrupt fires on the ATtiny.
   - The ATtiny immediately transmits the latest buffered PPG values over the 1-Wire bus to the Movesense.
