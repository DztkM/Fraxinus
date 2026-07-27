from pydantic import BaseModel

class B2BTokenRequest(BaseModel):
    api_key: str

class B2BTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
