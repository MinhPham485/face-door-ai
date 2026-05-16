# Face Door AI - Local Setup & API Guide

## 1. Setup

Clone repo:

```bash
git clone https://github.com/MinhPham485/face-door-ai.git
cd face-door-ai
```

Tạo virtual environment:

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

Cài dependencies:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Test DeepFace:

```bash
python -c "from deepface import DeepFace; print('DeepFace OK')"
```

---

## 2. Run server

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Project docs:

```txt
http://localhost:8000/docs
```

Camera verify page:

```txt
http://localhost:8000/verify
```

Swagger UI:

```txt
http://localhost:8000/api-docs
```

Health check:

```bash
curl http://localhost:8000/health
```

Expected response:

```json
{
  "status": "ok"
}
```

IoT connection check:

```bash
curl http://localhost:8000/iot/ping
```

Expected response:

```json
{
  "success": true,
  "message": "AI_SERVER_READY"
}
```

---

## 3. Add owner image

Endpoint:

```http
POST /owners/{owner_name}/images
```

Example:

```bash
curl -X POST "http://localhost:8000/owners/minh/images" \
  -F "file=@test_images/minh_1.jpg"
```

Add 3-5 images per owner.

Check owners:

```bash
curl http://localhost:8000/owners
```

Example response:

```json
{
  "success": true,
  "owners": [
    {
      "name": "minh",
      "image_count": 3
    }
  ]
}
```

---

## 4. Rebuild embeddings

Run this after adding owner images:

```bash
curl -X POST "http://localhost:8000/embeddings/rebuild"
```

Example response:

```json
{
  "success": true,
  "message": "EMBEDDINGS_REBUILT",
  "result": {
    "minh": {
      "image_count": 3,
      "embedding_count": 3
    }
  }
}
```

---

## 5. Verify face

Open the browser verify page:

```txt
http://localhost:8000/verify
```

This page uses your browser camera and sends frames to the same API below.

Endpoint:

```http
POST /verify-face
```

Request type:

```txt
multipart/form-data
```

Field:

```txt
file: jpg/jpeg/png image
```

Example:

```bash
curl -X POST "http://localhost:8000/verify-face" \
  -F "file=@test_images/anhtest1.jpg"
```

Authorized response:

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

Denied response:

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

No face response:

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

## 6. How IoT should use the response

IoT only needs to check `action`.

Button flow:

```txt
button pressed -> capture image -> POST /verify-face -> read action -> open/deny
```

```txt
if action == "OPEN":
    unlock door
else:
    keep locked
```

Example pseudo code:

```cpp
if (action == "OPEN") {
    openDoor();
} else {
    denyAccess();
}
```

---

## 7. Use with ESP32 / IoT device

Run server on the machine that hosts the AI service:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Get local IP of that machine.

### macOS

```bash
ipconfig getifaddr en0
```

Example IP:

```txt
192.168.1.25
```

IoT device should call:

```txt
http://192.168.1.25:8000/verify-face
```

Do not use:

```txt
http://localhost:8000/verify-face
```

because `localhost` on ESP32 means the ESP32 itself.

---

## 8. Webcam local test

Run server first:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Open another terminal:

```bash
source .venv/bin/activate
python webcam_client.py
```

The webcam client sends frames to:

```txt
http://localhost:8000/verify-face
```

---

## 9. Useful curl commands

Add owner image:

```bash
curl -X POST "http://localhost:8000/owners/minh/images" \
  -F "file=@test_images/minh_1.jpg"
```

List owners:

```bash
curl http://localhost:8000/owners
```

Rebuild embeddings:

```bash
curl -X POST "http://localhost:8000/embeddings/rebuild"
```

Verify face:

```bash
curl -X POST "http://localhost:8000/verify-face" \
  -F "file=@test_images/anhtest1.jpg"
```

Pretty JSON output with `jq`:

```bash
curl -X POST "http://localhost:8000/verify-face" \
  -F "file=@test_images/anhtest1.jpg" | jq
```

Install `jq` on macOS:

```bash
brew install jq
```

---

## 10. Troubleshooting

### Port 8000 already in use

```bash
lsof -i :8000
kill -9 <PID>
```

Or run on another port:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8001
```

### Curl cannot read image file

Error:

```txt
curl: (26) Failed to open/read local data from file/application
```

Use the correct file path:

```bash
curl -X POST "http://localhost:8000/verify-face" \
  -F "file=@test_images/anhtest1.jpg"
```

Or absolute path:

```bash
curl -X POST "http://localhost:8000/verify-face" \
  -F "file=@/Users/yourname/Downloads/anhtest1.jpg"
```

### No face detected

Use a clearer image:

```txt
- face visible
- enough light
- not too blurry
- not too far from camera
- jpg/png format
```

### First run is slow

DeepFace may download model weights on first run. Later runs will be faster.

---

## 11. Privacy note

Do not commit real face images or embeddings.

These folders should stay ignored:

```txt
known_faces/
uploads/
test_images/
embeddings/
```
