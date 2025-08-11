# @auth-kit/cli

CLI tool for scaffolding Auth Kit projects with authentication pre-configured.

## Installation

```bash
npm install -g @auth-kit/cli
# or
npx @auth-kit/cli create my-app
```

## Usage

### Create a new project

```bash
auth-kit create my-app
```

This will prompt you to choose:
- Project type (Frontend, Backend, or Full-stack)
- Framework (React, Next.js, FastAPI)
- Database (PostgreSQL, MySQL, SQLite)
- Authentication features to include
- Styling solution
- Package manager

### Add Auth Kit to existing project

```bash
auth-kit add
```

This will:
- Detect your project type
- Install necessary dependencies
- Add authentication components
- Create configuration files

### Generate components

```bash
auth-kit generate component LoginForm
auth-kit generate page Dashboard
auth-kit generate hook useAuthGuard
```

Shortcuts:
```bash
auth-kit g component MyComponent
```

## Commands

### `create [project-name]`

Create a new Auth Kit project.

Options:
- `-t, --template <template>` - Use a specific template (react-spa, nextjs, fastapi, fullstack)
- `--typescript` - Use TypeScript (default)
- `--javascript` - Use JavaScript
- `--skip-install` - Skip dependency installation
- `--skip-git` - Skip git initialization

Examples:
```bash
# Interactive mode
auth-kit create my-app

# With template
auth-kit create my-app --template react-spa

# JavaScript project
auth-kit create my-app --javascript

# Skip installation
auth-kit create my-app --skip-install
```

### `add [feature]`

Add Auth Kit to an existing project.

Options:
- `-f, --framework <framework>` - Specify framework (react, nextjs, fastapi)

Examples:
```bash
# Add complete auth system
auth-kit add

# Add specific feature
auth-kit add passkeys
auth-kit add 2fa

# Specify framework
auth-kit add --framework nextjs
```

### `generate <type> [name]`

Generate auth-related components and files.

Aliases: `g`

Options:
- `-t, --typescript` - Generate TypeScript files
- `-j, --javascript` - Generate JavaScript files

Types:
- `component` - React components
- `page` - Page components
- `hook` - Custom hooks
- `api` - API endpoints

Examples:
```bash
# Generate login form component
auth-kit generate component LoginForm

# Generate dashboard page
auth-kit g page Dashboard

# Generate auth guard hook
auth-kit g hook useAuthGuard

# Generate API endpoint
auth-kit g api profile
```

## Templates

### React SPA
Single-page React application with:
- Vite for fast development
- React Router for navigation
- TypeScript support
- Auth Kit React integration

### Next.js
Next.js application with:
- App Router
- Server and Client Components
- API Routes
- TypeScript support

### FastAPI
Python backend with:
- FastAPI framework
- SQLAlchemy ORM
- Alembic migrations
- Auth Kit FastAPI integration

### Full-stack
Combined frontend and backend:
- React/Next.js frontend
- FastAPI backend
- Shared types
- Docker support

## Project Structure

Projects created with the CLI follow this structure:

```
my-app/
├── frontend/         # React/Next.js app (full-stack only)
├── backend/          # FastAPI app (full-stack only)
├── src/              # Source code
│   ├── components/   # UI components
│   ├── contexts/     # React contexts
│   ├── hooks/        # Custom hooks
│   ├── pages/        # Page components
│   └── utils/        # Utilities
├── .env              # Environment variables
├── .env.example      # Example environment file
└── README.md         # Project documentation
```

## Features Configuration

The CLI allows you to select which authentication features to include:

- **Email/Password Login** - Traditional authentication
- **Passkeys (WebAuthn)** - Passwordless authentication
- **Two-Factor Authentication** - TOTP-based 2FA
- **Email Verification** - Verify user emails
- **Password Reset** - Forgot password flow
- **Social Login** - OAuth providers (coming soon)

## Environment Variables

The CLI generates appropriate `.env` files based on your selections:

### Frontend
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_APP_URL=http://localhost:3000
NEXT_PUBLIC_ENABLE_PASSKEYS=true
NEXT_PUBLIC_ENABLE_2FA=true
```

### Backend
```env
DATABASE_URL=postgresql://user:pass@localhost:5432/dbname
JWT_SECRET=your-secret-key
PASSKEY_RP_ID=localhost
SMTP_HOST=smtp.gmail.com
```

## Contributing

See the main [Auth Kit repository](https://github.com/yourusername/auth-kit) for contribution guidelines.

## License

MIT