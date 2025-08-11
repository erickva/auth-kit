import { Command } from 'commander'
import inquirer from 'inquirer'
import chalk from 'chalk'
import fs from 'fs-extra'
import path from 'path'

export const generateCommand = new Command('generate')
  .alias('g')
  .description('Generate auth-related components and pages')
  .argument('[type]', 'What to generate (component, page, hook)')
  .argument('[name]', 'Name of the item to generate')
  .option('-t, --typescript', 'Generate TypeScript files')
  .option('-j, --javascript', 'Generate JavaScript files')
  .action(async (type: string | undefined, name: string | undefined, options: any) => {
    try {
      // Get configuration
      const config = await getGenerateConfig(type, name, options)
      
      // Generate the requested item
      switch (config.type) {
        case 'component':
          await generateComponent(config)
          break
        case 'page':
          await generatePage(config)
          break
        case 'hook':
          await generateHook(config)
          break
        case 'api':
          await generateApiEndpoint(config)
          break
        default:
          console.error(chalk.red(`Unknown type: ${config.type}`))
          process.exit(1)
      }
      
      console.log(chalk.green(`✨ Generated ${config.type}: ${config.name}`))
      
    } catch (error) {
      console.error(chalk.red('Error:'), error)
      process.exit(1)
    }
  })

async function getGenerateConfig(type: string | undefined, name: string | undefined, options: any) {
  const answers = await inquirer.prompt([
    {
      type: 'list',
      name: 'type',
      message: 'What do you want to generate?',
      choices: [
        { name: 'Component', value: 'component' },
        { name: 'Page', value: 'page' },
        { name: 'Hook', value: 'hook' },
        { name: 'API Endpoint', value: 'api' },
      ],
      when: !type,
    },
    {
      type: 'list',
      name: 'template',
      message: 'Which template?',
      choices: (answers: any) => {
        const t = type || answers.type
        switch (t) {
          case 'component':
            return [
              { name: 'Login Form', value: 'login-form' },
              { name: 'Signup Form', value: 'signup-form' },
              { name: 'Password Reset Form', value: 'password-reset' },
              { name: 'Profile Settings', value: 'profile-settings' },
              { name: 'Auth Guard', value: 'auth-guard' },
              { name: 'Passkey Manager', value: 'passkey-manager' },
              { name: '2FA Setup', value: '2fa-setup' },
              { name: 'Custom', value: 'custom' },
            ]
          case 'page':
            return [
              { name: 'Login Page', value: 'login' },
              { name: 'Signup Page', value: 'signup' },
              { name: 'Dashboard', value: 'dashboard' },
              { name: 'Profile Page', value: 'profile' },
              { name: 'Settings Page', value: 'settings' },
              { name: 'Password Reset Page', value: 'password-reset' },
              { name: 'Email Verification Page', value: 'verify-email' },
              { name: 'Custom', value: 'custom' },
            ]
          case 'hook':
            return [
              { name: 'useAuthGuard', value: 'auth-guard' },
              { name: 'useAuthRedirect', value: 'auth-redirect' },
              { name: 'usePermissions', value: 'permissions' },
              { name: 'useSessionTimeout', value: 'session-timeout' },
              { name: 'Custom', value: 'custom' },
            ]
          case 'api':
            return [
              { name: 'User Profile Endpoint', value: 'profile' },
              { name: 'Change Password Endpoint', value: 'change-password' },
              { name: 'Delete Account Endpoint', value: 'delete-account' },
              { name: 'Sessions Management', value: 'sessions' },
              { name: 'Custom', value: 'custom' },
            ]
          default:
            return []
        }
      },
    },
    {
      type: 'input',
      name: 'name',
      message: (answers: any) => {
        const t = type || answers.type
        return `${t.charAt(0).toUpperCase() + t.slice(1)} name:`
      },
      when: (answers: any) => !name && answers.template === 'custom',
      validate: (input: string) => {
        if (!input) return 'Name is required'
        if (!/^[A-Za-z][A-Za-z0-9]*$/.test(input)) {
          return 'Name must start with a letter and contain only letters and numbers'
        }
        return true
      },
    },
  ])
  
  // Detect TypeScript/JavaScript preference
  let useTypeScript = options.typescript || !options.javascript
  
  if (!options.typescript && !options.javascript) {
    // Try to auto-detect
    const hasTypeScript = await fs.pathExists(path.join(process.cwd(), 'tsconfig.json'))
    useTypeScript = hasTypeScript
  }
  
  return {
    type: type || answers.type,
    template: answers.template,
    name: name || answers.name || getNameFromTemplate(answers.template),
    typescript: useTypeScript,
  }
}

