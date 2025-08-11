import fs from 'fs-extra'
import path from 'path'
import { ProjectConfig } from '../types'

export async function copyTemplate(config: ProjectConfig, projectPath: string) {
  const templateDir = path.join(__dirname, '../../templates')
  
  // Determine which templates to copy based on project type
  const templatesToCopy: string[] = []
  
  if (config.projectType === 'frontend' || config.projectType === 'fullstack') {
    templatesToCopy.push(config.framework === 'react' ? 'react-spa' : 'nextjs')
  }
  
  if (config.projectType === 'backend' || config.projectType === 'fullstack') {
    templatesToCopy.push('fastapi')
  }
  
  // Copy base template files
  const baseTemplate = path.join(templateDir, 'base')
  if (await fs.pathExists(baseTemplate)) {
    await fs.copy(baseTemplate, projectPath)
  }
  
  // Copy specific templates
  for (const template of templatesToCopy) {
    const templatePath = path.join(templateDir, template)
    if (await fs.pathExists(templatePath)) {
      if (config.projectType === 'fullstack') {
        // For fullstack, organize in subdirectories
        const targetDir = template === 'fastapi' ? 'backend' : 'frontend'
        await fs.copy(templatePath, path.join(projectPath, targetDir))
      } else {
        await fs.copy(templatePath, projectPath)
      }
    }
  }
  
  // Process template files (replace placeholders)
  await processTemplateFiles(projectPath, config)
  
  // Remove features that weren't selected
  await removeUnusedFeatures(projectPath, config)
  
  // Apply styling solution
  await applyStyling(projectPath, config)
  
  // Convert to JavaScript if needed
  if (config.language === 'javascript') {
    await convertToJavaScript(projectPath)
  }
}

async function processTemplateFiles(projectPath: string, config: ProjectConfig) {
  const filesToProcess = await findFilesToProcess(projectPath)
  
  for (const file of filesToProcess) {
    let content = await fs.readFile(file, 'utf-8')
    
    // Replace placeholders
    content = content
      .replace(/{{PROJECT_NAME}}/g, config.projectName)
      .replace(/{{PROJECT_NAME_SNAKE}}/g, toSnakeCase(config.projectName))
      .replace(/{{PROJECT_NAME_TITLE}}/g, toTitleCase(config.projectName))
      .replace(/{{DATABASE_TYPE}}/g, config.database)
      .replace(/{{DATABASE_URL}}/g, getDatabaseUrl(config))
      .replace(/{{YEAR}}/g, new Date().getFullYear().toString())
    
    await fs.writeFile(file, content)
  }
}

async function findFilesToProcess(dir: string): Promise<string[]> {
  const files: string[] = []
  const entries = await fs.readdir(dir, { withFileTypes: true })
  
  for (const entry of entries) {
    const fullPath = path.join(dir, entry.name)
    
    if (entry.isDirectory() && !entry.name.startsWith('.') && entry.name !== 'node_modules') {
      files.push(...await findFilesToProcess(fullPath))
    } else if (entry.isFile()) {
      const ext = path.extname(entry.name)
      if (['.ts', '.tsx', '.js', '.jsx', '.json', '.md', '.env', '.py', '.yml', '.yaml'].includes(ext)) {
        files.push(fullPath)
      }
    }
  }
  
  return files
}

async function removeUnusedFeatures(projectPath: string, config: ProjectConfig) {
  const features = config.features
  
  // Remove passkey-related code if not selected
  if (!features.includes('passkeys')) {
    await removeFeatureCode(projectPath, 'passkeys')
  }
  
  // Remove 2FA-related code if not selected
  if (!features.includes('twoFactor')) {
    await removeFeatureCode(projectPath, 'two-factor')
  }
  
  // Remove email verification if not selected
  if (!features.includes('emailVerification')) {
    await removeFeatureCode(projectPath, 'email-verification')
  }
}

