# ClipboarderX
Clipborad shareing

A lightweight, peer-to-peer text clipboard sharing utility for two Windows 11 PCs, using an ESP32 as a lightweight TCP/IP relay server.

## Overview

- **Bidirectional Text Sync:** Automatically detects text copied on one PC and syncs it to the other.
- **Zero-Config Portability:** Runs natively on Windows 11 (.NET Framework 4.8) with no external runtime dependencies.
- **No Master/Slave:** Both PCs run the exact same client binary and connect to the ESP32 relay.
- **Auto-Reconnect:** Both the Windows client and the ESP32 relay automatically recover from sleep, reboots, or network drops.

---

## Components

### 1. Relay Server (`ClipboarderX.ino`)
- **Target Hardware:** DOIT ESP32 DEVKIT V1
- **Core Version:** ESP32 Arduino Core `2.0.x` (e.g., `2.0.17`)
- **Default Port:** `50000` (TCP)

#### Setup & Serial Commands
1. Flash `ClipboarderX.ino` via Arduino IDE.
2. Open Serial Monitor at **`115200` baud** (Line ending: `NL` or `Both NL & CR`).
3. On first boot, enter your Wi-Fi **SSID** and **Password** when prompted. Credentials are saved to non-volatile memory (NVS).
4. Available commands in Serial Monitor:
   - `status` — Show current Wi-Fi IP address, port, and client connection status.
   - `setup` / `reset` — Clear saved credentials and re-enter Wi-Fi setup mode.

#### Onboard LED Status (GPIO 2)
- **Fast Blink (0.5s):** Connecting to Wi-Fi
- **Off:** Connected to Wi-Fi, 0 PCs connected
- **Slow Blink (1.0s):** 1 PC connected (waiting for the 2nd PC)
- **Solid On:** Both PCs connected (relay active)

---

### 2. Windows Client (`ClipboarderX.sln`)
- **IDE / Target:** Visual Studio 2019 / `.NET Framework 4.8` (Windows Forms)
- **Usage:** Pass the ESP32's IPv4 address and port number as command-line arguments:

```cmd
ClipboarderX.exe <ESP32_IP_ADDRESS> <PORT>
```