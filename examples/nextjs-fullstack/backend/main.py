"""
Auth Kit Next.js Example Backend
"""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from auth_kit_fastapi import create_auth_app, AuthConfig
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Create main app
app = FastAPI(
    title="Auth Kit Example API",
    description="Example backend for Auth Kit with Next.js",
    version="1.0.0"
)

# Configure CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure Auth Kit
auth_config = AuthConfig(
    # Database
    database_url=os.getenv("DATABASE_URL", "sqlite:///./auth_example.db"),
    
    # JWT
    jwt_secret=os.getenv("JWT_SECRET", "your-super-secret-key-change-in-production"),
    access_token_expire_minutes=30,
    refresh_token_expire_days=7,
    
    # Passkeys
    passkey_rp_id=os.getenv("PASSKEY_RP_ID", "localhost"),
    passkey_rp_name="Auth Kit Example",
    passkey_origin=os.getenv("PASSKEY_ORIGIN", "http://localhost:3000"),
    
    # Email (optional - configure for production)
    email_from=os.getenv("EMAIL_FROM"),
    smtp_host=os.getenv("SMTP_HOST"),
    smtp_port=int(os.getenv("SMTP_PORT", "587")),
    smtp_user=os.getenv("SMTP_USER"),
    smtp_password=os.getenv("SMTP_PASSWORD"),
    
    # Features
    features={
        "passkeys": True,
        "two_factor": True,
        "email_verification": bool(os.getenv("EMAIL_FROM")),  # Only if email is configured
    }
)

# Create auth app
auth_app = create_auth_app(auth_config)

# Mount auth routes
app.mount("/api/auth", auth_app)

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "Auth Kit Example API",
        "docs": "/docs",
        "auth": "/api/auth/health"
    }

# Example protected endpoint
from fastapi import Depends
from auth_kit_fastapi import get_current_user

@app.get("/api/protected")
async def protected_route(user = Depends(get_current_user)):
    """Example of a protected endpoint"""
    return {
        "message": f"Hello {user.email}!",
        "user": user.to_dict()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)