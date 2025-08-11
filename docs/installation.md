# Installation

Auth Kit is available as separate packages for different frameworks. This guide will help you install and set up Auth Kit in your project.

## Quick Start with CLI (Recommended)

The fastest way to get started with Auth Kit is using our CLI tool:

```bash
# Create a new project with authentication pre-configured
npx @auth-kit/cli create my-app

# Or add Auth Kit to an existing project
cd my-existing-project
npx @auth-kit/cli add
```

The CLI will:
- Set up all necessary dependencies
- Configure authentication features you select
- Generate environment files
- Create example components
- Set up database migrations (if using backend)

## Prerequisites

- Node.js 18+ (for React/Next.js)
- Python 3.8+ (for FastAPI)
- A database (PostgreSQL recommended, SQLite for development)

## Manual Installation

If you prefer to install Auth Kit manually or need to customize the setup, follow these instructions:

### React Installation

#### 1. Install Packages

```bash
npm install @auth-kit/core @auth-kit/react
# or
yarn add @auth-kit/core @auth-kit/react
# or
pnpm add @auth-kit/core @auth-kit/react
```

### 2. Peer Dependencies

Auth Kit requires React 16.8 or higher:

```bash
npm install react react-dom
```

### 3. TypeScript Support

Auth Kit is written in TypeScript and includes type definitions. No additional setup required!

## FastAPI Installation

### 1. Install Package

```bash
pip install auth-kit-fastapi
```

### 2. Dependencies

The following dependencies are automatically installed:
- FastAPI
- SQLAlchemy
- Pydantic
- python-jose[cryptography] (for JWT)
- passlib[bcrypt] (for password hashing)
- python-multipart (for form data)
- webauthn (for passkeys)
- pyotp (for 2FA)

### 3. Database Drivers

Install the appropriate database driver:

```bash
# PostgreSQL
pip install psycopg2-binary

# MySQL
pip install mysqlclient

# SQLite (included with Python)
```

## Next.js Installation

For Next.js applications, install both the React and core packages:

```bash
npm install @auth-kit/core @auth-kit/react
```

### App Router Setup

Create a provider component for the App Router:

```typescript
// app/providers.tsx
'use client'

import { AuthProvider } from '@auth-kit/react'
import { StorageType } from '@auth-kit/core'

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <AuthProvider
      config={{
        apiUrl: process.env.NEXT_PUBLIC_API_URL!,
        storageType: StorageType.Cookies,
      }}
    >
      {children}
    </AuthProvider>
  )
}
```

## Database Setup

### PostgreSQL

1. Create a database:
```sql
CREATE DATABASE authkit_db;
```

2. Update your connection string:
```env
DATABASE_URL=postgresql://user:password@localhost:5432/authkit_db
```

### SQLite (Development)

For development, SQLite requires no setup:
```env
DATABASE_URL=sqlite:///./authkit.db
```

## Environment Variables

Create a `.env` file in your project root:

### Frontend (.env.local for Next.js)
```env
# API Configuration
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_APP_URL=http://localhost:3000

# Optional
NEXT_PUBLIC_ENABLE_PASSKEYS=true
NEXT_PUBLIC_ENABLE_2FA=true
```

### Backend (.env)
```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/authkit_db

# JWT Configuration
JWT_SECRET=your-super-secret-key-change-in-production
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=30

# Passkey Configuration
PASSKEY_RP_ID=localhost
PASSKEY_RP_NAME=My App
PASSKEY_ORIGIN=http://localhost:3000

# Email Configuration (optional)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
EMAIL_FROM=noreply@myapp.com

# Application
APP_NAME=My App
APP_URL=http://localhost:3000
```

## Verify Installation

### React

Create a simple test component:

```tsx
import { useAuth } from '@auth-kit/react'

function TestAuth() {
  const { isAuthenticated, user } = useAuth()
  
  return (
    <div>
      {isAuthenticated ? (
        <p>Logged in as {user?.email}</p>
      ) : (
        <p>Not logged in</p>
      )}
    </div>
  )
}
```

### FastAPI

Create a test endpoint:

```python
from fastapi import FastAPI, Depends
from auth_kit_fastapi import AuthConfig, init_auth, auth_router
from auth_kit_fastapi.core.dependencies import get_current_user

app = FastAPI()

# Configure auth
config = AuthConfig(
    jwt_secret="test-secret",
    passkey_rp_id="localhost"
)

# Initialize auth
init_auth(app, config)
app.include_router(auth_router, prefix="/api/auth")

# Test endpoint
@app.get("/api/test")
async def test_auth(user = Depends(get_current_user)):
    return {"user": user.email}
```

## Next Steps

- Follow the [Quick Start Guide](./quickstart.md) to build your first app
- Learn about [Configuration Options](./configuration.md)
- Explore [Example Applications](../examples/)

## Troubleshooting

### Common Installation Issues

**Module not found errors**
- Ensure all packages are installed correctly
- Check your import paths
- Verify TypeScript configuration

**Database connection errors**
- Check your DATABASE_URL format
- Ensure database server is running
- Verify credentials and permissions

**CORS errors**
- Configure CORS in your backend
- Check API_URL in frontend configuration
- Ensure origins are allowed

For more help, see our [Troubleshooting Guide](./troubleshooting/common-issues.md).