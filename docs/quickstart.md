# Quick Start Guide

Get up and running with Auth Kit in 10 minutes! This guide will walk you through creating a simple authenticated application.

## Using the CLI (Fastest Method)

The quickest way to get started is using the Auth Kit CLI:

```bash
# Create a new full-stack app with authentication
npx @auth-kit/cli create my-auth-app

# Follow the interactive prompts to:
# - Choose project type (Frontend, Backend, or Full-stack)
# - Select authentication features
# - Configure your database
# - Set up styling preferences

cd my-auth-app
npm run dev
```

Your authenticated application is now running! The CLI has set up everything for you.

## Manual Setup

If you prefer to set up Auth Kit manually, follow the steps below.

## Overview

We'll build a basic app with:
- User registration and login
- Protected routes/endpoints
- User profile management
- Logout functionality

## Backend Setup (FastAPI)

### 1. Create a new project

```bash
mkdir my-auth-app
cd my-auth-app
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install dependencies

```bash
pip install auth-kit-fastapi uvicorn[standard]
```

### 3. Create the backend

Create `backend.py`:

```python
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from auth_kit_fastapi import (
    AuthConfig, 
    init_auth, 
    auth_router, 
    Base,
    get_current_active_user,
    BaseUser
)

# Create FastAPI app
app = FastAPI(title="My Auth App")

# Database setup
DATABASE_URL = "sqlite:///./myapp.db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

# Create tables
Base.metadata.create_all(bind=engine)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure auth
auth_config = AuthConfig(
    jwt_secret="your-secret-key-change-this",
    passkey_rp_id="localhost",
    passkey_rp_name="My Auth App"
)

# Initialize auth
init_auth(app, auth_config, SessionLocal)

# Mount auth routes
app.include_router(auth_router, prefix="/api/auth")

# Protected endpoint example
@app.get("/api/protected")
async def protected_route(user: BaseUser = Depends(get_current_active_user)):
    return {
        "message": f"Hello {user.email}!",
        "user_id": str(user.id)
    }

# Run with: uvicorn backend:app --reload
```

### 4. Start the backend

```bash
uvicorn backend:app --reload
```

Your API is now running at http://localhost:8000

## Frontend Setup (React)

### 1. Create React app

```bash
npx create-react-app my-auth-frontend --template typescript
cd my-auth-frontend
```

### 2. Install Auth Kit

```bash
npm install @auth-kit/core @auth-kit/react axios
```

### 3. Set up the app

Replace `src/App.tsx`:

```tsx
import React from 'react';
import { AuthProvider, useAuth, LoginForm, RegisterForm } from '@auth-kit/react';
import { StorageType } from '@auth-kit/core';
import './App.css';

// Main App Component
function App() {
  return (
    <AuthProvider
      config={{
        apiUrl: 'http://localhost:8000',
        storageType: StorageType.LocalStorage,
      }}
    >
      <div className="App">
        <h1>My Auth App</h1>
        <AuthContent />
      </div>
    </AuthProvider>
  );
}

// Auth Content Component
function AuthContent() {
  const { isAuthenticated, user, logout } = useAuth();
  const [showLogin, setShowLogin] = React.useState(true);

  if (isAuthenticated) {
    return (
      <div>
        <h2>Welcome, {user?.email}!</h2>
        <button onClick={logout}>Logout</button>
        <ProtectedContent />
      </div>
    );
  }

  return (
    <div style={{ maxWidth: '400px', margin: '0 auto' }}>
      {showLogin ? (
        <>
          <h2>Login</h2>
          <LoginForm
            onSuccess={() => console.log('Logged in!')}
            onError={(error) => alert(error.message)}
          />
          <p>
            Don't have an account?{' '}
            <button onClick={() => setShowLogin(false)}>Register</button>
          </p>
        </>
      ) : (
        <>
          <h2>Register</h2>
          <RegisterForm
            onSuccess={() => setShowLogin(true)}
            onError={(error) => alert(error.message)}
          />
          <p>
            Already have an account?{' '}
            <button onClick={() => setShowLogin(true)}>Login</button>
          </p>
        </>
      )}
    </div>
  );
}

// Protected Content Component
function ProtectedContent() {
  const [data, setData] = React.useState<any>(null);
  const { getAuthHeaders } = useAuth();

  React.useEffect(() => {
    // Fetch protected data
    fetch('http://localhost:8000/api/protected', {
      headers: getAuthHeaders(),
    })
      .then((res) => res.json())
      .then(setData)
      .catch(console.error);
  }, []);

  return (
    <div>
      <h3>Protected Content</h3>
      {data && <pre>{JSON.stringify(data, null, 2)}</pre>}
    </div>
  );
}

export default App;
```

### 4. Add basic styles

Add to `src/App.css`:

```css
.App {
  text-align: center;
  padding: 40px;
  font-family: Arial, sans-serif;
}

button {
  background-color: #4CAF50;
  color: white;
  padding: 10px 20px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  margin: 10px;
}

button:hover {
  background-color: #45a049;
}

input {
  width: 100%;
  padding: 10px;
  margin: 8px 0;
  box-sizing: border-box;
  border: 1px solid #ccc;
  border-radius: 4px;
}
```

### 5. Start the frontend

```bash
npm start
```

Your app is now running at http://localhost:3000

## Test Your App

1. **Register a new user**
   - Enter email and password
   - Click "Register"

2. **Login**
   - Use your credentials
   - You'll see the welcome message

3. **View protected content**
   - The app fetches data from the protected endpoint
   - Only works when authenticated

4. **Logout**
   - Click the logout button
   - You'll return to the login screen

## Next Steps

### Add More Features

**Enable Passkeys:**
```tsx
<LoginForm 
  showPasskey={true}
  onSuccess={() => console.log('Logged in!')}
/>
```

**Add 2FA:**
```python
auth_config = AuthConfig(
    jwt_secret="your-secret-key",
    features={
        "two_factor": True
    }
)
```

**Email Verification:**
```python
auth_config = AuthConfig(
    jwt_secret="your-secret-key",
    features={
        "email_verification": True
    },
    smtp_host="smtp.gmail.com",
    smtp_username="your-email@gmail.com",
    smtp_password="your-app-password"
)
```

### Customize UI

Create custom forms:
```tsx
import { useAuth } from '@auth-kit/react';

function CustomLoginForm() {
  const { login } = useAuth();
  const [email, setEmail] = React.useState('');
  const [password, setPassword] = React.useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await login({ email, password });
    } catch (error) {
      console.error('Login failed:', error);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <input
        type="email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        placeholder="Email"
        required
      />
      <input
        type="password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        placeholder="Password"
        required
      />
      <button type="submit">Login</button>
    </form>
  );
}
```

### Add Protected Routes

For React Router:
```tsx
import { Navigate } from 'react-router-dom';
import { useAuth } from '@auth-kit/react';

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) return <div>Loading...</div>;
  if (!isAuthenticated) return <Navigate to="/login" />;

  return <>{children}</>;
}
```

## Complete Examples

For more complete examples, check out:
- [React SPA Example](../examples/react-spa/)
- [Next.js Example](../examples/nextjs/)
- [Multi-tenant SaaS Example](../examples/multi-tenant/)

## Getting Help

- Read the [full documentation](./README.md)
- Check [common issues](./troubleshooting/common-issues.md)
- Join our [Discord community](https://discord.gg/authkit)