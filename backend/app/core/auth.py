from fastapi import Request, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from jwt import PyJWKClient
from pydantic import BaseModel, Field

from core.config import settings

CLERK_FRONTEND_API = settings.CLERK_FRONTEND_API
JWKS_URL = f"{CLERK_FRONTEND_API}/.well-known/jwks.json"
CLERK_NAMESPACE_ID = "00000000-0000-0000-0000-000000000001"

jwks_client = PyJWKClient(JWKS_URL)
security = HTTPBearer(auto_error=False)

class AuthContext(BaseModel):
    user_id: str
    namespace_id: str

async def get_current_user(
        request: Request,
        auth: HTTPAuthorizationCredentials = Security(security)
) -> AuthContext | None:
    if request.query_params.get("share_token"):
        return None
    
    if not auth:
        raise HTTPException(
            status_code=401, 
            detail="Missing authentication token"
        )
    
    token = auth.credentials

    # try to decode as B2B token
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=["HS256"],
            options={"verify_aud": False}
        )
        # token must have namespace_id
        namespace_id = payload.get("namespace_id")
        if namespace_id:
            user_id = request.headers.get("X-User-Id")
            if not user_id:
                raise HTTPException(status_code=400, detail="Missing X-User-Id header for B2B request")
            return AuthContext(user_id=user_id, namespace_id=namespace_id)
    except jwt.InvalidTokenError:
        pass # Not a valid B2B token, fallback to Clerk

    # if it's not a B2B token, it might be a Clerk token
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
        if not user_id:
            raise HTTPException(
                status_code=401, 
                detail="user_id not found in token payload"
            )
        return AuthContext(user_id=user_id, namespace_id=CLERK_NAMESPACE_ID)

    except jwt.ExpiredSignatureError as e:
        raise HTTPException(status_code=401, detail=f"Token has expired: {str(e)}")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")
    except jwt.PyJWKClientError:
        raise HTTPException(
            status_code=500, 
            detail="Unable to fetch public keys from identity provider"
        )

async def get_clerk_user(
        request: Request,
        auth: HTTPAuthorizationCredentials = Security(security)
) -> AuthContext:
    ctx = await get_current_user(request, auth)
    if not ctx:
        raise HTTPException(status_code=401, detail="Authentication required")
    if ctx.namespace_id != CLERK_NAMESPACE_ID:
        raise HTTPException(status_code=403, detail="Clerk authentication required")
    return ctx
