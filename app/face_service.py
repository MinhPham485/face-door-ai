from pathlib import Path
from typing import Optional, Dict, Any, List
import json
import math

from deepface import DeepFace


KNOWN_FACES_DIR = Path("known_faces")
EMBEDDINGS_DIR = Path("embeddings")
EMBEDDINGS_DIR.mkdir(exist_ok=True)

MODEL_NAME = "Facenet"
DETECTOR_BACKEND = "opencv"

# Bạn có thể chỉnh threshold sau khi test thực tế
FACE_DISTANCE_THRESHOLD = 0.25


def cosine_distance(vec1: List[float], vec2: List[float]) -> float:
    dot = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = math.sqrt(sum(a * a for a in vec1))
    norm2 = math.sqrt(sum(b * b for b in vec2))

    if norm1 == 0 or norm2 == 0:
        return 1.0

    similarity = dot / (norm1 * norm2)
    return 1 - similarity


def extract_embedding(image_path: str) -> Optional[List[float]]:
    """
    Tính embedding vector cho 1 ảnh.
    """
    try:
        representations = DeepFace.represent(
            img_path=image_path,
            model_name=MODEL_NAME,
            detector_backend=DETECTOR_BACKEND,
            enforce_detection=True,
        )

        if not representations:
            return None

        return representations[0]["embedding"]

    except Exception as e:
        print(f"Extract embedding error for {image_path}: {e}")
        return None


def has_face(image_path: str) -> bool:
    embedding = extract_embedding(image_path)
    return embedding is not None


def get_owner_embedding_file(owner_name: str) -> Path:
    return EMBEDDINGS_DIR / f"{owner_name}.json"


def load_owner_embeddings(owner_name: str) -> List[List[float]]:
    embedding_file = get_owner_embedding_file(owner_name)

    if not embedding_file.exists():
        return []

    with open(embedding_file, "r", encoding="utf-8") as f:
        return json.load(f)


def save_owner_embeddings(owner_name: str, embeddings: List[List[float]]):
    embedding_file = get_owner_embedding_file(owner_name)

    with open(embedding_file, "w", encoding="utf-8") as f:
        json.dump(embeddings, f)


def add_owner_embedding(owner_name: str, image_path: str) -> bool:
    """
    Khi add ảnh owner:
    - extract embedding 1 lần
    - lưu vào embeddings/{owner}.json
    """
    embedding = extract_embedding(image_path)

    if embedding is None:
        return False

    embeddings = load_owner_embeddings(owner_name)
    embeddings.append(embedding)
    save_owner_embeddings(owner_name, embeddings)

    return True


def rebuild_all_embeddings():
    """
    Dùng khi bạn đã có sẵn ảnh trong known_faces/
    và muốn build lại toàn bộ embeddings.
    """
    result = {}

    if not KNOWN_FACES_DIR.exists():
        return result

    for person_dir in KNOWN_FACES_DIR.iterdir():
        if not person_dir.is_dir():
            continue

        owner_name = person_dir.name
        owner_embeddings = []

        image_files = (
            list(person_dir.glob("*.jpg"))
            + list(person_dir.glob("*.jpeg"))
            + list(person_dir.glob("*.png"))
        )

        for image_file in image_files:
            embedding = extract_embedding(str(image_file))

            if embedding is not None:
                owner_embeddings.append(embedding)

        save_owner_embeddings(owner_name, owner_embeddings)

        result[owner_name] = {
            "image_count": len(image_files),
            "embedding_count": len(owner_embeddings),
        }

    return result


def verify_person(image_path: str) -> Dict[str, Any]:
    """
    Verify tối ưu:
    - ảnh camera chỉ extract embedding 1 lần
    - sau đó so vector với embeddings đã lưu
    """

    input_embedding = extract_embedding(image_path)

    if input_embedding is None:
        return {
            "authorized": False,
            "person": None,
            "distance": None,
            "message": "NO_FACE_DETECTED",
        }

    best_person: Optional[str] = None
    best_distance: Optional[float] = None

    embedding_files = list(EMBEDDINGS_DIR.glob("*.json"))

    if not embedding_files:
        return {
            "authorized": False,
            "person": None,
            "distance": None,
            "message": "NO_KNOWN_EMBEDDINGS",
        }

    for embedding_file in embedding_files:
        owner_name = embedding_file.stem

        with open(embedding_file, "r", encoding="utf-8") as f:
            owner_embeddings = json.load(f)

        for known_embedding in owner_embeddings:
            distance = cosine_distance(input_embedding, known_embedding)

            if best_distance is None or distance < best_distance:
                best_distance = distance
                best_person = owner_name

    if best_distance is None:
        return {
            "authorized": False,
            "person": None,
            "distance": None,
            "message": "NO_KNOWN_FACE",
        }

    if best_distance <= FACE_DISTANCE_THRESHOLD:
        return {
            "authorized": True,
            "person": best_person,
            "distance": round(best_distance, 5),
            "message": "OPEN",
        }

    return {
        "authorized": False,
        "person": None,
        "distance": round(best_distance, 5),
        "message": "DENY",
    }