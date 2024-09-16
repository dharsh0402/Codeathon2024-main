from pydantic import BaseModel, EmailStr

# Input model for creating a user
class UserIn(BaseModel):
    name: str
    email: EmailStr
    password: str

# Response model for returning user details (excluding password)
class User(BaseModel):  # This is the same as UserOut, but using the existing 'User'
    id: int
    name: str
    email: EmailStr

# Input model for logging in a user
class UserLogin(BaseModel):
    email: EmailStr
    password: str
