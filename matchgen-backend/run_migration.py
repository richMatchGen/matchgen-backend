#!/usr/bin/env python
"""
Script to run database migration for email verification fields.
This should be run on Railway to apply the migration.
"""

import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'matchgen.settings')
django.setup()

from django.core.management import execute_from_command_line

if __name__ == '__main__':
    print("Running migration for email verification fields...")
    execute_from_command_line(['manage.py', 'migrate', 'users'])
    print("Migration completed!")
