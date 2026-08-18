# app/routes/users.py
import uuid
import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.security import hash_password, require_admin
from app.database import get_db
from app.models.token import PasswordResetToken
from app.models.user import User
from app.schemas.user import (
    InviteUserSchema,
    UserListResponse,
    UserResponse,
    UserUpdateSchema,
)
from app.services.email import send_invite_email

router = APIRouter(prefix="/api/users", tags=["Users"])

INVITE_TOKEN_EXPIRE_HOURS = 48


@router.get("", response_model=UserListResponse)
def list_users(
    q: str | None = None,
    role: int | None = None,
    status: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
):
    query = db.query(User)
    if q:
        like = f"%{q}%"
        query = query.filter(or_(User.name.ilike(like), User.email.ilike(like)))
    if role is not None:
        query = query.filter(User.role == role)
    if status:
        query = query.filter(User.status == status)

    total = query.count()
    items = (
        query.order_by(User.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return UserListResponse(items=items, total=total, page=page, page_size=page_size)


@router.post("/invite", response_model=UserResponse, status_code=201)
def invite_user(
    body: InviteUserSchema,
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
):
    if db.query(User).filter(User.email == body.email).first():
        raise HTTPException(status_code=400, detail="Email déjà utilisé")

    user = User(
        first_name=body.first_name,
        last_name=body.last_name,
        name=f"{body.first_name} {body.last_name}",
        email=body.email,
        password=hash_password(str(uuid.uuid4())),
        role=body.role,
        status="pending",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    invite_token = str(uuid.uuid4())
    expires = datetime.datetime.utcnow() + datetime.timedelta(hours=INVITE_TOKEN_EXPIRE_HOURS)
    db.add(PasswordResetToken(token=invite_token, user_id=user.id, expires_at=expires))
    db.commit()

    send_invite_email(user.email, invite_token)
    return user


@router.patch("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    body: UserUpdateSchema,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    if user_id == admin.id:
        raise HTTPException(
            status_code=400,
            detail="Vous ne pouvez pas modifier votre propre compte administrateur ici",
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")

    if body.role is not None:
        user.role = body.role
    if body.status is not None:
        user.status = body.status

    db.commit()
    db.refresh(user)
    return user


@router.delete("/{user_id}", response_model=UserResponse)
def deactivate_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="Vous ne pouvez pas désactiver votre propre compte")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")

    # Soft delete : reports/notifications/data_points référencent potentiellement
    # users.id en clé étrangère, donc on désactive au lieu de supprimer la ligne.
    user.status = "inactive"
    db.commit()
    db.refresh(user)
    return user
