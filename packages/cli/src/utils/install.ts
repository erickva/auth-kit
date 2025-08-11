import { execa } from 'execa'
import ora from 'ora'
import chalk from 'chalk'
import path from 'path'
import { PackageManager } from '../types'

export async function installDependencies(projectPath: string, packageManager: PackageManager) {
  const spinner = ora('Installing dependencies...').start()
  
  try {
    // Install frontend dependencies
    const frontendPath = path.join(projectPath, 'frontend')
    const hasFrontend = await checkDirectory(frontendPath)
    
    if (hasFrontend) {
      spinner.text = 'Installing frontend dependencies...'
      await runInstall(frontendPath, packageManager)
    }
    
    // Install backend dependencies
    const backendPath = path.join(projectPath, 'backend')
    const hasBackend = await checkDirectory(backendPath)
    
    if (hasBackend) {
      spinner.text = 'Installing backend dependencies...'
      await installPythonDependencies(backendPath)
    }
    
    // Install root dependencies if it's not a fullstack project
    if (!hasFrontend && !hasBackend) {
      await runInstall(projectPath, packageManager)
    }
    
    spinner.succeed('Dependencies installed')
  } catch (error) {
    spinner.fail('Failed to install dependencies')
    console.error(chalk.red('Error:'), error)
    console.log()
    console.log('You can install dependencies manually by running:')
    console.log(chalk.cyan(`  cd ${path.basename(projectPath)}`))
    console.log(chalk.cyan(`  ${packageManager} install`))
  }
}

async function runInstall(cwd: string, packageManager: PackageManager) {
  const installCommand = getInstallCommand(packageManager)
  
  await execa(packageManager, installCommand, {
    cwd,
    stdio: 'pipe',
  })
}

async function installPythonDependencies(backendPath: string) {
  try {
    // Create virtual environment
    await execa('python', ['-m', 'venv', 'venv'], {
      cwd: backendPath,
      stdio: 'pipe',
    })
    
    // Determine pip path based on OS
    const isWindows = process.platform === 'win32'
    const pipPath = isWindows 
      ? path.join(backendPath, 'venv', 'Scripts', 'pip')
      : path.join(backendPath, 'venv', 'bin', 'pip')
    
    // Install requirements
    await execa(pipPath, ['install', '-r', 'requirements.txt'], {
      cwd: backendPath,
      stdio: 'pipe',
    })
  } catch (error) {
    // If venv creation fails, try with python3
    try {
      await execa('python3', ['-m', 'venv', 'venv'], {
        cwd: backendPath,
        stdio: 'pipe',
      })
      
      const isWindows = process.platform === 'win32'
      const pipPath = isWindows 
        ? path.join(backendPath, 'venv', 'Scripts', 'pip')
        : path.join(backendPath, 'venv', 'bin', 'pip')
      
      await execa(pipPath, ['install', '-r', 'requirements.txt'], {
        cwd: backendPath,
        stdio: 'pipe',
      })
    } catch (pythonError) {
      console.log(chalk.yellow('\nNote: Python dependencies were not installed automatically.'))
      console.log('To install Python dependencies manually:')
      console.log(chalk.cyan('  cd backend'))
      console.log(chalk.cyan('  python -m venv venv'))
      console.log(chalk.cyan('  source venv/bin/activate  # On Windows: venv\\Scripts\\activate'))
      console.log(chalk.cyan('  pip install -r requirements.txt'))
    }
  }
}

function getInstallCommand(packageManager: PackageManager): string[] {
  switch (packageManager) {
    case 'npm':
      return ['install']
    case 'yarn':
      return ['install']
    case 'pnpm':
      return ['install']
    default:
      return ['install']
  }
}

async function checkDirectory(dirPath: string): Promise<boolean> {
  try {
    const fs = await import('fs-extra')
    return await fs.pathExists(dirPath)
  } catch {
    return false
  }
}