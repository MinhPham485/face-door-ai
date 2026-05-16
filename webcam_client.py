import time
import threading
import cv2
import requests


API_URL = "http://localhost:8000/verify-face"
CHECK_INTERVAL = 5

latest_result = {
    "action": "WAITING",
    "person": None,
    "is_processing": False,
}


def send_frame_to_api(frame):
    success, encoded_image = cv2.imencode(".jpg", frame)

    if not success:
        print("Failed to encode frame")
        return None

    files = {
        "file": ("frame.jpg", encoded_image.tobytes(), "image/jpeg")
    }

    try:
        response = requests.post(API_URL, files=files, timeout=20)
        return response.json()
    except Exception as e:
        print("Request error:", e)
        return None


def verify_in_background(frame):
    latest_result["is_processing"] = True
    print("Verifying...")

    result = send_frame_to_api(frame)

    if result:
        print(result)
        latest_result["action"] = result.get("action", "DENY")
        latest_result["person"] = result.get("person")
    else:
        latest_result["action"] = "ERROR"
        latest_result["person"] = None

    latest_result["is_processing"] = False


def main():
    cap = cv2.VideoCapture(0)

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    if not cap.isOpened():
        print("Cannot open camera")
        return

    last_check_time = 0

    while True:
        ret, frame = cap.read()

        if not ret:
            print("Cannot read frame")
            break


        now = time.time()

        if (
            now - last_check_time >= CHECK_INTERVAL
            and not latest_result["is_processing"]
        ):
            last_check_time = now
            frame_to_send = frame.copy()

            thread = threading.Thread(
                target=verify_in_background,
                args=(frame_to_send,),
                daemon=True,
            )
            thread.start()

        action = latest_result["action"]
        person = latest_result["person"]

        if latest_result["is_processing"]:
            label = "PROCESSING..."
        else:
            label = action
            if person:
                label += f" - {person}"

        cv2.putText(
            frame,
            label,
            (30, 50),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 255, 0) if action == "OPEN" else (0, 0, 255),
            2,
        )

        cv2.putText(
            frame,
            "Q: quit",
            (30, 90),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            2,
        )

        cv2.imshow("Face Door Camera Client", frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()