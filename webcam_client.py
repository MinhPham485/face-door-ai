import time
import cv2
import requests


API_URL = "http://localhost:8000/verify-face"
CHECK_INTERVAL = 5


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


def main():
    cap = cv2.VideoCapture(0)

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    if not cap.isOpened():
        print("Cannot open camera")
        return

    last_check_time = 0
    last_action = "WAITING"
    last_person = None

    while True:
        ret, frame = cap.read()

        if not ret:
            print("Cannot read frame")
            break
        frame = cv2.resize(frame, (640, 480))
        now = time.time()

        if now - last_check_time >= CHECK_INTERVAL:
            last_check_time = now
            result = send_frame_to_api(frame)

            if result:
                print(result)
                last_action = result.get("action", "DENY")
                last_person = result.get("person")

        label = last_action

        if last_person:
            label += f" - {last_person}"

        cv2.putText(
            frame,
            label,
            (30, 50),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 255, 0) if last_action == "OPEN" else (0, 0, 255),
            2,
        )

        cv2.imshow("Face Door Camera Client", frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()