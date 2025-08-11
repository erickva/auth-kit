export type ProjectType = 'frontend' | 'backend' | 'fullstack'
export type FrameworkType = 'react' | 'nextjs'
export type DatabaseType = 'postgresql' | 'sqlite' | 'mysql'
export type LanguageType = 'typescript' | 'javascript'
export type StylingType = 'tailwind' | 'css-modules' | 'styled-components' | 'css'
export type PackageManager = 'npm' | 'yarn' | 'pnpm'

export interface Features {
  password: boolean
  passkeys: boolean
  twoFactor: boolean
  emailVerification: boolean
  passwordReset: boolean
  socialLogin: boolean
}

export interface ProjectConfig {
  projectName: string
  projectType: ProjectType
  framework: FrameworkType
  database: DatabaseType
  features: string[]
  language: LanguageType
  styling: StylingType
  packageManager: PackageManager
}