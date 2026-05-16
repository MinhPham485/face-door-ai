const ownerInput = document.getElementById("ownerName");
const video = document.getElementById("video");
const canvas = document.getElementById("canvas");
const resultBox = document.getElementById("result");
const startButton = document.getElementById("startButton");
const stopCameraButton = document.getElementById("stopCameraButton");
const captureButton = document.getElementById("captureButton");
const autoButton = document.getElementById("autoButton");

const ownerNamePattern = /^[A-Za-z0-9_-]{1,50}$/;

let stream = null;
let isUploading = false;

startButton.addEventListener("click", startCamera);
stopCameraButton.addEventListener("click", stopCamera);
captureButton.addEventListener("click", captureAndUpload);
autoButton.addEventListener("click", autoCapture);

function setStatus(message, type = "") {
  resultBox.textContent = message;
  resultBox.className = `status ${type}`.trim();
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function getOwnerName() {
  const ownerName = ownerInput.value.trim();

  if (!ownerName) {
    setStatus("Please enter owner name.", "error");
    return null;
  }

  if (!ownerNamePattern.test(ownerName)) {
    setStatus("Owner name chi duoc dung chu, so, dau _ hoac -.", "error");
    return null;
  }

  return ownerName;
}

function setButtonsDisabled(disabled) {
  captureButton.disabled = disabled;
  autoButton.disabled = disabled;
  ownerInput.disabled = disabled;
}

function setCameraState(isRunning) {
  startButton.disabled = isRunning;
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
    setStatus("Camera started.", "ok");
  } catch (error) {
    setStatus(`Cannot start camera: ${error.message}`, "error");
  }
}

function stopCamera() {
  if (stream) {
    stream.getTracks().forEach((track) => track.stop());
    stream = null;
  }

  video.pause();
  video.removeAttribute("src");
  video.srcObject = null;
  setCameraState(false);
  setStatus("Camera stopped.");
}

async function captureBlob() {
  if (!stream) {
    setStatus("Please start camera first.", "error");
    return null;
  }

  if (!video.videoWidth || !video.videoHeight) {
    setStatus("Camera is not ready yet.", "error");
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

async function uploadCurrentFrame(ownerName, photoNumber = null) {
  const blob = await captureBlob();

  if (!blob) {
    return false;
  }

  const formData = new FormData();
  formData.append("file", blob, "capture.jpg");

  const label = photoNumber ? `Uploading photo ${photoNumber}...` : "Uploading...";
  setStatus(label);

  const response = await fetch(`/owners/${encodeURIComponent(ownerName)}/images`, {
    method: "POST",
    body: formData
  });

  const data = await response.json();

  if (!response.ok || !data.success) {
    const message = data.detail || data.error || "Upload failed.";
    setStatus(message, "error");
    return false;
  }

  setStatus(`Uploaded for ${data.owner}.\nImage: ${data.image}`, "ok");
  return true;
}

async function captureAndUpload() {
  const ownerName = getOwnerName();

  if (!ownerName || isUploading) {
    return;
  }

  try {
    isUploading = true;
    setButtonsDisabled(true);
    await uploadCurrentFrame(ownerName);
  } catch (error) {
    setStatus(`Upload failed: ${error.message}`, "error");
  } finally {
    isUploading = false;
    setButtonsDisabled(false);
  }
}

async function autoCapture() {
  const ownerName = getOwnerName();

  if (!ownerName || isUploading) {
    return;
  }

  try {
    isUploading = true;
    setButtonsDisabled(true);

    let uploadedCount = 0;

    for (let i = 1; i <= 5; i += 1) {
      setStatus(`Prepare photo ${i}/5...`);
      await sleep(900);

      const uploaded = await uploadCurrentFrame(ownerName, i);

      if (!uploaded) {
        break;
      }

      uploadedCount += 1;
    }

    setStatus(
      `Auto capture finished. Uploaded ${uploadedCount}/5 photos.`,
      uploadedCount > 0 ? "ok" : "error"
    );
  } catch (error) {
    setStatus(`Auto capture failed: ${error.message}`, "error");
  } finally {
    isUploading = false;
    setButtonsDisabled(false);
  }
}
