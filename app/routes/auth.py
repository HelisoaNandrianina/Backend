from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from jose import JWTError
from app.database import get_db
from app.models.user import User
from app.models.token import TokenBlacklist, PasswordResetToken
from app.models.auth import hash_password, verify_password, create_token, decode_token
from app.core.deps import get_current_user, oauth2_scheme
from app.services.email import send_reset_email
from app.schemas.user import (
    LoginSchema, TokenResponse, UserResponse,
    ForgotPasswordSchema, ResetPasswordSchema, MessageResponse,
)
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


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/refresh", response_model=TokenResponse)
def refresh(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = decode_token(token)
    except JWTError:
        raise HTTPException(status_code=401, detail="Token invalide ou expiré")

    old_jti = payload.get("jti")
    email = payload.get("sub")
    exp_ts = payload.get("exp")

    if not old_jti or not email or not exp_ts:
        raise HTTPException(status_code=401, detail="Token invalide ou expiré")

    if db.query(TokenBlacklist).filter(TokenBlacklist.jti == old_jti).first():
        raise HTTPException(status_code=401, detail="Token invalide ou expiré")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=401, detail="Utilisateur introuvable")

    db.add(TokenBlacklist(
        jti=old_jti,
        expires_at=datetime.datetime.utcfromtimestamp(exp_ts),
    ))
    db.commit()

    new_token = create_token({"sub": user.email, "id": user.id, "role": user.role})
    return TokenResponse(access_token=new_token, user=user)


@router.post("/logout", response_model=MessageResponse)
def logout(
    token: str = Depends(oauth2_scheme),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    payload = decode_token(token)
    jti = payload.get("jti")
    exp_ts = payload.get("exp")

    already = db.query(TokenBlacklist).filter(TokenBlacklist.jti == jti).first()
    if not already:
        db.add(TokenBlacklist(
            jti=jti,
            expires_at=datetime.datetime.utcfromtimestamp(exp_ts),
        ))
        db.commit()

    return {"message": "Déconnexion réussie"}


@router.post("/forgot-password", response_model=MessageResponse)
def forgot_password(body: ForgotPasswordSchema, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email).first()

    if user:
        raw_token = str(uuid.uuid4())
        expires = datetime.datetime.utcnow() + datetime.timedelta(minutes=30)
        db.add(PasswordResetToken(
            token=raw_token,
            user_id=user.id,
            expires_at=expires,
        ))
        db.commit()
        send_reset_email(user.email, raw_token)

    return {"message": "Si cet email existe, un lien de réinitialisation a été envoyé."}


@router.post("/reset-password", response_model=MessageResponse)
def reset_password(body: ResetPasswordSchema, db: Session = Depends(get_db)):
    reset = db.query(PasswordResetToken).filter(
        PasswordResetToken.token == body.token
    ).first()

    if not reset or reset.used or reset.expires_at < datetime.datetime.utcnow():
        raise HTTPException(status_code=400, detail="Token invalide ou expiré")

    user = db.query(User).filter(User.id == reset.user_id).first()
    if not user:
        raise HTTPException(status_code=400, detail="Utilisateur introuvable")

    user.password = hash_password(body.new_password)
    reset.used = True
    db.commit()

    return {"message": "Mot de passe réinitialisé avec succès"}