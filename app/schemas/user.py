from pydantic import BaseModel, EmailStr, field_validator

class RegisterSchema(BaseModel):
    name: str
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

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    role: int
    status: str

    class Config:
        from_attributes = True