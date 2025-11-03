#!/usr/bin/env python3
"""
Tenant Setup Script for Vertigo AI Recruitment System

This script helps you create new tenants with initial admin users.
Run this script to set up multiple organizations with their own credentials.

Usage:
    python setup_tenant.py

Requirements:
    - MongoDB connection configured
    - Environment variables set (MONGO_CONNECTION_STRING, JWT_SECRET)
"""

import os
import sys
import getpass
from datetime import datetime

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.tenant_service import create_tenant, ensure_tenant_collections
from services.user_service import create_user
from services.data_manager import db


def setup_tenant():
    """Interactive tenant setup"""
    print("🏢 Vertigo AI - Tenant Setup")
    print("=" * 50)
    print()
    
    # Check database connection
    if db is None:
        print("❌ Error: Cannot connect to MongoDB")
        print("Please check your MONGO_CONNECTION_STRING environment variable")
        return False
    
    print("✅ Database connection established")
    print()
    
    # Get company information
    company_name = input("Company Name: ").strip()
    if not company_name:
        print("❌ Company name is required")
        return False
    
    # Get admin user information
    admin_name = input("Admin Full Name: ").strip()
    if not admin_name:
        print("❌ Admin name is required")
        return False
    
    admin_email = input("Admin Email: ").strip()
    if not admin_email or "@" not in admin_email:
        print("❌ Valid email address is required")
        return False
    
    # Check if user already exists
    from services.user_service import get_user_by_email
    existing_user = get_user_by_email(admin_email)
    if existing_user:
        print(f"❌ User with email {admin_email} already exists")
        return False
    
    # Get password
    while True:
        admin_password = getpass.getpass("Admin Password: ")
        if len(admin_password) < 8:
            print("❌ Password must be at least 8 characters long")
            continue
        
        confirm_password = getpass.getpass("Confirm Password: ")
        if admin_password != confirm_password:
            print("❌ Passwords do not match")
            continue
        
        break
    
    print()
    print("Creating tenant and admin user...")
    
    try:
        # Create tenant
        tenant_id = create_tenant(admin_email, company_name)
        print(f"✅ Tenant created: {tenant_id}")
        
        # Ensure tenant collections exist
        ensure_tenant_collections(tenant_id)
        print("✅ Tenant collections created")
        
        # Create admin user
        user_id = create_user(
            email=admin_email,
            password=admin_password,
            tenant_id=tenant_id,
            role="admin",
            name=admin_name
        )
        
        if not user_id:
            print("❌ Failed to create admin user")
            return False
        
        print(f"✅ Admin user created: {user_id}")
        
        print()
        print("🎉 Setup completed successfully!")
        print("=" * 50)
        print(f"Company: {company_name}")
        print(f"Tenant ID: {tenant_id}")
        print(f"Admin Email: {admin_email}")
        print(f"Admin Name: {admin_name}")
        print()
        print("🔑 Login credentials:")
        print(f"   Email: {admin_email}")
        print(f"   Password: [as entered]")
        print()
        print("📝 Next steps:")
        print("   1. Save these credentials securely")
        print("   2. Login to the HR dashboard")
        print("   3. Create additional users from the 'Gestione Utenti' page")
        print("   4. Set up your first job position")
        print()
        
        return True
        
    except Exception as e:
        print(f"❌ Error during setup: {e}")
        return False


def list_tenants():
    """List existing tenants"""
    if db is None:
        print("❌ Cannot connect to database")
        return
    
    print("📋 Existing Tenants:")
    print("=" * 50)
    
    try:
        tenants = list(db["tenants"].find({"status": "active"}))
        if not tenants:
            print("No tenants found")
            return
        
        for tenant in tenants:
            print(f"🏢 {tenant.get('company_name', 'Unknown')}")
            print(f"   ID: {tenant.get('_id')}")
            print(f"   Email: {tenant.get('email')}")
            print(f"   Created: {tenant.get('created_at', {}).get('$date', 'Unknown')}")
            print()
            
    except Exception as e:
        print(f"❌ Error listing tenants: {e}")


def main():
    """Main function"""
    if len(sys.argv) > 1 and sys.argv[1] == "list":
        list_tenants()
        return
    
    print("Welcome to Vertigo AI Tenant Setup!")
    print()
    print("This script will help you create a new tenant (organization)")
    print("with an initial admin user for the recruitment system.")
    print()
    
    choice = input("Do you want to continue? (y/n): ").strip().lower()
    if choice != 'y':
        print("Setup cancelled")
        return
    
    success = setup_tenant()
    if success:
        print("Setup completed successfully! 🎉")
    else:
        print("Setup failed. Please check the errors above.")
        sys.exit(1)


if __name__ == "__main__":
    main()

