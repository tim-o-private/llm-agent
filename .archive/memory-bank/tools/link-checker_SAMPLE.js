#!/usr/bin/env node
/**
 * Link Checker & Documentation Validator
 * Validates bidirectional links, file length limits, and detects unused files
 */

const fs = require('fs');
const path = require('path');
const glob = require('glob');

// Configuration
const CONFIG = {
  FILE_LIMITS: {
    'memory-bank/README.md': 200,
    'memory-bank/patterns/*.md': 400,
    'memory-bank/active-tasks.md': 200,
    'memory-bank/project-context.md': 300,
  },
  REQUIRED_HEADERS: {
    'webApp/src/**/*.tsx': ['@docs'],
    'webApp/src/**/*.ts': ['@docs'],
    'chatServer/**/*.py': ['@docs'],
    'src/**/*.py': ['@docs'],
  },
  REQUIRED_DOC_SECTIONS: {
    'memory-bank/patterns/*.md': ['**Files**', '**Rules**', '**Examples**'],
  },
  IGNORE_PATTERNS: [
    'node_modules/**',
    '.git/**',
    'dist/**',
    'build/**',
    '**/*.test.*',
    '**/*.spec.*',
  ]
};

class LinkChecker {
  constructor() {
    this.errors = [];
    this.warnings = [];
    this.unusedFiles = [];
    this.referencedFiles = new Set();
  }

  // Main validation function
  async validate() {
    console.log('🔍 Starting documentation validation...\n');
    
    await this.checkFileLengths();
    await this.checkCodeHeaders();
    await this.checkDocumentationLinks();
    await this.detectUnusedFiles();
    
    this.printResults();
    return this.errors.length === 0;
  }

  // Check file length limits
  async checkFileLengths() {
    console.log('📏 Checking file length limits...');
    
    for (const [pattern, limit] of Object.entries(CONFIG.FILE_LIMITS)) {
      const files = glob.sync(pattern);
      
      for (const file of files) {
        const content = fs.readFileSync(file, 'utf8');
        const lineCount = content.split('\n').length;
        
        if (lineCount > limit) {
          this.errors.push({
            type: 'FILE_LENGTH',
            file,
            message: `File has ${lineCount} lines, limit is ${limit}`,
            severity: 'error'
          });
        }
      }
    }
  }

