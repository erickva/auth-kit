import { Command } from 'commander'
import inquirer from 'inquirer'
import chalk from 'chalk'
import ora from 'ora'
import fs from 'fs-extra'
import path from 'path'

export const addCommand = new Command('add')
  .description('Add Auth Kit to an existing project')
  .argument('[feature]', 'Feature to add (auth, passkeys, 2fa)')
  .option('-f, --framework <framework>', 'Framework (react, nextjs, fastapi)')
  .action(async (feature: string | undefined, options: any) => {
    try {
      // Check if we're in a valid project
      const projectRoot = process.cwd()
      const hasPackageJson = await fs.pathExists(path.join(projectRoot, 'package.json'))
      const hasRequirementsTxt = await fs.pathExists(path.join(projectRoot, 'requirements.txt'))
      const hasPyprojectToml = await fs.pathExists(path.join(projectRoot, 'pyproject.toml'))
      
      if (!hasPackageJson && !hasRequirementsTxt && !hasPyprojectToml) {
        console.error(chalk.red('Error: Not in a valid project directory'))
        console.log('Please run this command from the root of your project')
        process.exit(1)
      }
      
      // Determine project type
      const projectType = hasPackageJson ? 'javascript' : 'python'
      let framework = options.framework
      
      if (!framework && projectType === 'javascript') {
        // Try to auto-detect framework
        const packageJson = await fs.readJson(path.join(projectRoot, 'package.json'))
        if (packageJson.dependencies?.next) {
          framework = 'nextjs'
        } else if (packageJson.dependencies?.react) {
          framework = 'react'
        }
      }
      
      // Get configuration
      const config = await getAddConfig(feature, framework, projectType)
      
      console.log()
      const spinner = ora('Adding Auth Kit to your project...').start()
      
      try {
        // Add dependencies
        spinner.text = 'Adding dependencies...'
        await addDependencies(projectRoot, config)
        
        // Copy necessary files
        spinner.text = 'Setting up authentication...'
        await copyAuthFiles(projectRoot, config)
        
        // Update configuration files
        spinner.text = 'Updating configuration...'
        await updateConfig(projectRoot, config)
        
        // Generate environment variables
        spinner.text = 'Creating environment files...'
        await createEnvFiles(projectRoot, config)
        
        spinner.succeed('Auth Kit added successfully!')
        
        // Show next steps
        console.log()
        console.log(chalk.green('✨ Setup complete!'))
        console.log()
        console.log('Next steps:')
        console.log(chalk.cyan('  1. Update your .env file with your configuration'))
        console.log(chalk.cyan('  2. Run database migrations (if using a backend)'))
        console.log(chalk.cyan('  3. Wrap your app with AuthProvider (React/Next.js)'))
        console.log(chalk.cyan('  4. Start using auth hooks and components'))
        console.log()
        console.log('Documentation: https://github.com/yourusername/auth-kit')
        
      } catch (error) {
        spinner.fail('Failed to add Auth Kit')
        throw error
      }
      
    } catch (error) {
      console.error(chalk.red('Error:'), error)
      process.exit(1)
    }
  })

async function getAddConfig(feature: string | undefined, framework: string | undefined, projectType: string) {
  const answers = await inquirer.prompt([
    {
      type: 'list',
      name: 'feature',
      message: 'What do you want to add?',
      choices: [
        { name: 'Complete authentication system', value: 'auth' },
        { name: 'Passkeys (WebAuthn) only', value: 'passkeys' },
        { name: 'Two-factor authentication only', value: '2fa' },
        { name: 'Email verification only', value: 'email' },
      ],
      when: !feature,
    },
    {
      type: 'list',
      name: 'framework',
      message: 'Which framework are you using?',
      choices: projectType === 'javascript' 
        ? [
            { name: 'React', value: 'react' },
            { name: 'Next.js', value: 'nextjs' },
          ]
        : [
            { name: 'FastAPI', value: 'fastapi' },
            { name: 'Django', value: 'django' },
            { name: 'Flask', value: 'flask' },
          ],
      when: !framework,
    },
    {
      type: 'checkbox',
      name: 'features',
      message: 'Which features do you want to include?',
      choices: [
        { name: 'Email/Password login', value: 'password', checked: true },
        { name: 'Passkeys (WebAuthn)', value: 'passkeys', checked: true },
        { name: 'Two-factor authentication', value: '2fa', checked: true },
        { name: 'Email verification', value: 'emailVerification', checked: true },
        { name: 'Password reset', value: 'passwordReset', checked: true },
      ],
      when: (answers: any) => (answers.feature || feature) === 'auth',
    },
    {
      type: 'confirm',
      name: 'typescript',
      message: 'Are you using TypeScript?',
      default: true,
      when: projectType === 'javascript',
    },
  ])
  
  return {
    feature: feature || answers.feature,
    framework: framework || answers.framework,
    features: answers.features || [feature || answers.feature],
    projectType,
    typescript: answers.typescript !== false,
  }
}

async function addDependencies(projectRoot: string, config: any) {
  if (config.projectType === 'javascript') {
    const packageJson = await fs.readJson(path.join(projectRoot, 'package.json'))
    
    // Add Auth Kit dependencies
    packageJson.dependencies = {
      ...packageJson.dependencies,
      '@auth-kit/core': '^1.0.0',
      '@auth-kit/react': '^1.0.0',
    }
    
    // Add peer dependencies if needed
    if (config.features.includes('passkeys')) {
      packageJson.dependencies['@simplewebauthn/browser'] = '^9.0.0'
    }
    
    await fs.writeJson(path.join(projectRoot, 'package.json'), packageJson, { spaces: 2 })
    
  } else {
    // Python project
    let requirements = ''
    
    if (await fs.pathExists(path.join(projectRoot, 'requirements.txt'))) {
      requirements = await fs.readFile(path.join(projectRoot, 'requirements.txt'), 'utf-8')
    }
    
    // Add Auth Kit dependencies
    const newDeps = [
      'auth-kit-fastapi>=1.0.0',
      'python-jose[cryptography]>=3.3.0',
      'passlib[bcrypt]>=1.7.4',
      'python-multipart>=0.0.6',
    ]
    
    if (config.features.includes('passkeys')) {
      newDeps.push('webauthn>=1.11.0')
    }
    
    if (config.features.includes('2fa')) {
      newDeps.push('pyotp>=2.9.0')
      newDeps.push('qrcode[pil]>=7.4.0')
    }
    
    // Add dependencies that aren't already present
    for (const dep of newDeps) {
      const depName = dep.split('>=')[0].split('[')[0]
      if (!requirements.includes(depName)) {
        requirements += `\n${dep}`
      }
    }
    
    await fs.writeFile(path.join(projectRoot, 'requirements.txt'), requirements.trim() + '\n')
  }
}

async function copyAuthFiles(projectRoot: string, config: any) {
  const templateDir = path.join(__dirname, '../../templates/add', config.framework)
  
  if (await fs.pathExists(templateDir)) {
    // Copy auth-related files
    const filesToCopy = await getFilesToCopy(config)
    
    for (const file of filesToCopy) {
      const src = path.join(templateDir, file.src)
      const dest = path.join(projectRoot, file.dest || file.src)
      
      if (await fs.pathExists(src)) {
        await fs.ensureDir(path.dirname(dest))
        await fs.copy(src, dest, { overwrite: false })
      }
    }
  }
}

async function getFilesToCopy(config: any) {
  const files = []
  
  if (config.framework === 'react' || config.framework === 'nextjs') {
    // Core files
    files.push(
      { src: 'src/contexts/AuthContext.tsx', dest: 'src/contexts/AuthContext.tsx' },
      { src: 'src/hooks/useAuth.ts', dest: 'src/hooks/useAuth.ts' },
      { src: 'src/components/LoginForm.tsx', dest: 'src/components/LoginForm.tsx' },
      { src: 'src/components/ProtectedRoute.tsx', dest: 'src/components/ProtectedRoute.tsx' },
    )
    
    // Feature-specific files
    if (config.features.includes('passkeys')) {
      files.push(
        { src: 'src/hooks/usePasskey.ts', dest: 'src/hooks/usePasskey.ts' },
        { src: 'src/components/PasskeyButton.tsx', dest: 'src/components/PasskeyButton.tsx' },
      )
    }
    
    if (config.features.includes('2fa')) {
      files.push(
        { src: 'src/hooks/use2FA.ts', dest: 'src/hooks/use2FA.ts' },
        { src: 'src/components/TwoFactorSetup.tsx', dest: 'src/components/TwoFactorSetup.tsx' },
      )
    }
    
    // Convert to .js/.jsx if not using TypeScript
    if (!config.typescript) {
      files.forEach(file => {
        file.src = file.src.replace(/\.tsx?$/, file.src.endsWith('.tsx') ? '.jsx' : '.js')
        file.dest = file.dest.replace(/\.tsx?$/, file.dest.endsWith('.tsx') ? '.jsx' : '.js')
      })
    }
  } else if (config.framework === 'fastapi') {
    // FastAPI files
    files.push(
      { src: 'api/auth.py', dest: 'app/api/auth.py' },
      { src: 'models/user.py', dest: 'app/models/user.py' },
      { src: 'core/security.py', dest: 'app/core/security.py' },
      { src: 'core/config.py', dest: 'app/core/config.py' },
    )
    
    if (config.features.includes('passkeys')) {
      files.push({ src: 'api/passkeys.py', dest: 'app/api/passkeys.py' })
    }
    
    if (config.features.includes('2fa')) {
      files.push({ src: 'api/two_factor.py', dest: 'app/api/two_factor.py' })
    }
  }
  
  return files
}

