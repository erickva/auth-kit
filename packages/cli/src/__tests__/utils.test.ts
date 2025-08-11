import validateProjectName from 'validate-npm-package-name'

describe('CLI Utils', () => {
  describe('Project Name Validation', () => {
    it('should accept valid project names', () => {
      const validNames = ['my-app', 'auth-kit-example', 'project123', 'test_app']
      
      validNames.forEach(name => {
        const result = validateProjectName(name)
        expect(result.validForNewPackages).toBe(true)
      })
    })

    it('should reject invalid project names', () => {
      const invalidNames = ['My App', '123start', '.hidden', 'node_modules']
      
      invalidNames.forEach(name => {
        const result = validateProjectName(name)
        expect(result.validForNewPackages).toBe(false)
      })
    })
  })
})