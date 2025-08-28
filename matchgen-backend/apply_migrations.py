#!/usr/bin/env python
"""
Script to apply all Django migrations on Railway.
This should be run on Railway to apply the email verification database changes.
"""

import os
import django
import sys

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'matchgen.settings')
django.setup()

from django.core.management import execute_from_command_line
from django.db import connection

def apply_migrations():
    """Apply all pending migrations."""
    print("Starting migration process...")
    
    try:
        # Check current migration status
        print("Checking current migration status...")
        execute_from_command_line(['manage.py', 'showmigrations'])
        
        # Apply migrations
        print("\nApplying migrations...")
        execute_from_command_line(['manage.py', 'migrate'])
        
        # Check final migration status
        print("\nFinal migration status:")
        execute_from_command_line(['manage.py', 'showmigrations'])
        
        print("\n✅ Migrations completed successfully!")
        
    except Exception as e:
        print(f"❌ Error during migration: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    apply_migrations()
