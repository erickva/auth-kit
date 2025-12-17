import fs from 'fs-extra'
import path from 'path'
import crypto from 'crypto'
import { ProjectConfig } from '../types'

export async function generateEnvFile(config: ProjectConfig, projectPath: string) {
  const envVars: Record<string, string> = {}
  
  // Generate secure random secrets
  const jwtSecret = crypto.randomBytes(32).toString('hex')
  const encryptionKey = crypto.randomBytes(32).toString('base64')
  
  // Common environment variables
  envVars['NODE_ENV'] = 'development'
  envVars['JWT_SECRET'] = jwtSecret
  envVars['ENCRYPTION_KEY'] = encryptionKey
  
  // Frontend environment variables
  if (config.projectType === 'frontend' || config.projectType === 'fullstack') {
    const frontendEnv: Record<string, string> = {
      'NEXT_PUBLIC_API_URL': 'http://localhost:8000',
      'NEXT_PUBLIC_APP_URL': 'http://localhost:3000',
      'NEXT_PUBLIC_APP_NAME': config.projectName,
    }
    
    // Add feature flags
    if (config.features.includes('passkeys')) {
      frontendEnv['NEXT_PUBLIC_ENABLE_PASSKEYS'] = 'true'
    }
    if (config.features.includes('twoFactor')) {
      frontendEnv['NEXT_PUBLIC_ENABLE_2FA'] = 'true'
    }
    if (config.features.includes('socialLogin')) {
      frontendEnv['NEXT_PUBLIC_ENABLE_SOCIAL_LOGIN'] = 'true'
    }
    
    // Write frontend .env.local
    const frontendEnvPath = config.projectType === 'fullstack' 
      ? path.join(projectPath, 'frontend', '.env.local')
      : path.join(projectPath, '.env.local')
    
    await writeEnvFile(frontendEnvPath, frontendEnv)
  }
  
  // Backend environment variables
  if (config.projectType === 'backend' || config.projectType === 'fullstack') {
    const backendEnv: Record<string, string> = {
      // Database
      'DATABASE_URL': getDatabaseUrl(config),
      
      // JWT
      'JWT_SECRET': jwtSecret,
      'JWT_ALGORITHM': 'HS256',
      'ACCESS_TOKEN_EXPIRE_MINUTES': '30',
      'REFRESH_TOKEN_EXPIRE_DAYS': '30',
      
      // Security
      'BCRYPT_ROUNDS': '12',
      'ENCRYPTION_KEY': encryptionKey,
      
      // Application
      'APP_NAME': config.projectName,
      'APP_URL': 'http://localhost:3000',
      'API_URL': 'http://localhost:8000',
      
      // CORS
      'CORS_ORIGINS': 'http://localhost:3000,http://localhost:3001',
      'CORS_ALLOW_CREDENTIALS': 'true',
    }
    
    // Passkey configuration
    if (config.features.includes('passkeys')) {
      backendEnv['PASSKEY_RP_ID'] = 'localhost'
      backendEnv['PASSKEY_RP_NAME'] = config.projectName
      backendEnv['PASSKEY_ORIGIN'] = 'http://localhost:3000'
    }
    
    // Email configuration (with placeholders)
    if (config.features.includes('emailVerification') || config.features.includes('passwordReset')) {
      backendEnv['SMTP_HOST'] = 'smtp.gmail.com'
      backendEnv['SMTP_PORT'] = '587'
      backendEnv['SMTP_USERNAME'] = 'your-email@gmail.com'
      backendEnv['SMTP_PASSWORD'] = 'your-app-password'
      backendEnv['SMTP_USE_TLS'] = 'true'
      backendEnv['EMAIL_FROM'] = `noreply@${config.projectName}.com`
    }

    // Social login configuration
    if (config.features.includes('socialLogin')) {
      // OAuth token encryption key (32 bytes base64)
      const oauthEncryptionKey = crypto.randomBytes(32).toString('base64')
      backendEnv['AUTH_KIT_OAUTH_TOKEN_ENCRYPTION_KEY'] = oauthEncryptionKey

      // Google OAuth (placeholders)
      backendEnv['AUTH_KIT_OAUTH_GOOGLE_CLIENT_ID'] = 'your-google-client-id'
      backendEnv['AUTH_KIT_OAUTH_GOOGLE_CLIENT_SECRET'] = 'your-google-client-secret'

      // GitHub OAuth (placeholders)
      backendEnv['AUTH_KIT_OAUTH_GITHUB_CLIENT_ID'] = 'your-github-client-id'
      backendEnv['AUTH_KIT_OAUTH_GITHUB_CLIENT_SECRET'] = 'your-github-client-secret'

      // Apple OAuth (placeholders)
      backendEnv['AUTH_KIT_OAUTH_APPLE_CLIENT_ID'] = 'your-apple-service-id'
      backendEnv['AUTH_KIT_OAUTH_APPLE_TEAM_ID'] = 'your-apple-team-id'
      backendEnv['AUTH_KIT_OAUTH_APPLE_KEY_ID'] = 'your-apple-key-id'
      backendEnv['AUTH_KIT_OAUTH_APPLE_PRIVATE_KEY'] = '-----BEGIN PRIVATE KEY-----\\nYour Apple private key here\\n-----END PRIVATE KEY-----'

      // Update features to include social_login with default providers
      backendEnv['AUTH_KIT_FEATURES'] = '{"passkeys": true, "two_factor": true, "email_verification": true, "social_login": ["google", "github", "apple"]}'
    }

    // Write backend .env
    const backendEnvPath = config.projectType === 'fullstack'
      ? path.join(projectPath, 'backend', '.env')
      : path.join(projectPath, '.env')
    
    await writeEnvFile(backendEnvPath, backendEnv)
  }
  
  // Create .env.example files
  await createEnvExamples(config, projectPath)
}

