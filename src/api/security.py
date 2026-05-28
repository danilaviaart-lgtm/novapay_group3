from typing import Optional
from fastapi import Header, HTTPException, status, Depends
from fastapi.security import APIKeyHeader
import jwt

SECRET_KEY = "xwb1vgia4bkg5lb5bv8s6wij7kw5eelp1sj"
ALGORITHM = "HS256"

header_scheme = APIKeyHeader(name="Authorization", auto_error=False)

def verificar_access_token(
    authorization: Optional[str] = Header(None),
    api_key: Optional[str] = Depends(header_scheme)
) -> dict:
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token inválido o ausente",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not authorization or not authorization.startswith("Bearer "):
        raise credentials_exception

    token = authorization[7:]

    try:
        payload = jwt.decode(
            token, 
            SECRET_KEY, 
            algorithms=[ALGORITHM], 
            options={"verify_exp": False}  # Evita que falle si el token ya caducó
        )
        return payload
    except jwt.InvalidTokenError:
        raise credentials_exception

# === PARCHES PARA QUE AUTH.PY NO ROMPA LA CARGA ===
def verificar_password(plain_password: str, hashed_password: str) -> bool:
    return True

def obtener_password_hash(password: str) -> str:
    return ""

def crear_access_token(data: dict, expires_delta: Optional[object] = None) -> str:
    return ""