# Face Door AI

An AI-powered smart door access control system that combines **ESP32-CAM**, **FastAPI**, and **DeepFace** to perform real-time facial recognition and automatically control door access.

The system captures images using an ESP32-CAM, sends them to a backend server for face verification, and returns an authorization result. Authorized users can unlock the door automatically, while unauthorized users are denied access.

## Features

* Real-time facial recognition using DeepFace
* ESP32-CAM image capture and Wi-Fi communication
* Automatic door unlocking with servo motor
* Motion-triggered activation using PIR sensor
* REST API built with FastAPI
* Face embedding storage for fast verification
* Low-power operation with ESP32 Deep Sleep
* Browser-based camera verification page
* Owner management and embedding rebuild APIs

---

## System Architecture

```text
PIR Sensor
     │
     ▼
ESP32-CAM
     │ HTTP POST
     ▼
FastAPI Server
     │
     ▼
DeepFace Verification
     │
 ┌───┴────┐
 │        │
 ▼        ▼
OPEN     DENY
 │          │
 ▼          ▼
Servo      Locked
```

---

## Technology Stack

### Embedded

* ESP32-CAM (AI Thinker)
* Arduino Framework
* Wi-Fi
* HTTP Client
* ESP32Servo

### Backend

* Python 3.11+
* FastAPI
* DeepFace
* TensorFlow
* Uvicorn

---

# Local Setup

## Clone Repository

```bash
git clone https://github.com/MinhPham485/face-door-ai.git
cd face-door-ai
```

## Create Virtual Environment

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Windows PowerShell

```powershell
py -3 -m venv .venv
.venv\Scripts\Activate.ps1
```

## Install Dependencies

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Verify DeepFace Installation

```bash
python -c "from deepface import DeepFace; print('DeepFace OK')"
```

---

# Run Server

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Available endpoints:

| Service            | URL                            |
| ------------------ | ------------------------------ |
| API Docs           | http://localhost:8000/api-docs |
| Camera Verify Page | http://localhost:8000/verify   |
| Health Check       | http://localhost:8000/health   |
| IoT Ping           | http://localhost:8000/iot/ping |

---

# API Usage

## Add Owner Images

```http
POST /owners/{owner_name}/images
```

Example:

```bash
curl -X POST "http://localhost:8000/owners/minh/images" \
-F "file=@test_images/minh_1.jpg"
```

Recommended:

* Add 3–5 images per owner
* Use different lighting conditions and angles

---

## Rebuild Embeddings

After adding owner images:

```bash
curl -X POST "http://localhost:8000/embeddings/rebuild"
```

This generates facial embeddings used during verification.

---

## Verify Face

```http
POST /verify-face
```

Request:

```text
multipart/form-data
```

Field:

```text
file
```

Example:

```bash
curl -X POST "http://localhost:8000/verify-face" \
-F "file=@test_images/sample.jpg"
```

### Authorized Response

```json
{
  "success": true,
  "authorized": true,
  "person": "minh",
  "distance": 0.0541,
  "message": "OPEN",
  "action": "OPEN"
}
```

### Unauthorized Response

```json
{
  "success": true,
  "authorized": false,
  "person": null,
  "distance": 0.47464,
  "message": "DENY",
  "action": "DENY"
}
```

### No Face Detected

```json
{
  "success": true,
  "authorized": false,
  "person": null,
  "distance": null,
  "message": "NO_FACE_DETECTED",
  "action": "DENY"
}
```

---

# ESP32 Integration

Verification flow:

```text
Motion Detected
      ↓
Capture Image
      ↓
POST /verify-face
      ↓
Read action
      ↓
OPEN or DENY
```

Example:

```cpp
if (action == "OPEN")
{
    openDoor();
}
else
{
    denyAccess();
}
```

Use the server's local IP address:

```text
http://192.168.x.x:8000/verify-face
```

Do not use:

```text
http://localhost:8000
```

because localhost on ESP32 refers to the ESP32 itself.

---

# Testing

Health check:

```bash
curl http://localhost:8000/health
```

IoT connectivity:

```bash
curl http://localhost:8000/iot/ping
```

Webcam test:

```bash
python webcam_client.py
```

---

# Troubleshooting

### Port Already In Use

```bash
lsof -i :8000
kill -9 <PID>
```

or

```bash
uvicorn app.main:app --port 8001
```

### No Face Detected

Use images with:

* Good lighting
* Clear frontal face
* Minimal blur
* JPG or PNG format

### Slow First Run

DeepFace may download model weights during the first execution.

Subsequent runs will be significantly faster.

---

# Privacy

Do not commit personal face data or generated embeddings.

Ignored directories:

```text
known_faces/
uploads/
embeddings/
test_images/
```

---

# Author

Bui Le Hoang

Pham Hoang Minh

Computer Engineering Students
Hanoi University of Science and Technology (HUST)