async function writeEnvFile(filePath: string, envVars: Record<string, string>) {
  const envContent = Object.entries(envVars)
    .map(([key, value]) => `${key}=${value}`)
    .join('\n')
  
  await fs.ensureDir(path.dirname(filePath))
  await fs.writeFile(filePath, envContent + '\n')
}

async function createEnvExamples(config: ProjectConfig, projectPath: string) {
  // Create .env.example with placeholder values
  const exampleVars: Record<string, string> = {}
  
  if (config.projectType === 'frontend' || config.projectType === 'fullstack') {
    const frontendExample: Record<string, string> = {
      'NEXT_PUBLIC_API_URL': 'http://localhost:8000',
      'NEXT_PUBLIC_APP_URL': 'http://localhost:3000',
      'NEXT_PUBLIC_APP_NAME': 'Your App Name',
    }
    
    if (config.features.includes('passkeys')) {
      frontendExample['NEXT_PUBLIC_ENABLE_PASSKEYS'] = 'true'
    }
    if (config.features.includes('twoFactor')) {
      frontendExample['NEXT_PUBLIC_ENABLE_2FA'] = 'true'
    }
    if (config.features.includes('socialLogin')) {
      frontendExample['NEXT_PUBLIC_ENABLE_SOCIAL_LOGIN'] = 'true'
    }

    const frontendExamplePath = config.projectType === 'fullstack'
      ? path.join(projectPath, 'frontend', '.env.example')
      : path.join(projectPath, '.env.example')
    
    await writeEnvFile(frontendExamplePath, frontendExample)
  }
  
  if (config.projectType === 'backend' || config.projectType === 'fullstack') {
    const backendExample: Record<string, string> = {
      'DATABASE_URL': 'postgresql://user:password@localhost:5432/dbname',
      'JWT_SECRET': 'your-super-secret-jwt-key-change-this',
      'JWT_ALGORITHM': 'HS256',
      'ACCESS_TOKEN_EXPIRE_MINUTES': '30',
      'REFRESH_TOKEN_EXPIRE_DAYS': '30',
      'BCRYPT_ROUNDS': '12',
      'ENCRYPTION_KEY': 'your-encryption-key-base64',
      'APP_NAME': 'Your App Name',
      'APP_URL': 'http://localhost:3000',
      'API_URL': 'http://localhost:8000',
      'CORS_ORIGINS': 'http://localhost:3000',
      'CORS_ALLOW_CREDENTIALS': 'true',
    }
    
    if (config.features.includes('passkeys')) {
      backendExample['PASSKEY_RP_ID'] = 'yourdomain.com'
      backendExample['PASSKEY_RP_NAME'] = 'Your App Name'
      backendExample['PASSKEY_ORIGIN'] = 'https://yourdomain.com'
    }
    
    if (config.features.includes('emailVerification') || config.features.includes('passwordReset')) {
      backendExample['SMTP_HOST'] = 'smtp.example.com'
      backendExample['SMTP_PORT'] = '587'
      backendExample['SMTP_USERNAME'] = 'your-smtp-username'
      backendExample['SMTP_PASSWORD'] = 'your-smtp-password'
      backendExample['SMTP_USE_TLS'] = 'true'
      backendExample['EMAIL_FROM'] = 'noreply@yourdomain.com'
    }

    if (config.features.includes('socialLogin')) {
      backendExample['AUTH_KIT_OAUTH_TOKEN_ENCRYPTION_KEY'] = 'your-32-byte-base64-encryption-key'
      backendExample['AUTH_KIT_OAUTH_GOOGLE_CLIENT_ID'] = 'your-google-client-id'
      backendExample['AUTH_KIT_OAUTH_GOOGLE_CLIENT_SECRET'] = 'your-google-client-secret'
      backendExample['AUTH_KIT_OAUTH_GITHUB_CLIENT_ID'] = 'your-github-client-id'
      backendExample['AUTH_KIT_OAUTH_GITHUB_CLIENT_SECRET'] = 'your-github-client-secret'
      backendExample['AUTH_KIT_OAUTH_APPLE_CLIENT_ID'] = 'your-apple-service-id'
      backendExample['AUTH_KIT_OAUTH_APPLE_TEAM_ID'] = 'your-apple-team-id'
      backendExample['AUTH_KIT_OAUTH_APPLE_KEY_ID'] = 'your-apple-key-id'
      backendExample['AUTH_KIT_OAUTH_APPLE_PRIVATE_KEY'] = '-----BEGIN PRIVATE KEY-----\\n...\\n-----END PRIVATE KEY-----'
      backendExample['AUTH_KIT_FEATURES'] = '{"passkeys": true, "two_factor": true, "email_verification": true, "social_login": ["google", "github", "apple"]}'
    }

    const backendExamplePath = config.projectType === 'fullstack'
      ? path.join(projectPath, 'backend', '.env.example')
      : path.join(projectPath, '.env.example')
    
    await writeEnvFile(backendExamplePath, backendExample)
  }
}

function getDatabaseUrl(config: ProjectConfig): string {
  const dbName = config.projectName.toLowerCase().replace(/[^a-z0-9]/g, '_')
  
  switch (config.database) {
    case 'postgresql':
      return `postgresql://postgres:postgres@localhost:5432/${dbName}`
    case 'mysql':
      return `mysql://root:password@localhost:3306/${dbName}`
    case 'sqlite':
      return 'sqlite:///./app.db'
    default:
      return `postgresql://postgres:postgres@localhost:5432/${dbName}`
  }
}