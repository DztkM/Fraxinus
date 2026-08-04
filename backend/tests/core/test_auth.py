import pytest
import hashlib
from fastapi import Request, HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from unittest.mock import AsyncMock, Mock, patch
import jwt

from core.auth import get_current_user, get_clerk_user, CLERK_NAMESPACE_ID, AuthContext
from core.config import settings

@pytest.fixture
def mock_request():
    request = Mock(spec=Request)
    request.query_params = {}
    request.headers = {}
    return request

@pytest.fixture
def mock_db():
    return AsyncMock()

@pytest.mark.asyncio
async def test_missing_token(mock_request, mock_db):
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(mock_request, None, None, mock_db)
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Missing authentication token"

@pytest.mark.asyncio
async def test_b2b_api_key_success(mock_request, mock_db):
    api_key_str = "valid_api_key_123"
    auth = HTTPAuthorizationCredentials(scheme="Bearer", credentials=api_key_str)
    x_user_id = "b2b_user_1"

    # Mock DB response
    mock_result = Mock()
    mock_api_key_obj = Mock()
    mock_api_key_obj.namespace_id = "b2b-namespace-123"
    mock_result.scalars.return_value.first.return_value = mock_api_key_obj
    mock_db.execute.return_value = mock_result

    ctx = await get_current_user(mock_request, x_user_id, auth, mock_db)
    
    assert isinstance(ctx, AuthContext)
    assert ctx.user_id == "b2b_user_1"
    assert ctx.namespace_id == "b2b-namespace-123"
    mock_db.execute.assert_called_once()

@pytest.mark.asyncio
async def test_b2b_api_key_missing_header(mock_request, mock_db):
    api_key_str = "valid_api_key_123"
    auth = HTTPAuthorizationCredentials(scheme="Bearer", credentials=api_key_str)
    x_user_id = None

    # Mock DB response
    mock_result = Mock()
    mock_api_key_obj = Mock()
    mock_api_key_obj.namespace_id = "b2b-namespace-123"
    mock_result.scalars.return_value.first.return_value = mock_api_key_obj
    mock_db.execute.return_value = mock_result

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(mock_request, x_user_id, auth, mock_db)
    assert exc_info.value.status_code == 400
    assert "Missing X-User-Id header" in exc_info.value.detail

@pytest.mark.asyncio
async def test_b2b_api_key_invalid(mock_request, mock_db):
    api_key_str = "invalid_api_key"
    auth = HTTPAuthorizationCredentials(scheme="Bearer", credentials=api_key_str)
    x_user_id = "b2b_user_1"

    # Mock DB response returning None
    mock_result = Mock()
    mock_result.scalars.return_value.first.return_value = None
    mock_db.execute.return_value = mock_result

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(mock_request, x_user_id, auth, mock_db)
    assert exc_info.value.status_code == 401
    assert "Invalid token or API key" in exc_info.value.detail

@pytest.mark.asyncio
@patch("core.auth.jwks_client.get_signing_key_from_jwt")
@patch("core.auth.jwt.decode")
async def test_clerk_token_success(mock_jwt_decode, mock_get_signing_key, mock_request, mock_db):
    # Mock JWKS and JWT decode for Clerk token
    mock_get_signing_key.return_value.key = "fake_key"
    mock_jwt_decode.return_value = {"sub": "clerk_user_1"}
    
    clerk_token = "fake.clerk.token"
    auth = HTTPAuthorizationCredentials(scheme="Bearer", credentials=clerk_token)

    ctx = await get_current_user(mock_request, None, auth, mock_db)
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
