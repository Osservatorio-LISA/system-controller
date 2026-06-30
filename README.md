# System Controller - LISA Astronomical Observatory

This repository contains the software for the **System Controller** (Central Controller) of the LISA Astronomical Observatory located at Liceo Scientifico "G.D. Cassini" in Genoa. It acts as the core coordinator of the entire infrastructure, managing and supervising the various hardware modules to enable remote operation and automation.

---

## Overview

The System Controller is deployed on a **Raspberry Pi 3B+** single-board computer running Python. It serves as a central orchestrator, bridging user interfaces (both local and remote) with the peripheral microcontrollers (ESP32-based nodes) responsible for the physical sub-systems:
- **Dome Module (cupola astronomica)**: Handles rotation tracking and absolute positioning.
- **Slit Module (feritoia)**: Controls the opening and closing of the observing window.
- **Telescope Module**: Acts as a proxy converting system commands to native serial commands for the Meade LX200 telescope.
<img width="1672" height="941" alt="Schema logico Architettura" src="https://github.com/user-attachments/assets/0132dd8b-fec0-49c5-a392-bdf87ba0a57d" />

---

## Key Features

- **Star Network Topology**: It communicates via a wireless star topology, meaning each peripheral module operates independently. This keeps the firmware decoupled and allows us to add or modify modules without affecting the rest of the application.
- **Digital Twin (Local State Model)**: It maintains a centralized, thread-safe memory model (`global_state.py`) reflecting the real-time telemetry of the entire observatory (e.g., dome positions in degrees/ticks, slit state). This eliminates the need to constantly poll the physical hardware sensors.
- **Concurrent & Asynchronous Execution**: Built using a multi-threaded architecture with daemon threads and thread-safe queues (`queue.Queue`). This ensures optimal responsiveness to user inputs without causing computational or network bottlenecks.
- **Active Diagnostics & Heartbeat**: It tracks periodic TCP heartbeat packets from each peripheral. If a module fails to report within `MAX_HEARTBEAT_TIME`, it triggers automated HTTP diagnostics and initiates an emergency shutdown (`close_system`) if a critical failure is detected, preventing mechanical damage.
- **Dual-Control Interface**: It seamlessly handles and synchronizes incoming instructions from both a local terminal interface and a remote web dashboard.

---

## Repository Structure & Core Modules

### 1. Front-End / External Interfaces
- **`ext_interface.py`**: Handles low-level I/O. It implements a non-blocking message-routing architecture using thread-safe queues to isolate input capturing from core execution.
- **`cmd_handler.py`**: Runs as a background daemon thread. It processes incoming command strings through a parser (`cmd_parser`) and executes mapped routines like:
  - `STATUS` / `GET`: Queries the local digital twin and returns JSON telemetry.
  - `GOTO`: Calculates geometric offsets between the dome and telescope, then coordinates synchronized positioning via HTTP PUT requests.
  - `MOVE`: Passes complex parameters down to specific hardware drivers.
  - `EXIT`: Triggers a controlled system shutdown, gracefully closing Flask services and network sockets.

### 2. Back-End / Internal Communications
- **`http_interface.py`**: Manages synchronous, blocking REST API requests (`GET`, `PUT`) to individual ESP32 modules. It handles query formatting, JSON payload parsing, and connection timeout exceptions.
- **`TcpServer.py` & `baseTcpHandler.py`**: Manage continuous, event-driven, full-duplex TCP socket communication. It receives raw strings bounded by a special character (`$`), deserializes the JSON payloads, and updates the global state.
- **`./modules_handlers/`**: Houses specialized logic handlers for decoding asynchronous data streams from individual modules.

### 3. Web Dashboard Graphical User Interface
We developed an interactive web-based dashboard using a client-server paradigm:
- **`web_gui_interface.py`**: A Flask-based backend acting as a pseudo-REST API layer that pipes commands to the core system.
- **`index.html` & `stile.css`**: Provide a fully responsive graphical layout including a control panel, terminal feed, and status displays.
- **`api.js`**: Manages asynchronous AJAX interactions to avoid page refreshes.
- **`canvas.js`**: Renders real-time orientation and rotation graphics of both the dome and the telescope using HTML5 Canvas APIs.
- **`terminal.js` & `Keys.js`**: Embed an interactive virtual terminal command line directly inside the browser window.

---

## System Images & Diagrams

The system design relies on several visual architectures documented during the implementation:

### 1. Observatory Layout & Planimetry
The star network layout positions the **System Controller (D)** as the central hub connecting the Dome Controller (A), Slit Controller (B), and Telescope Node (C).

<img width="500" height="500" alt="Schema cupola_" src="https://github.com/user-attachments/assets/82ae09bd-c898-44b6-ad61-95b7b5ded3c9" />


### 2. Logical Communication Flows
The communication architecture combines RESTful HTTP for synchronous actions and raw TCP sockets for real-time telemetry streaming and heartbeats.

### 3. Web GUI Components
The front-end control panel features a real-time tracking radar canvas alongside
<img width="581" height="670" alt="web_API_graphic" src="https://github.com/user-attachments/assets/1c4ce227-8903-43d4-a3ef-9a35927a0d79" />
and a virtual command terminal.
<img width="457" height="209" alt="web_API_terminal" src="https://github.com/user-attachments/assets/8d2c8bc4-ad33-4359-8dca-2f4138b0f6c4" />


---

## Setup & Running

1. **Prerequisites**: Ensure Python 3.x and `pip` are installed on your Raspberry Pi.
2. **Install Dependencies**:
 ```bash
 pip install flask
 ```
3. **Execution**: Run the main controller application:
 ```Bash
python main.py
 ```

