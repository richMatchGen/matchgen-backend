#!/usr/bin/env python
"""
Quick migration script for Railway.
Run this to apply the email verification database changes.
"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'matchgen.settings')
django.setup()

from django.core.management import call_command

print("🚀 Starting Railway migration...")

try:
    # Apply all migrations
    print("📦 Applying migrations...")
    call_command('migrate', verbosity=2)
    print("✅ Migrations completed successfully!")
    
    # Show migration status
    print("\n📋 Migration status:")
    call_command('showmigrations', verbosity=1)
    
    print("\n🎉 Email verification system is now enabled!")
    print("📧 Users will now receive verification emails during registration.")
    
except Exception as e:
    print(f"❌ Migration failed: {e}")
    exit(1)
