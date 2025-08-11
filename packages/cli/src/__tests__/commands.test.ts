import { Command } from 'commander'
import { createCommand } from '../commands/create'
import { addCommand } from '../commands/add'
import { generateCommand } from '../commands/generate'

describe('CLI Commands', () => {
  describe('Create Command', () => {
    it('should be defined with correct properties', () => {
      expect(createCommand).toBeInstanceOf(Command)
      expect(createCommand.name()).toBe('create')
      expect(createCommand.description()).toContain('Create a new Auth Kit project')
    })

    it('should have the correct options', () => {
      const options = createCommand.options
      const optionNames = options.map(opt => opt.long)
      
      expect(optionNames).toContain('--template')
      expect(optionNames).toContain('--typescript')
      expect(optionNames).toContain('--javascript')
      expect(optionNames).toContain('--skip-install')
      expect(optionNames).toContain('--skip-git')
    })
  })

  describe('Add Command', () => {
    it('should be defined with correct properties', () => {
      expect(addCommand).toBeInstanceOf(Command)
      expect(addCommand.name()).toBe('add')
      expect(addCommand.description()).toContain('Add Auth Kit to an existing project')
    })

    it('should have framework option', () => {
      const options = addCommand.options
      const frameworkOption = options.find(opt => opt.long === '--framework')
      
      expect(frameworkOption).toBeDefined()
    })
  })

  describe('Generate Command', () => {
    it('should be defined with correct properties', () => {
      expect(generateCommand).toBeInstanceOf(Command)
      expect(generateCommand.name()).toBe('generate')
      expect(generateCommand.description()).toContain('Generate auth-related components')
    })

    it('should have alias "g"', () => {
      expect(generateCommand.alias()).toBe('g')
    })

    it('should have typescript and javascript options', () => {
      const options = generateCommand.options
      const optionNames = options.map(opt => opt.long)
      
      expect(optionNames).toContain('--typescript')
      expect(optionNames).toContain('--javascript')
    })
  })
})