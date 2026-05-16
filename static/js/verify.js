const video = document.getElementById("video");
const canvas = document.getElementById("canvas");
const startCameraButton = document.getElementById("startCameraButton");
const stopCameraButton = document.getElementById("stopCameraButton");
const startVerifyButton = document.getElementById("startVerifyButton");
const stopVerifyButton = document.getElementById("stopVerifyButton");
const singleVerifyButton = document.getElementById("singleVerifyButton");
const statusBox = document.getElementById("statusBox");
const actionValue = document.getElementById("actionValue");
const personValue = document.getElementById("personValue");
const distanceValue = document.getElementById("distanceValue");
const messageValue = document.getElementById("messageValue");
const timeValue = document.getElementById("timeValue");

const verifyIntervalMs = 5000;

let stream = null;
let verifyTimer = null;
let isVerifying = false;

startCameraButton.addEventListener("click", startCamera);
stopCameraButton.addEventListener("click", stopCamera);
startVerifyButton.addEventListener("click", startAutoVerify);
stopVerifyButton.addEventListener("click", stopAutoVerify);
singleVerifyButton.addEventListener("click", verifyOnce);

function updateStatus(text, type = "") {
  statusBox.textContent = text;
  statusBox.className = `status ${type}`.trim();
}

function updateResult(data) {
  const action = data.action || "DENY";
  const isOpen = action === "OPEN";

  updateStatus(isOpen ? `OPEN - ${data.person || "UNKNOWN"}` : action, isOpen ? "open" : "deny");
  actionValue.textContent = action;
  personValue.textContent = data.person || "-";
  distanceValue.textContent = data.distance === null || data.distance === undefined ? "-" : data.distance;
  messageValue.textContent = data.message || "-";
  timeValue.textContent = new Date().toLocaleTimeString();
}

function setCameraState(isRunning) {
  startCameraButton.disabled = isRunning;
  stopCameraButton.disabled = !isRunning;
}

async function startCamera() {
  try {
    if (stream) {
      stream.getTracks().forEach((track) => track.stop());
    }

    stream = await navigator.mediaDevices.getUserMedia({
      video: {
        width: { ideal: 1280 },
        height: { ideal: 720 },
        facingMode: "user"
      },
      audio: false
    });

    video.srcObject = stream;
    await video.play();
    setCameraState(true);
    updateStatus("CAMERA_READY");
  } catch (error) {
    updateStatus(`CAMERA_ERROR: ${error.message}`, "deny");
  }
}

function stopCamera() {
  stopAutoVerify();

  if (stream) {
    stream.getTracks().forEach((track) => track.stop());
    stream = null;
  }

  video.pause();
  video.removeAttribute("src");
  video.srcObject = null;
  setCameraState(false);
  updateStatus("CAMERA_STOPPED");
}

async function captureBlob() {
  if (!stream) {
    updateStatus("START_CAMERA_FIRST", "deny");
    return null;
  }

  if (!video.videoWidth || !video.videoHeight) {
    updateStatus("CAMERA_NOT_READY", "deny");
    return null;
  }

  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;

  const ctx = canvas.getContext("2d");
  ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

  return new Promise((resolve) => {
    canvas.toBlob((blob) => resolve(blob), "image/jpeg", 0.95);
  });
}

async function verifyOnce() {
  if (isVerifying) {
    return;
  }

  try {
    isVerifying = true;
    singleVerifyButton.disabled = true;
    updateStatus("PROCESSING...");

    const blob = await captureBlob();

    if (!blob) {
      return;
    }

    const formData = new FormData();
    formData.append("file", blob, "frame.jpg");

    const response = await fetch("/verify-face", {
      method: "POST",
      body: formData
    });

    const data = await response.json();
    updateResult(data);
  } catch (error) {
    updateStatus(`ERROR: ${error.message}`, "deny");
    actionValue.textContent = "DENY";
    messageValue.textContent = "ERROR";
    timeValue.textContent = new Date().toLocaleTimeString();
  } finally {
    isVerifying = false;
    singleVerifyButton.disabled = false;
  }
}

async function startAutoVerify() {
  if (!stream) {
    await startCamera();
  }

  if (!stream || verifyTimer) {
    return;
  }

  startVerifyButton.disabled = true;
  stopVerifyButton.disabled = false;
  updateStatus("AUTO_VERIFY_RUNNING");

  await verifyOnce();
  verifyTimer = window.setInterval(verifyOnce, verifyIntervalMs);
}

function stopAutoVerify() {
  if (verifyTimer) {
    window.clearInterval(verifyTimer);
    verifyTimer = null;
  }

  startVerifyButton.disabled = false;
  stopVerifyButton.disabled = true;
  updateStatus("AUTO_VERIFY_STOPPED");
}