async function removeFeatureCode(projectPath: string, feature: string) {
  // This is a simplified version - in a real implementation,
  // you'd want to parse the AST and remove specific code blocks
  // For now, we'll just remove specific files
  
  const featureFiles: Record<string, string[]> = {
    'passkeys': [
      'src/components/PasskeyButton.tsx',
      'src/components/PasskeyButton.jsx',
      'src/hooks/usePasskey.ts',
      'src/hooks/usePasskey.js',
      'api/passkeys.py',
    ],
    'two-factor': [
      'src/components/TwoFactorSetup.tsx',
      'src/components/TwoFactorSetup.jsx',
      'src/hooks/use2FA.ts',
      'src/hooks/use2FA.js',
      'api/two_factor.py',
    ],
    'email-verification': [
      'src/components/EmailVerification.tsx',
      'src/components/EmailVerification.jsx',
      'src/pages/verify-email.tsx',
      'src/pages/verify-email.jsx',
    ],
  }
  
  const filesToRemove = featureFiles[feature] || []
  
  for (const file of filesToRemove) {
    const filePath = path.join(projectPath, file)
    if (await fs.pathExists(filePath)) {
      await fs.remove(filePath)
    }
  }
}

async function applyStyling(projectPath: string, config: ProjectConfig) {
  if (config.projectType === 'backend') return
  
  const stylingDir = path.join(__dirname, '../../templates/styling', config.styling)
  if (await fs.pathExists(stylingDir)) {
    await fs.copy(stylingDir, projectPath, { overwrite: true })
  }
  
  // Update package.json with styling dependencies
  const packageJsonPath = path.join(
    projectPath,
    config.projectType === 'fullstack' ? 'frontend/package.json' : 'package.json'
  )
  
  if (await fs.pathExists(packageJsonPath)) {
    const packageJson = await fs.readJson(packageJsonPath)
    
    switch (config.styling) {
      case 'tailwind':
        packageJson.devDependencies = {
          ...packageJson.devDependencies,
          'tailwindcss': '^3.4.1',
          'autoprefixer': '^10.4.17',
          'postcss': '^8.4.35',
        }
        break
      case 'styled-components':
        packageJson.dependencies = {
          ...packageJson.dependencies,
          'styled-components': '^6.1.8',
        }
        packageJson.devDependencies = {
          ...packageJson.devDependencies,
          '@types/styled-components': '^5.1.34',
        }
        break
    }
    
    await fs.writeJson(packageJsonPath, packageJson, { spaces: 2 })
  }
}

async function convertToJavaScript(projectPath: string) {
  // This is a simplified version - in production, you'd use a proper TypeScript compiler
  // For now, we'll just rename files and remove type annotations
  
  const files = await findTypeScriptFiles(projectPath)
  
  for (const file of files) {
    const jsFile = file.replace(/\.tsx?$/, file.endsWith('.tsx') ? '.jsx' : '.js')
    
    // For templates, we'll have both TS and JS versions
    // So we can just remove the TS files
    if (await fs.pathExists(jsFile)) {
      await fs.remove(file)
    } else {
      // In a real implementation, strip types here
      await fs.rename(file, jsFile)
    }
  }
  
  // Remove TypeScript config files
  const tsConfigFiles = ['tsconfig.json', 'tsconfig.node.json']
  for (const configFile of tsConfigFiles) {
    const configPath = path.join(projectPath, configFile)
    if (await fs.pathExists(configPath)) {
      await fs.remove(configPath)
    }
  }
}

async function findTypeScriptFiles(dir: string): Promise<string[]> {
  const files: string[] = []
  const entries = await fs.readdir(dir, { withFileTypes: true })
  
  for (const entry of entries) {
    const fullPath = path.join(dir, entry.name)
    
    if (entry.isDirectory() && !entry.name.startsWith('.') && entry.name !== 'node_modules') {
      files.push(...await findTypeScriptFiles(fullPath))
    } else if (entry.isFile() && /\.tsx?$/.test(entry.name)) {
      files.push(fullPath)
    }
  }
  
  return files
}

// Utility functions
function toSnakeCase(str: string): string {
  return str.replace(/[A-Z]/g, letter => `_${letter.toLowerCase()}`).replace(/^_/, '')
}

function toTitleCase(str: string): string {
  return str.replace(/[-_]/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
}

function getDatabaseUrl(config: ProjectConfig): string {
  switch (config.database) {
    case 'postgresql':
      return 'postgresql://user:password@localhost:5432/' + toSnakeCase(config.projectName)
    case 'mysql':
      return 'mysql://user:password@localhost:3306/' + toSnakeCase(config.projectName)
    case 'sqlite':
      return 'sqlite:///./app.db'
    default:
      return 'postgresql://user:password@localhost:5432/' + toSnakeCase(config.projectName)
  }
}