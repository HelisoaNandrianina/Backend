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


@router.post("/register", response_model=UserResponse, status_code=201)
def register(
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    role: int = Form(2),
    photo: UploadFile = File(None),  # ← optionnel
    db: Session = Depends(get_db)
):
    if role not in [1, 2]:
        raise HTTPException(status_code=400, detail="Rôle invalide")

    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=400, detail="Email déjà utilisé")

    # Sauvegarde de la photo
    photo_url = None
    if photo and photo.filename:
        ext = photo.filename.split(".")[-1]
        filename = f"{uuid.uuid4()}.{ext}"
        path = os.path.join(UPLOAD_DIR, filename)
        with open(path, "wb") as f:
            shutil.copyfileobj(photo.file, f)
        photo_url = f"/{path}"

    user = User(
        name=name,
        email=email,
        password=hash_password(password),
        role=role,
        photo_url=photo_url  # ← à ajouter dans votre modèle SQLAlchemy
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
def login(body: LoginSchema, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email).first()
    if not user or not verify_password(body.password, user.password):
        raise HTTPException(status_code=401, detail="Identifiants invalides")

    # Mettre à jour last_login
    user.last_login = datetime.datetime.utcnow()
    db.commit()

    token = create_token({"sub": user.email, "id": user.id, "role": user.role})
    return {"access_token": token, "token_type": "bearer"}