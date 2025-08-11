import { Command } from 'commander'
import inquirer from 'inquirer'
import chalk from 'chalk'
import ora from 'ora'
import path from 'path'
import fs from 'fs-extra'
import { execa } from 'execa'
import validateProjectName from 'validate-npm-package-name'
import { ProjectConfig, ProjectType, FrameworkType, DatabaseType, Features } from '../types'
import { copyTemplate } from '../utils/template'
import { installDependencies } from '../utils/install'
import { generateEnvFile } from '../utils/env'

export const createCommand = new Command('create')
  .description('Create a new Auth Kit project')
  .argument('[project-name]', 'Name of the project')
  .option('-t, --template <template>', 'Project template (react-spa, nextjs, fastapi, fullstack)')
  .option('--typescript', 'Use TypeScript (default)')
  .option('--javascript', 'Use JavaScript')
  .option('--skip-install', 'Skip dependency installation')
  .option('--skip-git', 'Skip git initialization')
  .action(async (projectName: string | undefined, options: any) => {
    try {
      // Get project configuration through prompts
      const config = await getProjectConfig(projectName, options)
      
      // Validate project name
      const validation = validateProjectName(config.projectName)
      if (!validation.validForNewPackages) {
        console.error(chalk.red(`Invalid project name: ${validation.errors?.[0] || 'Unknown error'}`))
        process.exit(1)
      }

      // Check if directory already exists
      const projectPath = path.join(process.cwd(), config.projectName)
      if (fs.existsSync(projectPath)) {
        const { overwrite } = await inquirer.prompt([
          {
            type: 'confirm',
            name: 'overwrite',
            message: `Directory ${config.projectName} already exists. Overwrite?`,
            default: false,
          },
        ])
        
        if (!overwrite) {
          console.log(chalk.yellow('Operation cancelled'))
          process.exit(0)
        }
        
        await fs.remove(projectPath)
      }

      // Create project
      console.log()
      const spinner = ora(`Creating project ${chalk.cyan(config.projectName)}...`).start()

      try {
        // Create project directory
        await fs.ensureDir(projectPath)

        // Copy template files
        await copyTemplate(config, projectPath)

        // Generate environment files
        await generateEnvFile(config, projectPath)

        spinner.succeed('Project created')

        // Initialize git repository
        if (!options.skipGit) {
          spinner.start('Initializing git repository...')
          await execa('git', ['init'], { cwd: projectPath })
          await execa('git', ['add', '.'], { cwd: projectPath })
          await execa('git', ['commit', '-m', 'Initial commit from Auth Kit CLI'], { cwd: projectPath })
          spinner.succeed('Git repository initialized')
        }

        // Install dependencies
        if (!options.skipInstall) {
          await installDependencies(projectPath, config.packageManager)
        }

        // Success message
        console.log()
        console.log(chalk.green('✨ Project created successfully!'))
        console.log()
        console.log('Next steps:')
        console.log(chalk.cyan(`  cd ${config.projectName}`))
        
        if (options.skipInstall) {
          console.log(chalk.cyan(`  ${config.packageManager} install`))
        }

        // Project-specific instructions
        if (config.projectType === 'fullstack') {
          console.log()
          console.log('To start the development servers:')
          console.log(chalk.cyan(`  ${config.packageManager} run dev:backend  # Start backend`))
          console.log(chalk.cyan(`  ${config.packageManager} run dev:frontend # Start frontend`))
        } else if (config.projectType === 'backend') {
          console.log(chalk.cyan(`  ${config.packageManager} run dev`))
        } else {
          console.log(chalk.cyan(`  ${config.packageManager} run dev`))
        }

        console.log()
        console.log('For more information, visit:')
        console.log(chalk.blue('  https://github.com/yourusername/auth-kit'))
        console.log()

      } catch (error) {
        spinner.fail('Failed to create project')
        throw error
      }

    } catch (error) {
      console.error(chalk.red('Error:'), error)
      process.exit(1)
    }
  })

