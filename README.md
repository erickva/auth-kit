# Auth Kit 🔐

A comprehensive, production-ready authentication solution for modern web applications. Auth Kit provides modular packages for React and FastAPI with support for JWT authentication, passkeys (WebAuthn), two-factor authentication, and more.

## 🌟 Features

- **🔑 Multiple Authentication Methods**
  - Email/Password with secure hashing
  - Passkeys (WebAuthn) for passwordless login
  - Two-factor authentication (TOTP)
  - ~~OAuth2/Social login ready~~ (coming soon - see [SOCIALS.md](./SOCIALS.md))

- **🛡️ Security First**
  - JWT with refresh token rotation
  - Secure session management
  - Email verification
  - Password reset flow
  - Recovery codes for 2FA

- **📦 Modular Architecture**
  - Separate packages for different frameworks
  - Core package with shared utilities
  - Extensible and customizable
  - TypeScript and Python type safety

- **🚀 Production Ready**
  - Event-driven architecture
  - Comprehensive error handling
  - Built-in security best practices
  - Easy deployment

## 🚀 Quick Start

### React Application

```bash
npm install @auth-kit/core @auth-kit/react
```

```tsx
import { AuthProvider } from '@auth-kit/react'

function App() {
  return (
    <AuthProvider config={{
      apiUrl: 'http://localhost:8000/api',
      enableAutoRefresh: true
    }}>
      {/* Your app */}
    </AuthProvider>
  )
}
```

### FastAPI Backend

```bash
pip install auth-kit-fastapi
```

```python
from fastapi import FastAPI
from auth_kit_fastapi import AuthConfig, init_auth, auth_router

app = FastAPI()

auth_config = AuthConfig(
    jwt_secret="your-secret-key",
    passkey_rp_id="localhost",
    passkey_rp_name="My App"
)

init_auth(app, auth_config)
app.include_router(auth_router, prefix="/api")
```

## 📦 Packages

### @auth-kit/core
Core utilities and types shared across all Auth Kit packages.

### @auth-kit/react
Complete authentication solution for React applications with hooks and pre-built components.

### auth-kit-fastapi
FastAPI integration with models, endpoints, and middleware for authentication.

### @auth-kit/cli
Command-line tool for scaffolding new Auth Kit projects with authentication pre-configured.

```bash
# Install globally
npm install -g @auth-kit/cli

# Or use directly with npx
npx @auth-kit/cli create my-app
```

**Features:**
- Interactive project setup
- Multiple project templates (React SPA, Next.js, FastAPI, Full-stack)
- Automatic dependency installation
- Environment file generation
- TypeScript/JavaScript support

**Commands:**
- `auth-kit create <project-name>` - Create a new project
- `auth-kit add` - Add auth to existing project
- `auth-kit generate <component>` - Generate auth components

## 📖 Documentation

### Getting Started
- [Installation Guide](./docs/installation.md)
- [Quick Start Tutorial](./docs/quickstart.md)
- [Configuration Options](./docs/configuration.md)

### Guides
- [Implementing Passkeys](./docs/guides/passkeys.md)
- [Setting up 2FA](./docs/guides/two-factor.md)
- [Email Verification](./docs/guides/email-verification.md)
- [Custom User Models](./docs/guides/custom-users.md)

### API Reference
- [@auth-kit/react API](./packages/react/README.md)
- [auth-kit-fastapi API](./packages/fastapi/README.md)

### Examples
- [React SPA Example](./examples/react-spa/)
- [Multi-tenant SaaS Example](./examples/multi-tenant/)

## 🏗️ Architecture

```
auth-kit/
├── packages/
│   ├── core/           # Shared types and utilities
│   ├── react/          # React hooks and components
│   ├── fastapi/        # FastAPI integration
│   └── cli/            # CLI tool for scaffolding
├── examples/           # Example applications
│   ├── react-spa/      # Single-page React application
│   └── multi-tenant/   # Multi-tenant SaaS example
├── docs/               # Documentation
└── tests/              # Test suites
```

## 🔧 Development

### Prerequisites
- Node.js 18+
- Python 3.8+
- npm or yarn

### Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/auth-kit.git
cd auth-kit
```

2. Install dependencies:
```bash
npm install
```

3. Build all packages:
```bash
npm run build
```

4. Run tests:
```bash
npm test
```

### Development Workflow

This is a monorepo managed with Lerna. To work on a specific package:

```bash
# Work on React package
cd packages/react
npm run dev

# Work on FastAPI package
cd packages/fastapi
pip install -e .
```

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](./CONTRIBUTING.md) for details.

### Reporting Issues
- Use GitHub Issues for bug reports and feature requests
- Follow the issue templates
- Provide reproducible examples

### Pull Requests
- Fork the repository
- Create a feature branch
- Write tests for new features
- Ensure all tests pass
- Submit a PR with a clear description

## 📄 License

MIT License - see [LICENSE](./LICENSE) for details.

## 🙏 Acknowledgments

- Built with [FastAPI](https://fastapi.tiangolo.com/)
- React integration inspired by [Auth0](https://auth0.com/)
- Passkey implementation using [py_webauthn](https://github.com/duo-labs/py_webauthn)

## 🔗 Links

- [Documentation](https://auth-kit.dev)
- [GitHub Repository](https://github.com/yourusername/auth-kit)
- [NPM Package](https://www.npmjs.com/package/@auth-kit/react)
- [PyPI Package](https://pypi.org/project/auth-kit-fastapi/)

---

Made with ❤️ by the Auth Kit team