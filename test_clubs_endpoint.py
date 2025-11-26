#!/usr/bin/env python
"""
Test script to verify the AllClubsListView endpoint works correctly.
"""
import os
import sys
import django
from django.conf import settings

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'matchgen.settings')
django.setup()

from users.models import User, Club
from users.views import AllClubsListView
from rest_framework.test import APIRequestFactory
from rest_framework import status
from django.contrib.auth import get_user_model

def test_all_clubs_endpoint():
    """Test the AllClubsListView endpoint."""
    print("Testing AllClubsListView endpoint...")
    
    # Get a test user
    try:
        user = User.objects.get(email='rich@matchgen.co.uk')
        print(f"Found test user: {user.email}")
    except User.DoesNotExist:
        print("Test user rich@matchgen.co.uk not found")
        return
    
    # Create a request factory
    factory = APIRequestFactory()
    
    # Create a GET request
    request = factory.get('/api/users/clubs/all/')
    request.user = user
    
    # Create the view instance
    view = AllClubsListView()
    
    try:
        # Call the get method
        response = view.get(request)
        
        print(f"Response status: {response.status_code}")
        print(f"Response data: {response.data}")
        
        if response.status_code == 200:
            print(f"✅ SUCCESS: Found {len(response.data)} clubs")
            for club in response.data[:3]:  # Show first 3 clubs
                print(f"  - {club['name']} (ID: {club['id']})")
        else:
            print(f"❌ ERROR: Status {response.status_code}")
            
    except Exception as e:
        print(f"❌ EXCEPTION: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_all_clubs_endpoint()




