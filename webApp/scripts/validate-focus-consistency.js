#!/usr/bin/env node

const fs = require('fs');
const path = require('path');
const glob = require('glob');

// Patterns that indicate manual focus implementations
const MANUAL_FOCUS_PATTERNS = [
  /focus:ring-\d+/g,
  /focus:ring-[a-zA-Z-]+/g,
  /focus-visible:ring-\d+/g,
  /focus-visible:ring-[a-zA-Z-]+/g,
  /focus:outline-none focus:ring/g,
  /focus-visible:outline-none focus-visible:ring/g,
];

// Files that are allowed to have manual focus (exceptions)
const ALLOWED_MANUAL_FOCUS_FILES = [
  'webApp/src/utils/focusStates.ts', // The focus system itself
  'webApp/src/styles/ui-components.css', // Global CSS
  'webApp/src/components/ui/toast.tsx', // Complex toast component
];

// Patterns that indicate proper usage of our focus system
const PROPER_FOCUS_PATTERNS = [
  /getFocusClasses\(\)/g,
  /getCompleteInteractiveClasses\(/g,
  /getFocusRing\(/g,
];

function findTsxFiles() {
  return glob.sync('webApp/src/**/*.{tsx,ts}', {
    ignore: ['webApp/src/**/*.test.{tsx,ts}', 'webApp/src/**/*.spec.{tsx,ts}']
  });
}

function checkFileForManualFocus(filePath) {
  const content = fs.readFileSync(filePath, 'utf8');
  const violations = [];
  
  // Check for manual focus patterns
  MANUAL_FOCUS_PATTERNS.forEach(pattern => {
    const matches = content.match(pattern);
    if (matches) {
      matches.forEach(match => {
        const lines = content.split('\n');
        lines.forEach((line, index) => {
          if (line.includes(match)) {
            violations.push({
              file: filePath,
              line: index + 1,
              pattern: match,
              content: line.trim(),
              type: 'manual_focus'
            });
          }
        });
      });
    }
  });
  
  // Check if file uses proper focus system
  const usesProperFocus = PROPER_FOCUS_PATTERNS.some(pattern => 
    pattern.test(content)
  );
  
  return {
    violations,
    usesProperFocus,
    hasManualFocus: violations.length > 0
  };
}

function main() {
  console.log('🔍 Checking for focus consistency violations...\n');
  
  const files = findTsxFiles();
  let totalViolations = 0;
  let filesWithViolations = 0;
  let filesUsingProperSystem = 0;
  
  const violationsByFile = [];
  
  files.forEach(file => {
    // Skip allowed files
    if (ALLOWED_MANUAL_FOCUS_FILES.some(allowed => file.includes(allowed))) {
      return;
    }
    
    const result = checkFileForManualFocus(file);
    
    if (result.usesProperFocus) {
      filesUsingProperSystem++;
    }
    
    if (result.hasManualFocus) {
      filesWithViolations++;
      totalViolations += result.violations.length;
      violationsByFile.push({
        file,
        violations: result.violations
      });
    }
  });
  
  // Report results
  console.log(`📊 Focus Consistency Report:`);
  console.log(`   Total files checked: ${files.length}`);
  console.log(`   Files using proper focus system: ${filesUsingProperSystem}`);
  console.log(`   Files with violations: ${filesWithViolations}`);
  console.log(`   Total violations: ${totalViolations}\n`);
  
  if (violationsByFile.length > 0) {
    console.log('❌ Focus Consistency Violations:\n');
    
    violationsByFile.forEach(({ file, violations }) => {
      console.log(`📄 ${file}:`);
      violations.forEach(violation => {
        console.log(`   Line ${violation.line}: ${violation.pattern}`);
        console.log(`   Content: ${violation.content}`);
        console.log('');
      });
    });
    
    console.log('💡 To fix these violations:');
    console.log('   1. Import getFocusClasses from @/utils/focusStates');
    console.log('   2. Replace manual focus:ring-* with getFocusClasses()');
    console.log('   3. For complex components, use getCompleteInteractiveClasses()');
    console.log('   4. Remove focus:outline-none when using our system\n');
    
    process.exit(1);
  } else {
    console.log('✅ All files are using consistent focus system!');
    console.log('🎉 Great job maintaining focus consistency!\n');
    process.exit(0);
  }
}

if (require.main === module) {
  main();
} 