async function updateConfig(projectRoot: string, config: any) {
  if (config.framework === 'nextjs') {
    // Update next.config.js if it exists
    const nextConfigPath = path.join(projectRoot, 'next.config.js')
    if (await fs.pathExists(nextConfigPath)) {
      // Add any necessary configuration
    }
  } else if (config.framework === 'fastapi') {
    // Update main.py to include auth routes
    const mainPyPath = path.join(projectRoot, 'main.py')
    if (await fs.pathExists(mainPyPath)) {
      let content = await fs.readFile(mainPyPath, 'utf-8')
      
      // Add imports if not present
      if (!content.includes('from app.api import auth')) {
        const importLine = 'from app.api import auth'
        const fastApiImportIndex = content.indexOf('from fastapi import')
        if (fastApiImportIndex !== -1) {
          const nextLineIndex = content.indexOf('\n', fastApiImportIndex) + 1
          content = content.slice(0, nextLineIndex) + importLine + '\n' + content.slice(nextLineIndex)
        }
      }
      
      // Add router if not present
      if (!content.includes('app.include_router(auth.router')) {
        const appCreateIndex = content.indexOf('app = FastAPI(')
        if (appCreateIndex !== -1) {
          const insertIndex = content.indexOf('\n', content.indexOf(')', appCreateIndex)) + 1
          content = content.slice(0, insertIndex) + 
            '\n# Include authentication routes\n' +
            'app.include_router(auth.router, prefix="/api/auth", tags=["auth"])\n' +
            content.slice(insertIndex)
        }
      }
      
      await fs.writeFile(mainPyPath, content)
    }
  }
}

async function createEnvFiles(projectRoot: string, config: any) {
  const envPath = path.join(projectRoot, '.env')
  const envExamplePath = path.join(projectRoot, '.env.example')
  
  // Check if .env already exists
  if (await fs.pathExists(envPath)) {
    console.log(chalk.yellow('\n.env file already exists. Please add the following variables:'))
    
    if (config.projectType === 'javascript') {
      console.log(chalk.gray('NEXT_PUBLIC_API_URL=http://localhost:8000'))
      if (config.features.includes('passkeys')) {
        console.log(chalk.gray('NEXT_PUBLIC_ENABLE_PASSKEYS=true'))
      }
    } else {
      console.log(chalk.gray('JWT_SECRET=your-secret-key'))
      console.log(chalk.gray('DATABASE_URL=postgresql://user:pass@localhost/db'))
    }
  } else {
    // Create new .env file
    let envContent = ''
    
    if (config.projectType === 'javascript') {
      envContent = `# API Configuration
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_APP_URL=http://localhost:3000

# Feature Flags
${config.features.includes('passkeys') ? 'NEXT_PUBLIC_ENABLE_PASSKEYS=true\n' : ''}${config.features.includes('2fa') ? 'NEXT_PUBLIC_ENABLE_2FA=true\n' : ''}`
    } else {
      envContent = `# Database
DATABASE_URL=postgresql://user:password@localhost:5432/myapp

# Security
JWT_SECRET=your-super-secret-key-change-this
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=30

# Application
APP_NAME=My App
CORS_ORIGINS=http://localhost:3000
${config.features.includes('passkeys') ? '\n# Passkeys\nPASSKEY_RP_ID=localhost\nPASSKEY_RP_NAME=My App\n' : ''}`
    }
    
    await fs.writeFile(envPath, envContent)
    await fs.writeFile(envExamplePath, envContent.replace(/=.*/g, '='))
  }
}