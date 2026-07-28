import pytest
from fastapi import Request, HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from unittest.mock import Mock, patch
import jwt

from core.auth import get_current_user, get_clerk_user, CLERK_NAMESPACE_ID, AuthContext
from core.config import settings

@pytest.fixture
def mock_request():
    request = Mock(spec=Request)
    request.query_params = {}
    request.headers = {}
    return request

@pytest.mark.asyncio
async def test_missing_token(mock_request):
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(mock_request, None, None)
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Missing authentication token"

@pytest.mark.asyncio
async def test_b2b_token_success(mock_request):
    # Generate a valid B2B token
    b2b_token = jwt.encode(
        {"namespace_id": "b2b-namespace-123"},
        settings.SECRET_KEY,
        algorithm="HS256"
    )
    auth = HTTPAuthorizationCredentials(scheme="Bearer", credentials=b2b_token)
    x_user_id = "b2b_user_1"

    ctx = await get_current_user(mock_request, x_user_id, auth)
    assert isinstance(ctx, AuthContext)
    assert ctx.user_id == "b2b_user_1"
    assert ctx.namespace_id == "b2b-namespace-123"

@pytest.mark.asyncio
async def test_b2b_token_missing_header(mock_request):
    b2b_token = jwt.encode(
        {"namespace_id": "b2b-namespace-123"},
        settings.SECRET_KEY,
        algorithm="HS256"
    )
    auth = HTTPAuthorizationCredentials(scheme="Bearer", credentials=b2b_token)
    # Don't set x_user_id
    x_user_id = None

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(mock_request, x_user_id, auth)
    assert exc_info.value.status_code == 400
    assert "Missing X-User-Id header" in exc_info.value.detail

@pytest.mark.asyncio
@patch("core.auth.jwks_client.get_signing_key_from_jwt")
@patch("core.auth.jwt.decode")
async def test_clerk_token_success(mock_jwt_decode, mock_get_signing_key, mock_request):
    # Mock JWKS and JWT decode for Clerk token
    mock_get_signing_key.return_value.key = "fake_key"
    mock_jwt_decode.return_value = {"sub": "clerk_user_1"}
    
    clerk_token = "fake.clerk.token"
    auth = HTTPAuthorizationCredentials(scheme="Bearer", credentials=clerk_token)

    def mock_decode_side_effect(token, key, algorithms, **kwargs):
        if key == settings.SECRET_KEY:
            raise jwt.InvalidTokenError("Not a B2B token")
        return {"sub": "clerk_user_1"}
        
    mock_jwt_decode.side_effect = mock_decode_side_effect

    ctx = await get_current_user(mock_request, None, auth)
    assert isinstance(ctx, AuthContext)
    assert ctx.user_id == "clerk_user_1"
    assert ctx.namespace_id == CLERK_NAMESPACE_ID

@pytest.mark.asyncio
async def test_get_clerk_user_success():
    ctx_input = AuthContext(user_id="clerk_user_1", namespace_id=CLERK_NAMESPACE_ID)
    
    ctx = await get_clerk_user(ctx=ctx_input)
    assert ctx.user_id == "clerk_user_1"

@pytest.mark.asyncio
async def test_get_clerk_user_forbidden():
    ctx_input = AuthContext(user_id="b2b_user_1", namespace_id="other-namespace")
    
    with pytest.raises(HTTPException) as exc_info:
        await get_clerk_user(ctx=ctx_input)
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Clerk authentication required"