async function getProjectConfig(projectName: string | undefined, options: any): Promise<ProjectConfig> {
  const answers = await inquirer.prompt([
    {
      type: 'input',
      name: 'projectName',
      message: 'Project name:',
      default: 'my-auth-app',
      when: !projectName,
      validate: (input: string) => {
        const validation = validateProjectName(input)
        return validation.validForNewPackages || validation.errors?.[0] || 'Invalid project name'
      },
    },
    {
      type: 'list',
      name: 'projectType',
      message: 'What type of project do you want to create?',
      choices: [
        { name: 'Full-stack application (Frontend + Backend)', value: 'fullstack' },
        { name: 'Frontend only (React/Next.js)', value: 'frontend' },
        { name: 'Backend only (FastAPI)', value: 'backend' },
      ],
      when: !options.template,
    },
    {
      type: 'list',
      name: 'framework',
      message: 'Which frontend framework?',
      choices: [
        { name: 'React (Vite)', value: 'react' },
        { name: 'Next.js (App Router)', value: 'nextjs' },
      ],
      when: (answers: any) => 
        (answers.projectType === 'frontend' || answers.projectType === 'fullstack') && !options.template,
    },
    {
      type: 'list',
      name: 'database',
      message: 'Which database?',
      choices: [
        { name: 'PostgreSQL (Recommended)', value: 'postgresql' },
        { name: 'SQLite (Good for development)', value: 'sqlite' },
        { name: 'MySQL', value: 'mysql' },
      ],
      when: (answers: any) => 
        (answers.projectType === 'backend' || answers.projectType === 'fullstack') && !options.template,
    },
    {
      type: 'checkbox',
      name: 'features',
      message: 'Which authentication features do you want to include?',
      choices: [
        { name: 'Email/Password login', value: 'password', checked: true },
        { name: 'Passkeys (WebAuthn)', value: 'passkeys', checked: true },
        { name: 'Two-factor authentication', value: 'twoFactor', checked: true },
        { name: 'Email verification', value: 'emailVerification', checked: true },
        { name: 'Password reset', value: 'passwordReset', checked: true },
        { name: 'Social login (OAuth)', value: 'socialLogin', checked: false },
      ],
    },
    {
      type: 'list',
      name: 'styling',
      message: 'Which styling solution?',
      choices: [
        { name: 'Tailwind CSS', value: 'tailwind' },
        { name: 'CSS Modules', value: 'css-modules' },
        { name: 'Styled Components', value: 'styled-components' },
        { name: 'Plain CSS', value: 'css' },
      ],
      when: (answers: any) => answers.projectType !== 'backend',
    },
    {
      type: 'list',
      name: 'packageManager',
      message: 'Which package manager?',
      choices: [
        { name: 'npm', value: 'npm' },
        { name: 'yarn', value: 'yarn' },
        { name: 'pnpm', value: 'pnpm' },
      ],
    },
  ])

  // Merge answers with options
  const config: ProjectConfig = {
    projectName: projectName || answers.projectName,
    projectType: options.template ? getProjectTypeFromTemplate(options.template) : answers.projectType,
    framework: options.template ? getFrameworkFromTemplate(options.template) : answers.framework,
    database: answers.database || 'postgresql',
    features: answers.features || ['password', 'passkeys', 'twoFactor', 'emailVerification', 'passwordReset'],
    language: options.javascript ? 'javascript' : 'typescript',
    styling: answers.styling || 'tailwind',
    packageManager: answers.packageManager || 'npm',
  }

  return config
}

function getProjectTypeFromTemplate(template: string): ProjectType {
  switch (template) {
    case 'react-spa':
    case 'nextjs':
      return 'frontend'
    case 'fastapi':
      return 'backend'
    case 'fullstack':
      return 'fullstack'
    default:
      throw new Error(`Unknown template: ${template}`)
  }
}

function getFrameworkFromTemplate(template: string): FrameworkType {
  switch (template) {
    case 'react-spa':
      return 'react'
    case 'nextjs':
      return 'nextjs'
    case 'fastapi':
    case 'fullstack':
      return 'react' // Default to React for fullstack
    default:
      return 'react'
  }
}