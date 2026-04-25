from sqlalchemy import Column, Integer, String, DateTime
from app.database import Base
import datetime

class User(Base):
    __tablename__ = "users"

    id         = Column(Integer, primary_key=True, index=True)
    name       = Column(String, nullable=False)
    email      = Column(String, unique=True, nullable=False)
    password   = Column(String, nullable=False)          

    role       = Column(Integer, default=2)              # 1=admin, 2=analyst
    status     = Column(String, default="active")

    photo_url  = Column(String, nullable=True)         
    last_login = Column(DateTime, default=datetime.datetime.utcnow)