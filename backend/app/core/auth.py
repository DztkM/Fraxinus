from fastapi import Request, HTTPException, Security, Header, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import hashlib
import jwt
from jwt import PyJWKClient
from pydantic import BaseModel, Field

from core.config import settings
from core.database import get_db
from models.api_key import NamespaceAPIKey

CLERK_FRONTEND_API = settings.CLERK_FRONTEND_API
JWKS_URL = f"{CLERK_FRONTEND_API}/.well-known/jwks.json"
CLERK_NAMESPACE_ID = "00000000-0000-0000-0000-000000000001"

jwks_client = PyJWKClient(JWKS_URL)
security = HTTPBearer(auto_error=False)

class AuthContext(BaseModel):
    user_id: str
    namespace_id: str
    is_admin: bool = False

async def get_current_user(
        request: Request,
        x_user_id: str | None = Header(default=None, alias="X-User-Id", description="Required for B2B API requests"),
        auth: HTTPAuthorizationCredentials = Security(security),
        db: AsyncSession = Depends(get_db)
) -> AuthContext | None:
    if request.query_params.get("share_token"):
        return None
    
    if not auth:
        raise HTTPException(
            status_code=401, 
            detail="Missing authentication token"
        )
    
    token = auth.credentials

    # Try to decode as Clerk token first
    try:
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            options={"verify_aud": False},
            leeway=60
        )
        user_id = payload.get("sub")
        public_metadata = payload.get("public_metadata", {})
        is_admin = public_metadata.get("role") == "admin"
        
        if not user_id:
            raise HTTPException(
                status_code=401, 
                detail="user_id not found in token payload"
            )
        return AuthContext(user_id=user_id, namespace_id=CLERK_NAMESPACE_ID, is_admin=is_admin)
    
    except (jwt.ExpiredSignatureError, jwt.PyJWKClientError) as e:
        # It's a JWT but it failed validation
        raise HTTPException(status_code=401, detail=f"Token validation failed: {str(e)}")
    except jwt.InvalidTokenError:
        # Not a valid Clerk JWT, fallback to checking as B2B API key
        pass
    
    # Try B2B API key
    key_hash = hashlib.sha256(token.encode()).hexdigest()
    result = await db.execute(
        select(NamespaceAPIKey)
        .where(NamespaceAPIKey.key_hash == key_hash)
    )
    api_key = result.scalars().first()
    
    if api_key:
        if not x_user_id:
            raise HTTPException(status_code=400, detail="Missing X-User-Id header for B2B request")
        return AuthContext(user_id=x_user_id, namespace_id=str(api_key.namespace_id))
    
    # It's neither a valid Clerk JWT nor a valid API key
    raise HTTPException(status_code=401, detail="Invalid token or API key")

async def get_clerk_user(
        ctx: AuthContext | None = Depends(get_current_user)
) -> AuthContext:
    if not ctx:
        raise HTTPException(status_code=401, detail="Authentication required")
    if ctx.namespace_id != CLERK_NAMESPACE_ID:
        raise HTTPException(status_code=403, detail="Clerk authentication required")
    return ctx
