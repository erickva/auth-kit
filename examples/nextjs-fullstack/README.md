# Auth Kit Next.js Full-Stack Example

This example demonstrates how to use Auth Kit with a Next.js frontend and FastAPI backend.

## Features Demonstrated

- 🔐 Email/password authentication
- 🔑 Passkey authentication
- 🔒 Two-factor authentication
- 📧 Email verification
- 🔄 Password reset flow
- 👤 User profile management
- 🎨 Themed UI components
- 🌍 Internationalization

## Project Structure

```
nextjs-fullstack/
├── frontend/          # Next.js 14 app with App Router
│   ├── app/          # App routes
│   ├── components/   # UI components
│   └── lib/          # Utilities
├── backend/          # FastAPI backend
│   ├── main.py      # Main application
│   └── models.py    # Custom user model
└── docker-compose.yml # Run everything together
```

## Getting Started

### Prerequisites

- Node.js 18+
- Python 3.8+
- PostgreSQL (or use Docker)

### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
cp .env.example .env
# Edit .env with your configuration

# Run migrations
alembic upgrade head

# Start the backend
uvicorn main:app --reload
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Set environment variables
cp .env.example .env.local
# Edit .env.local with your configuration

# Run development server
npm run dev
```

### Using Docker

```bash
# Start everything with Docker Compose
docker-compose up

# Frontend: http://localhost:3000
# Backend: http://localhost:8000
# Database: PostgreSQL on localhost:5432
```

## Key Implementation Details

### Frontend Configuration

```typescript
// app/providers.tsx
import { AuthKitProvider } from '@auth-kit/react';

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <AuthKitProvider
      config={{
        api: {
          baseUrl: process.env.NEXT_PUBLIC_API_URL!,
        },
        features: {
          passkeys: true,
          twoFactor: true,
          emailVerification: true,
        },
      }}
    >
      {children}
    </AuthKitProvider>
  );
}
```

### Backend Configuration

```python
# main.py
from auth_kit_fastapi import create_auth_app, AuthConfig
from models import User

config = AuthConfig(
    database_url=os.getenv("DATABASE_URL"),
    jwt_secret=os.getenv("JWT_SECRET"),
    features={
        "passkeys": True,
        "two_factor": True,
        "email_verification": True
    }
)

app = create_auth_app(config)
```

### Protected Routes

```typescript
// app/dashboard/page.tsx
import { ProtectedRoute } from '@auth-kit/react';

export default function Dashboard() {
  return (
    <ProtectedRoute redirectTo="/login">
      <DashboardContent />
    </ProtectedRoute>
  );
}
```

## Environment Variables

### Frontend (.env.local)

```env
NEXT_PUBLIC_API_URL=http://localhost:8000/api
NEXT_PUBLIC_APP_URL=http://localhost:3000
```

### Backend (.env)

```env
DATABASE_URL=postgresql://user:pass@localhost/authkit_example
JWT_SECRET=your-secret-key-here
AUTH_KIT_PASSKEY_RP_ID=localhost
AUTH_KIT_PASSKEY_ORIGIN=http://localhost:3000
AUTH_KIT_EMAIL_FROM=noreply@example.com
```

## Customization

### Custom User Fields

```python
# models.py
from auth_kit_fastapi import BaseUser
from sqlalchemy import Column, String

class User(BaseUser):
    __tablename__ = "users"
    
    company_name = Column(String, nullable=True)
    job_title = Column(String, nullable=True)
```

### Custom Theme

```css
/* app/globals.css */
:root {
  --auth-kit-primary: #0070f3;
  --auth-kit-primary-hover: #0051cc;
  /* ... other custom properties */
}
```

## Testing

```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm test

# E2E tests
npm run test:e2e
```

## Deployment

See the deployment guides in the main Auth Kit documentation for deploying to:
- Vercel (frontend)
- Railway/Render (backend)
- AWS/GCP/Azure
- Docker/Kubernetes

## License

MIT