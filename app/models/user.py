from sqlalchemy import Column, Integer, String, DateTime
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String, nullable=False)  
    last_name = Column(String, nullable=False)   
    name = Column(String, nullable=True)          
    email = Column(String, unique=True, index=True)
    password = Column(String)
    role = Column(Integer, default=2)
    status = Column(String, default="active")
    photo_url = Column(String, nullable=True)
    last_login = Column(DateTime, nullable=True)