function getNameFromTemplate(template: string): string {
  const nameMap: Record<string, string> = {
    'login-form': 'LoginForm',
    'signup-form': 'SignupForm',
    'password-reset': 'PasswordResetForm',
    'profile-settings': 'ProfileSettings',
    'auth-guard': 'AuthGuard',
    'passkey-manager': 'PasskeyManager',
    '2fa-setup': 'TwoFactorSetup',
    'login': 'Login',
    'signup': 'Signup',
    'dashboard': 'Dashboard',
    'profile': 'Profile',
    'settings': 'Settings',
    'verify-email': 'VerifyEmail',
    'auth-redirect': 'useAuthRedirect',
    'permissions': 'usePermissions',
    'session-timeout': 'useSessionTimeout',
    'change-password': 'ChangePassword',
    'delete-account': 'DeleteAccount',
    'sessions': 'Sessions',
  }
  
  return nameMap[template] || template
}

async function generateComponent(config: any) {
  const ext = config.typescript ? 'tsx' : 'jsx'
  const componentDir = path.join(process.cwd(), 'src', 'components')
  await fs.ensureDir(componentDir)
  
  const componentPath = path.join(componentDir, `${config.name}.${ext}`)
  
  if (await fs.pathExists(componentPath)) {
    const { overwrite } = await inquirer.prompt([
      {
        type: 'confirm',
        name: 'overwrite',
        message: `${config.name}.${ext} already exists. Overwrite?`,
        default: false,
      },
    ])
    
    if (!overwrite) {
      console.log(chalk.yellow('Cancelled'))
      return
    }
  }
  
  const template = getComponentTemplate(config.template, config.typescript)
  const content = template.replace(/{{COMPONENT_NAME}}/g, config.name)
  
  await fs.writeFile(componentPath, content)
  console.log(chalk.green(`Created: ${path.relative(process.cwd(), componentPath)}`))
}

async function generatePage(config: any) {
  const ext = config.typescript ? 'tsx' : 'jsx'
  
  // Detect if using Next.js app directory or pages
  const hasAppDir = await fs.pathExists(path.join(process.cwd(), 'app'))
  const hasSrcApp = await fs.pathExists(path.join(process.cwd(), 'src', 'app'))
  const isNextApp = hasAppDir || hasSrcApp
  
  let pagePath: string
  
  if (isNextApp) {
    // Next.js app directory
    const appDir = hasSrcApp ? path.join('src', 'app') : 'app'
    const pageDir = path.join(process.cwd(), appDir, config.name.toLowerCase())
    await fs.ensureDir(pageDir)
    pagePath = path.join(pageDir, `page.${ext}`)
  } else {
    // Traditional pages directory or regular React
    const pagesDir = path.join(process.cwd(), 'src', 'pages')
    await fs.ensureDir(pagesDir)
    pagePath = path.join(pagesDir, `${config.name}.${ext}`)
  }
  
  if (await fs.pathExists(pagePath)) {
    const { overwrite } = await inquirer.prompt([
      {
        type: 'confirm',
        name: 'overwrite',
        message: `Page already exists. Overwrite?`,
        default: false,
      },
    ])
    
    if (!overwrite) {
      console.log(chalk.yellow('Cancelled'))
      return
    }
  }
  
  const template = getPageTemplate(config.template, config.typescript, isNextApp)
  const content = template.replace(/{{PAGE_NAME}}/g, config.name)
  
  await fs.writeFile(pagePath, content)
  console.log(chalk.green(`Created: ${path.relative(process.cwd(), pagePath)}`))
}

async function generateHook(config: any) {
  const ext = config.typescript ? 'ts' : 'js'
  const hooksDir = path.join(process.cwd(), 'src', 'hooks')
  await fs.ensureDir(hooksDir)
  
  const hookPath = path.join(hooksDir, `${config.name}.${ext}`)
  
  if (await fs.pathExists(hookPath)) {
    const { overwrite } = await inquirer.prompt([
      {
        type: 'confirm',
        name: 'overwrite',
        message: `${config.name}.${ext} already exists. Overwrite?`,
        default: false,
      },
    ])
    
    if (!overwrite) {
      console.log(chalk.yellow('Cancelled'))
      return
    }
  }
  
  const template = getHookTemplate(config.template, config.typescript)
  const content = template.replace(/{{HOOK_NAME}}/g, config.name)
  
  await fs.writeFile(hookPath, content)
  console.log(chalk.green(`Created: ${path.relative(process.cwd(), hookPath)}`))
}