  // Check code file headers for @docs, @rules, @examples
  async checkCodeHeaders() {
    console.log('📋 Checking code file headers...');
    
    for (const [pattern, requiredHeaders] of Object.entries(CONFIG.REQUIRED_HEADERS)) {
      const files = glob.sync(pattern, { ignore: CONFIG.IGNORE_PATTERNS });
      
      for (const file of files) {
        const content = fs.readFileSync(file, 'utf8');
        const headerMatch = content.match(/\/\*\*[\s\S]*?\*\//);
        
        if (!headerMatch) {
          this.warnings.push({
            type: 'MISSING_HEADER',
            file,
            message: 'Missing documentation header',
            severity: 'warning'
          });
          continue;
        }
        
        const header = headerMatch[0];
        
        for (const requiredHeader of requiredHeaders) {
          if (!header.includes(requiredHeader)) {
            this.errors.push({
              type: 'MISSING_DOC_REFERENCE',
              file,
              message: `Missing ${requiredHeader} reference in header`,
              severity: 'error'
            });
          }
        }
        
        // Validate @docs links
        const docsMatches = header.match(/@docs\s+([^\s\n]+)/g);
        if (docsMatches) {
          for (const match of docsMatches) {
            const docPath = match.replace('@docs ', '');
            this.validateDocLink(file, docPath);
          }
        }
        
        // Validate @rules links
        const rulesMatches = header.match(/@rules\s+([^\s\n]+)/g);
        if (rulesMatches) {
          for (const match of rulesMatches) {
            const rulePath = match.replace('@rules ', '');
            this.validateRuleLink(file, rulePath);
          }
        }
      }
    }
  }

  // Check documentation files for required sections and back-links
  async checkDocumentationLinks() {
    console.log('📖 Checking documentation links...');
    
    for (const [pattern, requiredSections] of Object.entries(CONFIG.REQUIRED_DOC_SECTIONS)) {
      const files = glob.sync(pattern);
      
      for (const file of files) {
        const content = fs.readFileSync(file, 'utf8');
        
        // Check required sections
        for (const section of requiredSections) {
          if (!content.includes(section)) {
            this.errors.push({
              type: 'MISSING_SECTION',
              file,
              message: `Missing required section: ${section}`,
              severity: 'error'
            });
          }
        }
        
        // Check back-links to code files
        const codeLinks = content.match(/\[`[^`]+`\]\([^)]+\)/g) || [];
        for (const link of codeLinks) {
          const pathMatch = link.match(/\]\(([^)]+)\)/);
          if (pathMatch) {
            const linkedPath = pathMatch[1];
            this.validateBackLink(file, linkedPath);
          }
        }
        
        // Track this file as referenced
        this.referencedFiles.add(file);
      }
    }
  }

  // Detect unused files
  async detectUnusedFiles() {
    console.log('🗑️  Detecting unused files...');
    
    const allFiles = glob.sync('memory-bank/**/*', { 
      ignore: CONFIG.IGNORE_PATTERNS,
      nodir: true 
    });
    
    for (const file of allFiles) {
      if (!this.referencedFiles.has(file) && !this.isSystemFile(file)) {
        this.unusedFiles.push(file);
      }
    }
  }

  // Validate documentation link
  validateDocLink(sourceFile, docPath) {
    const [filePath, anchor] = docPath.split('#');
    
    if (!fs.existsSync(filePath)) {
      this.errors.push({
        type: 'BROKEN_DOC_LINK',
        file: sourceFile,
        message: `Documentation file not found: ${filePath}`,
        severity: 'error'
      });
      return;
    }
    
    if (anchor) {
      const content = fs.readFileSync(filePath, 'utf8');
      const anchorPattern = new RegExp(`#+\\s*${anchor.replace(/-/g, '[-\\s]')}`, 'i');
      if (!anchorPattern.test(content)) {
        this.warnings.push({
          type: 'MISSING_ANCHOR',
          file: sourceFile,
          message: `Anchor not found in ${filePath}: #${anchor}`,
          severity: 'warning'
        });
      }
    }
    
    this.referencedFiles.add(filePath);
  }

  // Validate rule link
  validateRuleLink(sourceFile, rulePath) {
    const [filePath, ruleId] = rulePath.split('#');
    
    if (!fs.existsSync(filePath)) {
      this.errors.push({
        type: 'BROKEN_RULE_LINK',
        file: sourceFile,
        message: `Rule file not found: ${filePath}`,
        severity: 'error'
      });
      return;
    }
    
    if (ruleId) {
      try {
        const content = fs.readFileSync(filePath, 'utf8');
        const rules = JSON.parse(content);
        const ruleExists = rules.rules?.some(rule => rule.id === ruleId);
        
        if (!ruleExists) {
          this.errors.push({
            type: 'MISSING_RULE',
            file: sourceFile,
            message: `Rule not found in ${filePath}: ${ruleId}`,
            severity: 'error'
          });
        }
      } catch (e) {
        this.errors.push({
          type: 'INVALID_RULE_FILE',
          file: sourceFile,
          message: `Invalid JSON in rule file: ${filePath}`,
          severity: 'error'
        });
      }
    }
    
    this.referencedFiles.add(filePath);
  }

  // Validate back-link from docs to code
  validateBackLink(sourceFile, linkedPath) {
    // Convert relative path to absolute
    const absolutePath = path.resolve(path.dirname(sourceFile), linkedPath);
    
    if (!fs.existsSync(absolutePath)) {
      this.errors.push({
        type: 'BROKEN_BACK_LINK',
        file: sourceFile,
        message: `Code file not found: ${linkedPath}`,
        severity: 'error'
      });
    } else {
      this.referencedFiles.add(absolutePath);
    }
  }

  // Check if file is a system file that shouldn't be flagged as unused
  isSystemFile(file) {
    const systemFiles = [
      'memory-bank/README.md',
      'memory-bank/project-context.md',
      'memory-bank/active-tasks.md',
      'memory-bank/tools/',
    ];
    
    return systemFiles.some(pattern => file.includes(pattern));
  }

  // Print validation results
  printResults() {
    console.log('\n📊 Validation Results:');
    console.log('='.repeat(50));
    
    if (this.errors.length === 0 && this.warnings.length === 0 && this.unusedFiles.length === 0) {
      console.log('✅ All checks passed!');
      return;
    }
    
    if (this.errors.length > 0) {
      console.log(`\n❌ Errors (${this.errors.length}):`);
      this.errors.forEach(error => {
        console.log(`  ${error.file}: ${error.message}`);
      });
    }
    
    if (this.warnings.length > 0) {
      console.log(`\n⚠️  Warnings (${this.warnings.length}):`);
      this.warnings.forEach(warning => {
        console.log(`  ${warning.file}: ${warning.message}`);
      });
    }
    
    if (this.unusedFiles.length > 0) {
      console.log(`\n🗑️  Unused Files (${this.unusedFiles.length}):`);
      this.unusedFiles.forEach(file => {
        console.log(`  ${file} - Consider moving to archive/unused-files/`);
      });
    }
    
    console.log('\n' + '='.repeat(50));
    console.log(`Total: ${this.errors.length} errors, ${this.warnings.length} warnings, ${this.unusedFiles.length} unused files`);
  }
}

// CLI usage
if (require.main === module) {
  const checker = new LinkChecker();
  checker.validate().then(success => {
    process.exit(success ? 0 : 1);
  });
}

module.exports = LinkChecker; 