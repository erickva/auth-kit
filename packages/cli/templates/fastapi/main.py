from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

from auth_kit_fastapi import AuthConfig, init_auth, auth_router, Base

# Load environment variables
load_dotenv()

# Create FastAPI app
app = FastAPI(
    title="{{PROJECT_NAME_TITLE}} API",
    description="API for {{PROJECT_NAME_TITLE}}",
    version="1.0.0",
)

# Database setup
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")
engine = create_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create database tables
Base.metadata.create_all(bind=engine)

# CORS configuration
origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure Auth Kit
auth_config = AuthConfig(
    jwt_secret=os.getenv("JWT_SECRET", "your-secret-key-change-this"),
    jwt_algorithm=os.getenv("JWT_ALGORITHM", "HS256"),
    access_token_expire_minutes=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")),
    refresh_token_expire_days=int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "30")),
    passkey_rp_id=os.getenv("PASSKEY_RP_ID", "localhost"),
    passkey_rp_name=os.getenv("PASSKEY_RP_NAME", "{{PROJECT_NAME_TITLE}}"),
    passkey_origin=os.getenv("PASSKEY_ORIGIN", "http://localhost:3000"),
)

# Initialize Auth Kit
init_auth(app, auth_config, SessionLocal)

# Mount auth routes
app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])

@app.get("/")
async def root():
    return {"message": "Welcome to {{PROJECT_NAME_TITLE}} API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)