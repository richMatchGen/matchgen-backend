#!/usr/bin/env node

/**
 * Script to fix hardcoded production URLs in the frontend
 * This ensures all API calls use environment-based URLs
 */

const fs = require('fs');
const path = require('path');

const PRODUCTION_URL = 'https://matchgen-backend-production.up.railway.app/api/';
const FRONTEND_SRC_DIR = path.join(__dirname, '..', 'matchgen-frontend', 'src');

// Files to fix (relative to src directory)
const FILES_TO_FIX = [
  'pages/TextElementManagement.jsx',
  'pages/creatematch.jsx',
  'pages/ClubOverview.jsx',
  'pages/FixturesManagement.jsx',
  'pages/EnhancedTemplateSelection.jsx',
  'components/MatchdayPostGenerator.jsx',
  'pages/ResetPassword.jsx',
  'components/ResultCard.jsx',
  'pages/TemplateDetails.jsx',
  'pages/SubscriptionManagement.jsx',
  'pages/TeamManagement.jsx',
  'components/FeatureRestrictedButton.jsx',
  'components/FeatureRestrictedElement.jsx',
  'hooks/useFeatureAccess.js',
  'pages/createclub.jsx',
  'pages/ChoosePackage.jsx',
  'components/quickLinksCard.jsx',
  'components/TodoList.jsx',
  'components/EmailVerificationBanner.jsx',
  'components/MatchdayPostGenerator_fixed.jsx',
  'components/FeatureCatalog.jsx',
  'components/FixtureCard.jsx',
  'components/MatchdayCard.jsx',
  'components/EditFixtureModal.jsx',
  'components/GraphicPackList.jsx',
  'pages/editclub.jsx',
  'hooks/useClub.jsx',
  'hooks/auth.js'
];

function fixFile(filePath) {
  const fullPath = path.join(FRONTEND_SRC_DIR, filePath);
  
  if (!fs.existsSync(fullPath)) {
    console.log(`⚠️  File not found: ${filePath}`);
    return false;
  }

  let content = fs.readFileSync(fullPath, 'utf8');
  let modified = false;

  // Check if file already imports env
  const hasEnvImport = content.includes("import env from '../config/environment'") || 
                      content.includes("import env from \"../config/environment\"");

  // Fix hardcoded production URLs
  const urlRegex = /https:\/\/matchgen-backend-production\.up\.railway\.app\/api\//g;
  if (urlRegex.test(content)) {
    content = content.replace(urlRegex, '${env.API_BASE_URL}/');
    modified = true;
  }

  // Add env import if needed and file was modified
  if (modified && !hasEnvImport) {
    // Find the last import statement
    const importRegex = /import\s+.*?from\s+['"][^'"]+['"];?\s*$/gm;
    const imports = content.match(importRegex);
    
    if (imports && imports.length > 0) {
      const lastImport = imports[imports.length - 1];
      const lastImportIndex = content.lastIndexOf(lastImport);
      const insertIndex = lastImportIndex + lastImport.length;
      
      content = content.slice(0, insertIndex) + 
                "\nimport env from '../config/environment';" + 
                content.slice(insertIndex);
    }
  }

  if (modified) {
    fs.writeFileSync(fullPath, content, 'utf8');
    console.log(`✅ Fixed: ${filePath}`);
    return true;
  } else {
    console.log(`⏭️  No changes needed: ${filePath}`);
    return false;
  }
}

function main() {
  console.log('🔧 Fixing hardcoded production URLs...\n');
  
  let fixedCount = 0;
  
  FILES_TO_FIX.forEach(file => {
    if (fixFile(file)) {
      fixedCount++;
    }
  });
  
  console.log(`\n🎉 Fixed ${fixedCount} files!`);
  console.log('\n📋 Next steps:');
  console.log('1. Test the application in development mode');
  console.log('2. Test the application in production mode');
  console.log('3. Commit the changes when everything works');
}

if (require.main === module) {
  main();
}

module.exports = { fixFile, FILES_TO_FIX };
