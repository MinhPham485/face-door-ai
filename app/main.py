import shutil
import uuid
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware


from app.face_service import verify_person, add_owner_embedding, rebuild_all_embeddings

app = FastAPI(title="Face Door AI Service")

UPLOAD_DIR = Path("uploads")
KNOWN_FACES_DIR = Path("known_faces")

UPLOAD_DIR.mkdir(exist_ok=True)
KNOWN_FACES_DIR.mkdir(exist_ok=True)

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png"}


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def validate_image_file(file: UploadFile):
    file_ext = Path(file.filename or "").suffix.lower()

    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Only .jpg, .jpeg, .png files are allowed",
        )

    return file_ext


@app.get("/")
def root():
    return {
        "service": "Face Door AI Service",
        "status": "running",
    }


@app.get("/health")
def health_check():
    return {
        "status": "ok",
    }


@app.get("/owners")
def list_owners():
    owners = []

    for owner_dir in KNOWN_FACES_DIR.iterdir():
        if not owner_dir.is_dir():
            continue

        image_count = (
            len(list(owner_dir.glob("*.jpg")))
            + len(list(owner_dir.glob("*.jpeg")))
            + len(list(owner_dir.glob("*.png")))
        )

        owners.append({
            "name": owner_dir.name,
            "image_count": image_count,
        })

    return {
        "success": True,
        "owners": owners,
    }


@app.post("/owners/{owner_name}/images")
async def add_owner_image(
    owner_name: str,
    file: UploadFile = File(...)
):
    file_ext = validate_image_file(file)

    owner_dir = KNOWN_FACES_DIR / owner_name
    owner_dir.mkdir(parents=True, exist_ok=True)

    image_filename = f"{uuid.uuid4()}{file_ext}"
    image_path = owner_dir / image_filename

    try:
        with open(image_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        embedding_created = add_owner_embedding(owner_name, str(image_path))

        if not embedding_created:
            image_path.unlink(missing_ok=True)
            raise HTTPException(
                status_code=400,
                detail="No face detected in uploaded image",
    )

        return {
            "success": True,
            "message": "OWNER_IMAGE_ADDED",
            "owner": owner_name,
            "image": str(image_path),
        }

    except HTTPException:
        raise

    except Exception as e:
        image_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=500,
            detail=str(e),
        )


@app.post("/verify-face")
async def verify_face(file: UploadFile = File(...)):
    file_ext = validate_image_file(file)

    temp_filename = f"{uuid.uuid4()}{file_ext}"
    temp_path = UPLOAD_DIR / temp_filename

    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        result = verify_person(str(temp_path))

        return {
            "success": True,
            "authorized": result["authorized"],
            "person": result["person"],
            "distance": result["distance"],
            "message": result["message"],
            "action": "OPEN" if result["authorized"] else "DENY",
        }

    except Exception as e:
        return {
            "success": False,
            "authorized": False,
            "person": None,
            "distance": None,
            "message": "ERROR",
            "action": "DENY",
            "error": str(e),
        }

    finally:
        temp_path.unlink(missing_ok=True)

@app.post("/embeddings/rebuild")
def rebuild_embeddings():
    result = rebuild_all_embeddings()

    return {
        "success": True,
        "message": "EMBEDDINGS_REBUILT",
        "result": result,
    }