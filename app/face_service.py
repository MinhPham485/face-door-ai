from pathlib import Path
from typing import Optional, Dict, Any

from deepface import DeepFace


KNOWN_FACES_DIR = Path("known_faces")

MODEL_NAME = "Facenet"
DETECTOR_BACKEND = "opencv"
FACE_DISTANCE_THRESHOLD = 0.25

def has_face(image_path: str) -> bool:
    try:
        faces = DeepFace.extract_faces(
            img_path=image_path,
            detector_backend=DETECTOR_BACKEND,
            enforce_detection=True,
        )
        return len(faces) > 0
    except Exception:
        return False


def verify_person(image_path: str) -> Dict[str, Any]:
    best_person: Optional[str] = None
    best_distance: Optional[float] = None
    best_verified = False

    if not KNOWN_FACES_DIR.exists():
        return {
            "authorized": False,
            "person": None,
            "distance": None,
            "message": "KNOWN_FACES_DIR_NOT_FOUND",
        }

    for person_dir in KNOWN_FACES_DIR.iterdir():
        if not person_dir.is_dir():
            continue

        person_name = person_dir.name

        image_files = (
            list(person_dir.glob("*.jpg"))
            + list(person_dir.glob("*.jpeg"))
            + list(person_dir.glob("*.png"))
        )

        for known_image in image_files:
            try:
                result = DeepFace.verify(
                    img1_path=str(known_image),
                    img2_path=image_path,
                    model_name=MODEL_NAME,
                    detector_backend=DETECTOR_BACKEND,
                    enforce_detection=True,
                )

                distance = float(result["distance"])
                verified = bool(result["verified"])

                if best_distance is None or distance < best_distance:
                    best_distance = distance
                    best_person = person_name
                    best_verified = verified

            except Exception as e:
                print(f"Error comparing {known_image} with {image_path}: {e}")
                continue

    if best_distance is None:
        return {
            "authorized": False,
            "person": None,
            "distance": None,
            "message": "NO_FACE_DETECTED_OR_NO_KNOWN_FACE",
        }

    if best_distance <= FACE_DISTANCE_THRESHOLD:
          return {
            "authorized": True,
            "person": best_person,
            "distance": best_distance,
            "message": "OPEN",
    }
    return {
        "authorized": False,
        "person": None,
        "distance": best_distance,
        "message": "DENY",
    }