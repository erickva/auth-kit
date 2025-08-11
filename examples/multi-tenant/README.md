# Multi-Tenant SaaS Example

This example demonstrates how to build a multi-tenant SaaS application using Auth Kit with organization support, role-based access control, and tenant isolation.

## Features

- 🏢 **Multi-tenancy** - Organization-based tenant isolation
- 👥 **Team Management** - Invite users, manage roles
- 🔐 **Role-Based Access Control** - Admin, Member, Viewer roles
- 🎫 **Subscription Management** - Plans and billing integration ready
- 🔄 **Organization Switching** - Support multiple organizations per user
- 📊 **Admin Dashboard** - Organization analytics and management

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Next.js App   │────▶│  API Routes     │────▶│   PostgreSQL    │
│   (Frontend)    │     │  (Backend)      │     │   (Database)    │
└─────────────────┘     └─────────────────┘     └─────────────────┘
         │                       │                        │
         │                       │                        │
    ┌────▼────┐            ┌────▼────┐            ┌──────▼──────┐
    │ Auth Kit │            │ Auth Kit │            │   Organizations  │
    │  React   │            │ FastAPI  │            │   Users         │
    └──────────┘            └──────────┘            │   Memberships   │
                                                    └─────────────┘
```

## Data Model

### Organizations
- ID, name, slug, logo
- Subscription plan
- Settings and preferences

### Users
- Standard Auth Kit user model
- Can belong to multiple organizations

### Organization Memberships
- User-Organization relationship
- Role (admin, member, viewer)
- Invitation status

### Projects/Resources
- Belong to organizations
- Access controlled by membership

## Getting Started

### Prerequisites

- Node.js 18+
- Python 3.8+
- PostgreSQL
- Redis (optional, for caching)

### Installation

1. Install dependencies:

```bash
# Frontend
cd frontend
npm install

# Backend
cd ../backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

2. Set up environment variables:

```bash
# Frontend (.env.local)
cp .env.example .env.local

# Backend (.env)
cp .env.example .env
```

3. Run database migrations:

```bash
cd backend
alembic upgrade head
```

4. Seed sample data (optional):

```bash
python seed_data.py
```

5. Start the development servers:

```bash
# Terminal 1 - Backend
cd backend
uvicorn main:app --reload

# Terminal 2 - Frontend
cd frontend
npm run dev
```

## Usage

### Creating an Organization

1. Sign up or log in
2. Click "Create Organization"
3. Enter organization details
4. You're now the admin of the organization

### Inviting Team Members

1. Go to Settings → Team
2. Click "Invite Member"
3. Enter email and select role
4. User receives invitation email

### Switching Organizations

- Use the organization switcher in the header
- Your role and permissions update automatically

### Managing Access

Roles and permissions:

- **Admin**: Full access, can manage team and billing
- **Member**: Can create and edit resources
- **Viewer**: Read-only access

## API Endpoints

### Organization Management
- `GET /api/organizations` - List user's organizations
- `POST /api/organizations` - Create organization
- `GET /api/organizations/:id` - Get organization details
- `PUT /api/organizations/:id` - Update organization
- `DELETE /api/organizations/:id` - Delete organization

### Team Management
- `GET /api/organizations/:id/members` - List members
- `POST /api/organizations/:id/invitations` - Invite member
- `PUT /api/organizations/:id/members/:userId` - Update member role
- `DELETE /api/organizations/:id/members/:userId` - Remove member

### Current Context
- `GET /api/auth/context` - Get current user with active organization
- `POST /api/auth/switch-organization` - Switch active organization

## Implementation Details

### Frontend Organization Context

```tsx
// Provides current organization and switching functionality
<OrganizationProvider>
  <App />
</OrganizationProvider>
```

### Backend Tenant Isolation

```python
# All queries filtered by organization
@require_organization
async def get_projects(
    org: Organization = Depends(get_current_organization)
):
    return db.query(Project).filter(
        Project.organization_id == org.id
    ).all()
```

### Role-Based Access Control

```python
@require_role(["admin", "member"])
async def create_project(
    # Only admins and members can create
):
    pass
```

## Security Considerations

1. **Tenant Isolation**: All queries are scoped to organization
2. **Permission Checks**: Every endpoint validates user's role
3. **Invitation Tokens**: Secure, time-limited invitation links
4. **Audit Logging**: Track all organization actions
5. **Data Privacy**: Users can only see their organizations

## Customization

### Adding Custom Roles

1. Update the Role enum in `backend/models/organization.py`
2. Update permission checks in `backend/core/permissions.py`
3. Update UI role selectors in `frontend/components/RoleSelector.tsx`

### Adding Organization Settings

1. Add fields to Organization model
2. Create settings API endpoints
3. Build settings UI components

### Integrating Billing

1. Add subscription fields to Organization
2. Integrate payment provider (Stripe, etc.)
3. Add subscription management UI
4. Implement usage limits based on plan

## Production Deployment

### Environment Variables

Required for production:

- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis for caching and sessions
- `JWT_SECRET`: Strong secret for tokens
- `SMTP_*`: Email configuration
- `FRONTEND_URL`: For CORS and emails

### Database Considerations

- Use connection pooling
- Add indexes for organization_id columns
- Consider partitioning for large datasets
- Regular backups with organization data

### Scaling

- Horizontal scaling with load balancer
- Redis for distributed sessions
- CDN for static assets
- Database read replicas

## Troubleshooting

### Common Issues

1. **"Organization not found"**: Check organization slug in URL
2. **"Permission denied"**: Verify user's role in organization
3. **"Invalid invitation"**: Token may be expired
4. **Session issues**: Clear cookies and re-login

### Debug Mode

Enable debug logging:

```python
# Backend
ENVIRONMENT=development
LOG_LEVEL=DEBUG

# Frontend
NEXT_PUBLIC_DEBUG=true
```