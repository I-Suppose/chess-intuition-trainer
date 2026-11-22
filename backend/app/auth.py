import uuid
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from supabase import create_client
from app.core.config import settings
from app.database import get_db
from app.models import User
from sqlalchemy.orm import Session

bearer = HTTPBearer()


def current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer), db: Session = Depends(get_db)) -> User:
    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise HTTPException(status_code=503, detail="Supabase authentication is not configured. Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY.")
    try:
        client = create_client(settings.supabase_url, settings.supabase_service_role_key)
        auth_user = client.auth.get_user(credentials.credentials).user
        user_id = uuid.UUID(auth_user.id)
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired sign-in token.") from exc
    user = db.get(User, user_id)
    if not user:
        user = User(id=user_id, email=getattr(auth_user, "email", None))
        db.add(user)
        db.commit()
        db.refresh(user)
    return user
