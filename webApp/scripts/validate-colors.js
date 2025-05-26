#!/usr/bin/env node

const fs = require('fs');
const path = require('path');
const glob = require('glob');

// Forbidden color patterns
const FORBIDDEN_PATTERNS = [
  // Tailwind default colors
  /\b(bg|text|border|ring)-(blue|red|green|yellow|purple|pink|indigo|gray|slate|zinc|neutral|stone)-\d+\b/g,
  // Hex colors
  /#[0-9a-fA-F]{3,6}/g,
  // RGB/HSL colors
  /rgb\s*\([^)]+\)/g,
  /hsl\s*\([^)]+\)/g,
];

// Approved semantic tokens
const APPROVED_TOKENS = [
  'brand-primary', 'brand-primary-hover', 'brand-primary-text',
  'ui-bg', 'ui-bg-alt', 'ui-element-bg', 'ui-modal-bg', 'ui-surface',
  'ui-interactive-bg', 'ui-interactive-bg-hover', 'ui-interactive-bg-active',
  'ui-border', 'ui-border-hover', 'ui-border-focus',
  'text-primary', 'text-secondary', 'text-muted', 'text-disabled',
  'text-accent', 'text-accent-hover', 'text-destructive',
  'accent-subtle', 'accent-surface', 'accent-indicator',
  'success-indicator', 'success-strong', 'warning-strong', 'destructive',
];

function validateFile(filePath) {
  const content = fs.readFileSync(filePath, 'utf8');
  const violations = [];
  
  // Check for forbidden patterns
  FORBIDDEN_PATTERNS.forEach((pattern, index) => {
    const matches = content.match(pattern);
    if (matches) {
      const patternNames = ['Tailwind colors', 'Hex colors', 'RGB colors', 'HSL colors'];
      violations.push({
        type: patternNames[index] || 'Unknown pattern',
        matches: [...new Set(matches)], // Remove duplicates
        pattern: pattern.toString(),
      });
    }
  });
  
  return violations;
}

function scanDirectory(directory, extensions = ['tsx', 'ts', 'css', 'scss']) {
  const pattern = `${directory}/**/*.{${extensions.join(',')}}`;
  const files = glob.sync(pattern, {
    ignore: [
      '**/node_modules/**',
      '**/dist/**',
      '**/build/**',
      '**/*.d.ts',
    ]
  });
  
  const results = {
    totalFiles: files.length,
    violatingFiles: 0,
    violations: [],
  };
  
  files.forEach(file => {
    const violations = validateFile(file);
    if (violations.length > 0) {
      results.violatingFiles++;
      results.violations.push({
        file: path.relative(process.cwd(), file),
        violations,
      });
    }
  });
  
  return results;
}

function generateReport(results) {
  console.log('\n🎨 Color Usage Validation Report');
  console.log('================================\n');
  
  if (results.violatingFiles === 0) {
    console.log('✅ All files pass color validation!');
    console.log(`📊 Scanned ${results.totalFiles} files\n`);
    return true;
  }
  
  console.log(`❌ Found violations in ${results.violatingFiles}/${results.totalFiles} files\n`);
  
  results.violations.forEach(({ file, violations }) => {
    console.log(`📄 ${file}`);
    violations.forEach(({ type, matches }) => {
      console.log(`   ❌ ${type}:`);
      matches.forEach(match => {
        console.log(`      - ${match}`);
      });
    });
    console.log('');
  });
  
  console.log('💡 Fix suggestions:');
  console.log('   • Replace Tailwind colors with semantic tokens (bg-ui-element-bg, text-text-primary)');
  console.log('   • Replace hex/rgb/hsl with Radix variables (var(--gray-3), var(--accent-9))');
  console.log('   • See style guide for approved color tokens\n');
  
  return false;
}

function main() {
  const srcDir = path.join(__dirname, '../src');
  
  console.log('🔍 Scanning for color violations...');
  const results = scanDirectory(srcDir);
  const passed = generateReport(results);
  
  if (!passed) {
    process.exit(1);
  }
}

// Run if called directly
if (require.main === module) {
  main();
}

module.exports = { validateFile, scanDirectory, generateReport }; 