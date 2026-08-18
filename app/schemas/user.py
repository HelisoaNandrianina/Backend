from pydantic import BaseModel, EmailStr, field_validator


class RegisterSchema(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    password: str
    role: int = 2

    @field_validator("role")
    def role_valide(cls, v):
        if v not in [1, 2]:
            raise ValueError("Rôle invalide")
        return v


class LoginSchema(BaseModel):
    email: EmailStr
    password: str


# ⚠️ UserResponse doit être déclaré AVANT TokenResponse
class UserResponse(BaseModel):
    id: int
    first_name: str
    last_name: str
    name: str | None
    email: str
    role: int
    status: str
    photo_url: str | None = None

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse          # ✅ UserResponse est connu ici