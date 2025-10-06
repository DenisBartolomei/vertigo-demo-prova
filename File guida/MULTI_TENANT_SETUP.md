# Multi-Tenant User Management Setup Guide

This guide explains how to set up multiple credentials for different organizations (tenants) in the Vertigo AI recruitment system.

## 🏗️ System Architecture

The system now supports:
- **Multiple Tenants**: Each organization has its own isolated data
- **Multiple Users per Tenant**: Each tenant can have multiple HR users
- **Role-Based Access**: Admin and HR user roles with different permissions
- **Secure Authentication**: Password hashing and JWT tokens

## 🚀 Quick Setup

### Option 1: Using the Setup Script (Recommended)

1. **Run the setup script**:
   ```bash
   python setup_tenant.py
   ```

2. **Follow the interactive prompts**:
   - Enter company name
   - Enter admin full name
   - Enter admin email
   - Set admin password

3. **Save the credentials** provided by the script

### Option 2: Using the API Endpoint

1. **Create a tenant via API**:
   ```bash
   curl -X POST http://localhost:8000/auth/setup-tenant \
     -H "Content-Type: application/json" \
     -d '{
       "company_name": "Your Company",
       "admin_email": "admin@yourcompany.com",
       "admin_password": "secure_password",
       "admin_name": "Admin User"
     }'
   ```

2. **Use the returned token** to login immediately

## 👥 User Management

### Creating Additional Users

Once logged in as an admin:

1. **Navigate to "Gestione Utenti"** in the HR dashboard
2. **Click "Add New User"**
3. **Fill in the form**:
   - Email address
   - Full name
   - Role (HR User or Admin)
   - Password
4. **Click "Create User"**

### User Roles

- **Admin**: Can create/edit/delete users, full system access
- **HR User**: Can manage positions, sessions, and view reports

### Managing Users

- **View all users** in the "Gestione Utenti" page
- **Deactivate users** (only admins can do this)
- **Update user information** (users can update their own info)

## 🔐 Authentication Flow

### Login Process

1. **User enters credentials** on login page
2. **System authenticates** against user database
3. **JWT token generated** with tenant and user information
4. **User redirected** to appropriate dashboard

### Data Isolation

- **Tenant-specific collections**: Each tenant has separate MongoDB collections
- **User isolation**: Users can only access their tenant's data
- **Secure tokens**: JWT tokens include tenant information

## 📊 Database Structure

### Collections Created per Tenant

```
{tenant_id}_positions_data    # Job positions
{tenant_id}_sessions          # Interview sessions
{tenant_id}_interview_links   # Interview tokens
```

### Global Collections

```
tenants                       # Tenant information
users                         # All users across tenants
```

## 🛠️ Configuration

### Environment Variables

```bash
# Required
MONGO_CONNECTION_STRING=mongodb://...
JWT_SECRET=your-secret-key

# Optional
JWT_TTL_SECONDS=86400         # Token expiration (24 hours)
```

### Database Setup

The system automatically:
- Creates tenant collections when needed
- Sets up proper indexes
- Handles data isolation

## 🔧 API Endpoints

### Authentication
- `POST /auth/login` - User login
- `POST /auth/setup-tenant` - Create new tenant

### User Management
- `GET /users` - List users (tenant-specific)
- `POST /users` - Create user (admin only)
- `PUT /users/{user_id}` - Update user
- `POST /users/{user_id}/change-password` - Change password
- `DELETE /users/{user_id}` - Deactivate user (admin only)

## 🎯 Use Cases

### Scenario 1: Multiple Companies

Each company gets its own tenant:
- **Company A**: admin@companya.com
- **Company B**: admin@companyb.com
- **Company C**: admin@companyc.com

### Scenario 2: Multiple HR Teams

Within one company:
- **Admin**: admin@company.com (can manage users)
- **HR Manager**: hr.manager@company.com
- **HR Recruiter 1**: recruiter1@company.com
- **HR Recruiter 2**: recruiter2@company.com

### Scenario 3: Department Separation

Different departments with separate access:
- **HR Department**: hr@company.com
- **IT Department**: it@company.com
- **Management**: management@company.com

## 🔒 Security Features

### Password Security
- **PBKDF2 hashing** with salt
- **100,000 iterations** for key derivation
- **Secure random salts** for each password

### Token Security
- **JWT tokens** with expiration
- **Tenant isolation** in token payload
- **Role-based access** control

### Data Protection
- **Tenant isolation** at database level
- **User permission** checks on all operations
- **Soft delete** for user deactivation

## 🚨 Troubleshooting

### Common Issues

1. **"User already exists"**
   - Check if email is already registered
   - Use different email address

2. **"Invalid credentials"**
   - Verify email and password
   - Check if user is active

3. **"No tenant information"**
   - Ensure user has associated tenant
   - Check database connection

4. **"Permission denied"**
   - Verify user role (admin vs HR)
   - Check if user is trying to access other tenant's data

### Database Issues

1. **Connection problems**:
   ```bash
   # Check MongoDB connection
   python -c "from services.data_manager import db; print('Connected' if db else 'Failed')"
   ```

2. **Missing collections**:
   - Collections are created automatically
   - Check tenant setup was completed

## 📈 Monitoring

### User Activity
- **Last login tracking** for all users
- **Session management** with JWT expiration
- **Audit trail** for user actions

### System Health
- **Database connection** monitoring
- **Token validation** logging
- **Error tracking** for failed authentications

## 🔄 Migration from Single User

If you're upgrading from the single-user system:

1. **Backup existing data**
2. **Run tenant setup** for your organization
3. **Migrate existing data** to new tenant collections
4. **Update login credentials** to use new user system

## 📞 Support

For issues or questions:
1. Check the troubleshooting section above
2. Review the API documentation
3. Check system logs for error details
4. Ensure all environment variables are set correctly

---

**Note**: This system is designed for production use with proper security measures. Always use strong passwords and keep your JWT secret secure.
