#!/usr/bin/env node

import { Command } from 'commander'
import chalk from 'chalk'
import { createCommand } from './commands/create'
import { addCommand } from './commands/add'
import { generateCommand } from './commands/generate'

const program = new Command()

// CLI metadata
program
  .name('auth-kit')
  .description('CLI tool for scaffolding Auth Kit projects')
  .version('1.0.0')

// ASCII art logo
console.log(chalk.cyan(`
    ___         __  __       __ __ _ __ 
   / _ | __ __ / /_/ /      / //_/(_) /_
  / __ |/ // // __/ _ \\    / ,<  / / __/
 /_/ |_|\\_,_/ \\__/_//_/   /_/|_|/_/\\__/ 
                                         
`))

// Add commands
program.addCommand(createCommand)
program.addCommand(addCommand)
program.addCommand(generateCommand)

// Parse command line arguments
program.parse(process.argv)

// Show help if no command provided
if (!process.argv.slice(2).length) {
  program.outputHelp()
}