async function generateApiEndpoint(config: any) {
  // For Python/FastAPI projects
  const apiDir = path.join(process.cwd(), 'app', 'api')
  await fs.ensureDir(apiDir)
  
  const endpointPath = path.join(apiDir, `${config.name.toLowerCase()}.py`)
  
  if (await fs.pathExists(endpointPath)) {
    const { overwrite } = await inquirer.prompt([
      {
        type: 'confirm',
        name: 'overwrite',
        message: `${config.name.toLowerCase()}.py already exists. Overwrite?`,
        default: false,
      },
    ])
    
    if (!overwrite) {
      console.log(chalk.yellow('Cancelled'))
      return
    }
  }
  
  const template = getApiTemplate(config.template)
  const content = template
    .replace(/{{ENDPOINT_NAME}}/g, config.name)
    .replace(/{{ENDPOINT_NAME_LOWER}}/g, config.name.toLowerCase())
  
  await fs.writeFile(endpointPath, content)
  console.log(chalk.green(`Created: ${path.relative(process.cwd(), endpointPath)}`))
}

// Template functions
function getComponentTemplate(template: string, typescript: boolean): string {
  const templates: Record<string, string> = {
    'login-form': typescript ? `import React, { useState } from 'react'
import { useAuth } from '@auth-kit/react'

interface {{COMPONENT_NAME}}Props {
  onSuccess?: () => void
  onError?: (error: Error) => void
}

export function {{COMPONENT_NAME}}({ onSuccess, onError }: {{COMPONENT_NAME}}Props) {
  const { login } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)

    try {
      await login({ email, password })
      onSuccess?.()
    } catch (error) {
      onError?.(error as Error)
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label htmlFor="email" className="block text-sm font-medium">
          Email
        </label>
        <input
          id="email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          className="mt-1 block w-full rounded-md border-gray-300"
          disabled={isLoading}
        />
      </div>
      <div>
        <label htmlFor="password" className="block text-sm font-medium">
          Password
        </label>
        <input
          id="password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          className="mt-1 block w-full rounded-md border-gray-300"
          disabled={isLoading}
        />
      </div>
      <button
        type="submit"
        disabled={isLoading}
        className="w-full rounded-md bg-blue-600 px-4 py-2 text-white hover:bg-blue-700 disabled:opacity-50"
      >
        {isLoading ? 'Signing in...' : 'Sign In'}
      </button>
    </form>
  )
}` : `import React, { useState } from 'react'
import { useAuth } from '@auth-kit/react'

export function {{COMPONENT_NAME}}({ onSuccess, onError }) {
  const { login } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setIsLoading(true)

    try {
      await login({ email, password })
      onSuccess?.()
    } catch (error) {
      onError?.(error)
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label htmlFor="email" className="block text-sm font-medium">
          Email
        </label>
        <input
          id="email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          className="mt-1 block w-full rounded-md border-gray-300"
          disabled={isLoading}
        />
      </div>
      <div>
        <label htmlFor="password" className="block text-sm font-medium">
          Password
        </label>
        <input
          id="password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          className="mt-1 block w-full rounded-md border-gray-300"
          disabled={isLoading}
        />
      </div>
      <button
        type="submit"
        disabled={isLoading}
        className="w-full rounded-md bg-blue-600 px-4 py-2 text-white hover:bg-blue-700 disabled:opacity-50"
      >
        {isLoading ? 'Signing in...' : 'Sign In'}
      </button>
    </form>
  )
}`,
    'custom': typescript ? `import React from 'react'

interface {{COMPONENT_NAME}}Props {
  // Add your props here
}

export function {{COMPONENT_NAME}}({}: {{COMPONENT_NAME}}Props) {
  return (
    <div>
      <h1>{{COMPONENT_NAME}}</h1>
      {/* Add your component logic here */}
    </div>
  )
}` : `import React from 'react'

export function {{COMPONENT_NAME}}(props) {
  return (
    <div>
      <h1>{{COMPONENT_NAME}}</h1>
      {/* Add your component logic here */}
    </div>
  )
}`,
  }
  
  return templates[template] || templates.custom
}

