from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.models.auth import hash_password, verify_password, create_token
from app.schemas.user import RegisterSchema, LoginSchema, TokenResponse, UserResponse
import datetime

router = APIRouter(prefix="/auth", tags=["Auth"])

@router.post("/register", response_model=UserResponse, status_code=201)
def register(body: RegisterSchema, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == body.email).first():
        raise HTTPException(status_code=400, detail="Email déjà utilisé")

    user = User(
        name=body.name,
        email=body.email,
        password=hash_password(body.password),
        role=body.role
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