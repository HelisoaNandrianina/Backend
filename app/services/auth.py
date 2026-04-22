from pydantic import BaseModel, EmailStr
from datetime import datetime



class UserRegister(BaseModel):
    name: str
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str



class UserOut(BaseModel):
    id: int
    name: str
    email: str
    role: int
    status: str
    last_login: datetime

    model_config = {"from_attributes": True}  

class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut