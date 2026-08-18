from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.models.auth import hash_password, verify_password, create_token
from app.schemas.user import LoginSchema, TokenResponse, UserResponse
import datetime, shutil, os, uuid


router = APIRouter(prefix="/auth", tags=["Auth"])
UPLOAD_DIR = "static/photos_pdp"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(
    first_name: str = Form(...),
    last_name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    role: int = Form(2),
    photo: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    if role not in [1, 2]:
        raise HTTPException(status_code=400, detail="Rôle invalide")

    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=400, detail="Email déjà utilisé")

    photo_url = None
    if photo and photo.filename:
        ext = photo.filename.split(".")[-1]
        filename = f"{uuid.uuid4()}.{ext}"
        path = os.path.join(UPLOAD_DIR, filename)
        with open(path, "wb") as f:
            shutil.copyfileobj(photo.file, f)
        photo_url = f"/{path}"

    user = User(
        first_name=first_name,
        last_name=last_name,
        name=f"{first_name} {last_name}",
        email=email,
        password=hash_password(password),
        role=role,
        photo_url=photo_url
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_token({"sub": user.email, "id": user.id, "role": user.role})
    return TokenResponse(access_token=token, user=user) 


@router.post("/login", response_model=TokenResponse)
def login(body: LoginSchema, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email).first()
    if not user or not verify_password(body.password, user.password):
        raise HTTPException(status_code=401, detail="Identifiants invalides")

    user.last_login = datetime.datetime.utcnow()
    db.commit()

    token = create_token({"sub": user.email, "id": user.id, "role": user.role})
    return TokenResponse(access_token=token, user=user)  