function getPageTemplate(template: string, typescript: boolean, isNextApp: boolean): string {
  const clientDirective = isNextApp ? `'use client'\n\n` : ''
  
  const templates: Record<string, string> = {
    'login': typescript ? `${clientDirective}import { useAuth } from '@auth-kit/react'
import { useRouter } from '${isNextApp ? 'next/navigation' : 'next/router'}'
import { LoginForm } from '../components/LoginForm'

export default function {{PAGE_NAME}}Page() {
  const { isAuthenticated } = useAuth()
  const router = useRouter()

  if (isAuthenticated) {
    router.push('/dashboard')
    return null
  }

  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="max-w-md w-full space-y-8">
        <h2 className="text-center text-3xl font-extrabold">
          Sign in to your account
        </h2>
        <LoginForm
          onSuccess={() => router.push('/dashboard')}
          onError={(error) => console.error(error)}
        />
      </div>
    </div>
  )
}` : `${clientDirective}import { useAuth } from '@auth-kit/react'
import { useRouter } from '${isNextApp ? 'next/navigation' : 'next/router'}'
import { LoginForm } from '../components/LoginForm'

export default function {{PAGE_NAME}}Page() {
  const { isAuthenticated } = useAuth()
  const router = useRouter()

  if (isAuthenticated) {
    router.push('/dashboard')
    return null
  }

  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="max-w-md w-full space-y-8">
        <h2 className="text-center text-3xl font-extrabold">
          Sign in to your account
        </h2>
        <LoginForm
          onSuccess={() => router.push('/dashboard')}
          onError={(error) => console.error(error)}
        />
      </div>
    </div>
  )
}`,
    'custom': typescript ? `${clientDirective}export default function {{PAGE_NAME}}Page() {
  return (
    <div>
      <h1>{{PAGE_NAME}}</h1>
      {/* Add your page content here */}
    </div>
  )
}` : `${clientDirective}export default function {{PAGE_NAME}}Page() {
  return (
    <div>
      <h1>{{PAGE_NAME}}</h1>
      {/* Add your page content here */}
    </div>
  )
}`,
  }
  
  return templates[template] || templates.custom
}

function getHookTemplate(template: string, typescript: boolean): string {
  const templates: Record<string, string> = {
    'auth-guard': typescript ? `import { useEffect } from 'react'
import { useRouter } from 'next/router'
import { useAuth } from '@auth-kit/react'

interface UseAuthGuardOptions {
  redirectTo?: string
  permissions?: string[]
}

export function {{HOOK_NAME}}(options: UseAuthGuardOptions = {}) {
  const { isAuthenticated, isLoading, user } = useAuth()
  const router = useRouter()
  const { redirectTo = '/login', permissions = [] } = options

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push(redirectTo)
    }

    if (permissions.length > 0 && user) {
      const hasPermission = permissions.some(permission => 
        user.permissions?.includes(permission)
      )
      
      if (!hasPermission) {
        router.push('/unauthorized')
      }
    }
  }, [isAuthenticated, isLoading, user, router, redirectTo, permissions])

  return { isAuthenticated, isLoading, user }
}` : `import { useEffect } from 'react'
import { useRouter } from 'next/router'
import { useAuth } from '@auth-kit/react'

export function {{HOOK_NAME}}(options = {}) {
  const { isAuthenticated, isLoading, user } = useAuth()
  const router = useRouter()
  const { redirectTo = '/login', permissions = [] } = options

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push(redirectTo)
    }

    if (permissions.length > 0 && user) {
      const hasPermission = permissions.some(permission => 
        user.permissions?.includes(permission)
      )
      
      if (!hasPermission) {
        router.push('/unauthorized')
      }
    }
  }, [isAuthenticated, isLoading, user, router, redirectTo, permissions])

  return { isAuthenticated, isLoading, user }
}`,
    'custom': typescript ? `import { useState, useEffect } from 'react'

export function {{HOOK_NAME}}() {
  const [state, setState] = useState()

  useEffect(() => {
    // Add your hook logic here
  }, [])

  return state
}` : `import { useState, useEffect } from 'react'

export function {{HOOK_NAME}}() {
  const [state, setState] = useState()

  useEffect(() => {
    // Add your hook logic here
  }, [])

  return state
}`,
  }
  
  return templates[template] || templates.custom
}

function getApiTemplate(template: string): string {
  const templates: Record<string, string> = {
    'profile': `from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.user import UserUpdate, UserResponse

router = APIRouter()

@router.get("/{{ENDPOINT_NAME_LOWER}}", response_model=UserResponse)
async def get_{{ENDPOINT_NAME_LOWER}}(
    current_user: User = Depends(get_current_user)
):
    """Get current user profile"""
    return current_user

@router.put("/{{ENDPOINT_NAME_LOWER}}", response_model=UserResponse)
async def update_{{ENDPOINT_NAME_LOWER}}(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update current user profile"""
    for field, value in user_update.dict(exclude_unset=True).items():
        setattr(current_user, field, value)
    
    db.commit()
    db.refresh(current_user)
    
    return current_user`,
    'custom': `from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db
from app.models.user import User

router = APIRouter()

@router.get("/{{ENDPOINT_NAME_LOWER}}")
async def {{ENDPOINT_NAME_LOWER}}_endpoint(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """{{ENDPOINT_NAME}} endpoint"""
    # Add your endpoint logic here
    return {"message": "{{ENDPOINT_NAME}} endpoint"}`,
  }
  
  return templates[template] || templates.custom
}