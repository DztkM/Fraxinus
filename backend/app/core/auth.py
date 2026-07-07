from fastapi import Request, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from jwt import PyJWKClient


CLERK_FRONTEND_API = "https://relaxed-mustang-84.clerk.accounts.dev"
JWKS_URL = f"https://relaxed-mustang-84.clerk.accounts.dev/.well-known/jwks.json"

jwks_client = PyJWKClient(JWKS_URL)

security = HTTPBearer(auto_error=False)

async def get_current_user(
        request: Request,
        auth: HTTPAuthorizationCredentials = Security(security)
) -> str | None:
    if request.query_params.get("share_token"):
        return None
    
    if not auth:
        raise HTTPException(
            status_code=401, 
            detail="Missing authentication token"
        )
    
    token = auth.credentials

    try:
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            options={"verify_aud": False}
        )
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=401, 
                detail="user_id not found in token payload"
            )
        return user_id


    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except jwt.PyJWKClientError:
        raise HTTPException(
            status_code=500, 
            detail="Unable to fetch public keys from identity provider"
        )
