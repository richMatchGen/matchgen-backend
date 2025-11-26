#!/usr/bin/env python
"""
Script to get all clubs with bespoke template packages
"""
import os
import sys
import django

# Add the project directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'matchgen.settings')
django.setup()

from users.models import Club
from django.db import connection

# Get all clubs with bespoke templates using ORM
clubs_with_bespoke = Club.objects.filter(
    selected_pack__is_bespoke=True
).select_related('selected_pack', 'user').order_by('name')

print("\n" + "="*80)
print("CLUBS WITH BESPOKE TEMPLATE PACKAGES")
print("="*80 + "\n")

if clubs_with_bespoke.exists():
    for club in clubs_with_bespoke:
        print(f"Club ID: {club.id}")
        print(f"  Name: {club.name}")
        print(f"  Sport: {club.sport}")
        print(f"  Owner: {club.user.email}")
        print(f"  Subscription Tier: {club.subscription_tier or 'None'}")
        print(f"  Subscription Active: {club.subscription_active}")
        print(f"  Graphic Pack: {club.selected_pack.name if club.selected_pack else 'None'}")
        print(f"  Pack ID: {club.selected_pack.id if club.selected_pack else 'N/A'}")
        print(f"  Pack Active: {club.selected_pack.is_active if club.selected_pack else 'N/A'}")
        print(f"  Location: {club.location or 'N/A'}")
        print("-" * 80)
    
    print(f"\nTotal: {clubs_with_bespoke.count()} club(s) with bespoke templates")
else:
    print("No clubs found with bespoke template packages.")

# Also show the raw SQL query
print("\n" + "="*80)
print("RAW SQL QUERY:")
print("="*80)
print("""
SELECT 
    c.id AS club_id,
    c.name AS club_name,
    c.sport,
    c.subscription_tier,
    c.subscription_active,
    c.logo AS club_logo,
    c.location,
    u.email AS owner_email,
    gp.id AS graphic_pack_id,
    gp.name AS graphic_pack_name,
    gp.is_bespoke,
    gp.is_active AS pack_active,
    gp.sport AS pack_sport,
    gp.tier AS pack_tier
FROM 
    users_club c
INNER JOIN 
    graphicpack_graphicpack gp ON c.selected_pack_id = gp.id
INNER JOIN 
    users_user u ON c.user_id = u.id
WHERE 
    gp.is_bespoke = true
ORDER BY 
    c.name;
""")

# Execute and show raw SQL results
print("\n" + "="*80)
print("EXECUTING RAW SQL:")
print("="*80 + "\n")

with connection.cursor() as cursor:
    cursor.execute("""
        SELECT 
            c.id AS club_id,
            c.name AS club_name,
            c.sport,
            c.subscription_tier,
            c.subscription_active,
            u.email AS owner_email,
            gp.id AS graphic_pack_id,
            gp.name AS graphic_pack_name,
            gp.is_bespoke,
            gp.is_active AS pack_active
        FROM 
            users_club c
        INNER JOIN 
            graphicpack_graphicpack gp ON c.selected_pack_id = gp.id
        INNER JOIN 
            users_user u ON c.user_id = u.id
        WHERE 
            gp.is_bespoke = true
        ORDER BY 
            c.name;
    """)
    
    columns = [col[0] for col in cursor.description]
    results = cursor.fetchall()
    
    if results:
        # Print header
        print(" | ".join(f"{col:20}" for col in columns))
        print("-" * 120)
        
        # Print rows
        for row in results:
            print(" | ".join(f"{str(val):20}" for val in row))
        
        print(f"\nTotal rows: {len(results)}")
    else:
        print("No results found.")

