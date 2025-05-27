import { 
  validateSemanticColors, 
  validateColorClasses, 
  isApprovedColorToken,
  getAllApprovedTokens 
} from '../color-validation';

describe('Color Validation', () => {
  describe('validateSemanticColors', () => {
    it('should pass for elements with semantic color classes', () => {
      const element = document.createElement('div');
      element.className = 'bg-ui-element-bg text-text-primary border-ui-border';
      
      const result = validateSemanticColors(element);
      expect(result.valid).toBe(true);
      expect(result.violations).toHaveLength(0);
    });

    it('should fail for elements with forbidden Tailwind colors', () => {
      const element = document.createElement('div');
      element.className = 'bg-blue-500 text-gray-900 border-red-400';
      
      const result = validateSemanticColors(element);
      expect(result.valid).toBe(false);
      expect(result.violations.length).toBeGreaterThan(0);
      expect(result.violations[0]).toContain('forbidden');
    });

    it('should fail for elements with hardcoded inline styles', () => {
      const element = document.createElement('div');
      element.setAttribute('style', 'background-color: #3b82f6; color: rgb(255, 255, 255);');
      
      const result = validateSemanticColors(element);
      expect(result.valid).toBe(false);
      expect(result.violations.length).toBeGreaterThan(0);
    });
  });

  describe('validateColorClasses', () => {
    it('should identify approved and forbidden classes', () => {
      const className = 'bg-ui-element-bg text-blue-500 border-ui-border';
      
      const result = validateColorClasses(className);
      expect(result.valid).toBe(false);
      expect(result.approvedClasses).toContain('bg-ui-element-bg');
      expect(result.approvedClasses).toContain('border-ui-border');
      expect(result.forbiddenClasses).toContain('text-blue-500');
    });
  });

  describe('isApprovedColorToken', () => {
    it('should return true for approved tokens', () => {
      expect(isApprovedColorToken('brand-primary')).toBe(true);
      expect(isApprovedColorToken('ui-element-bg')).toBe(true);
      expect(isApprovedColorToken('text-primary')).toBe(true);
    });

    it('should return false for forbidden tokens', () => {
      expect(isApprovedColorToken('blue-500')).toBe(false);
      expect(isApprovedColorToken('gray-900')).toBe(false);
      expect(isApprovedColorToken('red-400')).toBe(false);
    });
  });

  describe('getAllApprovedTokens', () => {
    it('should return a non-empty array of approved tokens', () => {
      const tokens = getAllApprovedTokens();
      expect(Array.isArray(tokens)).toBe(true);
      expect(tokens.length).toBeGreaterThan(0);
      expect(tokens).toContain('brand-primary');
      expect(tokens).toContain('ui-element-bg');
      expect(tokens).toContain('text-primary');
    });
  });
}); 