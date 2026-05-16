import shutil
import uuid
import re
from fastapi.responses import FileResponse
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles


from app.face_service import verify_person, add_owner_embedding, rebuild_all_embeddings

app = FastAPI(
    title="Face Door AI Service",
    docs_url="/api-docs",
    redoc_url=None,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = PROJECT_ROOT / "static"
UPLOAD_DIR = PROJECT_ROOT / "uploads"
KNOWN_FACES_DIR = PROJECT_ROOT / "known_faces"
ENROLL_PAGE = STATIC_DIR / "enroll.html"
VERIFY_PAGE = STATIC_DIR / "verify.html"
DOCS_PAGE = STATIC_DIR / "docs.html"

UPLOAD_DIR.mkdir(exist_ok=True)
KNOWN_FACES_DIR.mkdir(exist_ok=True)

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png"}
OWNER_NAME_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,50}$")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def validate_image_file(file: UploadFile):
    file_ext = Path(file.filename or "").suffix.lower()

    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Only .jpg, .jpeg, .png files are allowed",
        )

    return file_ext


def validate_owner_name(owner_name: str) -> str:
    if not OWNER_NAME_PATTERN.fullmatch(owner_name):
        raise HTTPException(
            status_code=400,
            detail="Owner name can only contain letters, numbers, underscore, or hyphen",
        )

    return owner_name


@app.get("/")
def root():
    return {
        "service": "Face Door AI Service",
        "status": "running",
        "docs": "/docs",
        "api_docs": "/api-docs",
        "enroll": "/enroll",
        "verify": "/verify",
    }


@app.get("/health")
def health_check():
    return {
        "status": "ok",
    }


@app.get("/iot/ping")
def iot_ping():
    return {
        "success": True,
        "message": "AI_SERVER_READY",
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
    owner_name = validate_owner_name(owner_name)

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

@app.get("/docs", include_in_schema=False)
def docs_page():
    return FileResponse(DOCS_PAGE)


@app.get("/enroll", include_in_schema=False)
def enroll_page():
    return FileResponse(ENROLL_PAGE)


@app.get("/verify", include_in_schema=False)
def verify_page():
    return FileResponse(VERIFY_PAGE)
