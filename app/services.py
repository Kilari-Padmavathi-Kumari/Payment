from sqlalchemy.orm import Session
from passlib.context import CryptContext
from app.models import User
from app.schemas import UserCreate

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


#  User Services 
def get_user(db: Session, user_id: str) -> User | None:
    """Fetch a user by user_id"""
    return db.query(User).filter(User.user_id == user_id).first()


def get_user_by_email(db: Session, email: str) -> User | None:
    """Fetch a user by email"""
    return db.query(User).filter(User.email == email).first()


def create_user(db: Session, user: UserCreate) -> User:
    """Create a new user in the database"""
    # Hash the password
    hashed_password = pwd_context.hash(user.password)
    
    db_user = User(
        user_id=user.user_id,
        email=user.email,
        full_name=user.full_name,
        password=hashed_password,
        is_active=True
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def authenticate_user(db: Session, user_id: str, password: str) -> User | None:
    """Verify user credentials"""
    user = get_user(db, user_id)
    if not user:
        return None
    if not pwd_context.verify(password, user.password):
        return None
    return user