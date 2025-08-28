#!/usr/bin/env python
"""
Simple migration script for Railway deployment.
Run this to apply the email verification database changes.
"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'matchgen.settings')
django.setup()

from django.core.management import call_command

print("🚀 Applying Django migrations...")

try:
    # Apply all migrations
    call_command('migrate', verbosity=2)
    print("✅ Migrations completed successfully!")
    
    # Show migration status
    print("\n📋 Migration status:")
    call_command('showmigrations', verbosity=1)
    
except Exception as e:
    print(f"❌ Migration failed: {e}")
    exit(1)
