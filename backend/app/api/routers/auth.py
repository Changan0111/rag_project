from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import verify_password, get_password_hash, create_access_token, decode_access_token
from app.core.config import settings, UPLOAD_PATH
from app.models import User
from app.schemas import UserCreate, UserResponse, Token
from typing import Optional
from pydantic import BaseModel
from datetime import datetime
import os
import uuid
import shutil

router = APIRouter(prefix="/auth", tags=["认证"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

class LoginForm(BaseModel):
    username: str
    password: str
    role: Optional[str] = None


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无法验证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception
    
    user_id: Optional[int] = payload.get("user_id")
    if user_id is None:
        raise credentials_exception
    
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception
    
    return user


def get_current_admin(
    current_user: User = Depends(get_current_user)
) -> User:
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限"
        )
    return current_user


def get_current_user_optional(
    token: Optional[str] = Depends(OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)),
    db: Session = Depends(get_db)
) -> Optional[User]:
    if token is None:
        return None
    
    payload = decode_access_token(token)
    if payload is None:
        return None
    
    user_id: Optional[int] = payload.get("user_id")
    if user_id is None:
        return None
    
    user = db.query(User).filter(User.id == user_id).first()
    return user


def is_admin(user: User) -> bool:
    return user.role == "admin"


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.username == user_data.username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已存在"
        )
    
    hashed_password = get_password_hash(user_data.password)
    
    new_user = User(
        username=user_data.username,
        phone=user_data.phone,
        password=hashed_password,
        role="user"
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return new_user


@router.post("/login", response_model=Token)
def login(login_data: LoginForm, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == login_data.username).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not verify_password(login_data.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if login_data.role and login_data.role != user.role:
        if login_data.role == "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="您不是管理员，无法以管理员身份登录",
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="管理员请使用管理员身份登录",
            )

    # ✅ 更新最后登录时间
    user.last_login_at = datetime.now()
    db.commit()

    access_token = create_access_token(
        data={"user_id": user.id, "username": user.username, "role": user.role}
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": user.role,
        "username": user.username
    }


@router.get("/profile", response_model=UserResponse)
def get_profile(current_user: User = Depends(get_current_user)):
    return current_user


class ProfileUpdate(BaseModel):
    username: Optional[str] = None
    phone: Optional[str] = None


class PasswordUpdate(BaseModel):
    old_password: str
    new_password: str


@router.put("/profile", response_model=UserResponse)
def update_profile(
    update_data: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if update_data.username and update_data.username != current_user.username:
        existing_user = db.query(User).filter(User.username == update_data.username).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="用户名已存在"
            )
        current_user.username = update_data.username
    
    if update_data.phone:
        current_user.phone = update_data.phone
    
    db.commit()
    db.refresh(current_user)
    
    return current_user


@router.put("/password")
def update_password(
    password_data: PasswordUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not verify_password(password_data.old_password, current_user.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="原密码错误"
        )
    
    current_user.password = get_password_hash(password_data.new_password)
    db.commit()
    
    return {"message": "密码修改成功"}


@router.post("/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    allowed_types = ["image/jpeg", "image/png", "image/gif", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不支持的文件类型，仅支持 JPG、PNG、GIF、WEBP 格式"
        )
    
    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)
    
    if file_size > settings.MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"文件大小超过限制（最大 {settings.MAX_FILE_SIZE // 1024 // 1024}MB）"
        )
    
    file_ext = os.path.splitext(file.filename)[1]
    filename = f"{current_user.id}_{uuid.uuid4().hex}{file_ext}"
    avatar_dir = os.path.join(UPLOAD_PATH, "avatars")
    file_path = os.path.join(avatar_dir, filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    avatar_url = f"/uploads/avatars/{filename}"
    
    if current_user.avatar and current_user.avatar.startswith("/uploads/avatars/"):
        old_filename = current_user.avatar.split("/")[-1]
        old_file_path = os.path.join(avatar_dir, old_filename)
        if os.path.exists(old_file_path):
            os.remove(old_file_path)
    
    current_user.avatar = avatar_url
    db.commit()
    db.refresh(current_user)
    
    return {"avatar_url": avatar_url}
