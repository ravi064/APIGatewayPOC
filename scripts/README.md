# Scripts Directory

This directory contains utility scripts for managing the APIGatewayPOC project.

---

## Available Scripts

### 1. generate-api-docs.sh / generate-api-docs.ps1
**Purpose:** Generate markdown API documentation from FastAPI OpenAPI specs

**Requirements:**
- Bash/PowerShell
- curl (bash version)
- Services must be running
- Optional: widdershins for better output (`npm install -g widdershins`)
- Optional: jq for bash basic output (bash version)

**Usage:**
```bash
# Linux/Mac
chmod +x scripts/generate-api-docs.sh
./scripts/generate-api-docs.sh

# Windows
.\scripts\generate-api-docs.ps1
```

**What it does:**
- Fetches OpenAPI specs from running services
- Converts specs to markdown documentation
- Creates API documentation index
- Saves to `docs/api/` directory

**Output:**
- `docs/api/README.md` - API documentation index
- `docs/api/customer-service.md` - Customer API docs
- `docs/api/customer-service-openapi.json` - Customer OpenAPI spec
- `docs/api/product-service.md` - Product API docs
- `docs/api/product-service-openapi.json` - Product OpenAPI spec

---

### 2. rotate-secrets.sh (Linux/Mac)
**Purpose:** Rotate Keycloak client secrets

**Requirements:**
- Bash shell
- curl
- jq (JSON processor)

**Usage:**
```bash
chmod +x scripts/rotate-secrets.sh
./scripts/rotate-secrets.sh
```

**Features:**
- Interactive menu
- Rotate individual client secrets
- Rotate all client secrets at once
- Generate secure random secrets
- Automatically updates secrets via Keycloak Admin API

**Menu Options:**
1. Rotate api-gateway secret
2. Rotate customer-service secret
3. Rotate product-service secret
4. Rotate ALL confidential client secrets
5. Generate secure secret (display only)
6. Exit

**Example Output:**
```
=== New Secret ===
Client: api-gateway
Secret: a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6

IMPORTANT: Save this secret! Update your environment variables:
API_GATEWAY_CLIENT_SECRET=a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6
```

---

### 3. rotate-secrets.ps1 (Windows)
**Purpose:** Rotate Keycloak client secrets (PowerShell version)

**Requirements:**
- PowerShell 5.1 or higher
- Internet connection to Keycloak

**Usage:**
```powershell
.\scripts\rotate-secrets.ps1
```

**Optional Parameters:**
```powershell
# Custom Keycloak URL
.\scripts\rotate-secrets.ps1 -KeycloakUrl "http://localhost:8180"

# Custom realm
.\scripts\rotate-secrets.ps1 -Realm "api-gateway-poc"

# Custom admin credentials
.\scripts\rotate-secrets.ps1 -AdminUser "admin" -AdminPassword "admin"
```

**Features:**
- Same functionality as bash version
- Works on Windows without WSL
- Interactive menu
- Secure secret generation using .NET crypto libraries

---

### 4. setup.sh (Project Setup)
**Purpose:** Initial project setup

**Usage:**
```bash
./scripts/setup.sh
```

**What it does:**
- Installs dependencies
- Creates necessary directories
- Sets up environment

---

### 5. start.sh (Start Services)
**Purpose:** Start all services

**Usage:**
```bash
./scripts/start.sh
```

**What it does:**
- Builds Docker images
- Starts all services via docker-compose
- Shows service status

---

### 6. stop.sh (Stop Services)
**Purpose:** Stop all services

**Usage:**
```bash
./scripts/stop.sh
```

**What it does:**
- Stops all running containers
- Removes containers and networks

---

### 7. test.sh (Run Tests)
**Purpose:** Run integration tests

**Usage:**
```bash
./scripts/test.sh
```

**What it does:**
- Runs pytest test suite
- Displays test results

---

### 8. validate_project.py (Project Validation)
**Purpose:** Validate project structure and configuration

**Requirements:**
- Python 3.x
- Docker (for docker-compose validation)

**Usage:**
```bash
# From project root
python scripts/validate_project.py
```

**What it does:**
- Validates all required files exist
- Checks Docker configuration syntax
- Verifies .gitignore patterns
- Reports missing files or configuration issues

**Example Output:**
```
============================================================
PROJECT STRUCTURE VALIDATION
============================================================
[OK] README.md
[OK] docker-compose.yml
[OK] .gitignore
...
============================================================
VALIDATION SUMMARY
============================================================
Successful checks: 42
VALIDATION PASSED - All required files are present and configured correctly!
```

---

### 9. generate-api-docs.py (API Documentation Generator)
**Purpose:** Generate markdown API documentation from FastAPI OpenAPI specs

**Requirements:**
- Python 3.x
- requests library (`pip install requests`)
- Services must be running

**Usage:**
```bash
# Make sure services are running
docker-compose up -d

# Generate API documentation
python scripts/generate-api-docs.py
```

**What it does:**
- Fetches OpenAPI specs from running FastAPI services
- Generates markdown documentation
- Creates API documentation index
- Saves files to `docs/api/` directory

**Output:**
- `docs/api/README.md` - API documentation index
- `docs/api/customer-service.md` - Customer API docs
- `docs/api/product-service.md` - Product API docs
- OpenAPI JSON specs

---

## Secret Rotation Workflow

### When to Rotate Secrets

1. **Regular schedule** (e.g., every 90 days)
2. **After suspected compromise**
3. **When employee leaves** (if they had access)
4. **Before production deployment** (change defaults)

### How to Rotate

#### Step 1: Run Rotation Script
```bash
# Linux/Mac
./scripts/rotate-secrets.sh

# Windows
.\scripts\rotate-secrets.ps1
```

#### Step 2: Save New Secrets
Copy the output to your `.env` file:
```env
API_GATEWAY_CLIENT_SECRET=new-secret-here
CUSTOMER_SERVICE_CLIENT_SECRET=new-secret-here
PRODUCT_SERVICE_CLIENT_SECRET=new-secret-here
```

#### Step 3: Update Services
```bash
# Restart services to pick up new secrets
docker-compose restart
```

#### Step 4: Verify
```bash
# Test authentication with new secret
curl -X POST http://localhost:8180/realms/api-gateway-poc/protocol/openid-connect/token \
  -d "client_id=api-gateway" \
  -d "client_secret=NEW_SECRET_HERE" \
  -d "grant_type=client_credentials"
```

#### Step 5: Document
- Record rotation date
- Update secret management system
- Notify team if needed

---

## Security Best Practices

### For Development

**DO:**
- Use rotation scripts to generate secure secrets
- Test secret rotation process
- Keep .env file in .gitignore
- Use test-client for quick testing

**DON'T:**
- Commit secrets to git
- Share secrets in chat/email
- Use weak/predictable secrets
- Reuse secrets across environments

### For Production

**DO:**
- Use secrets manager (Azure Key Vault, AWS Secrets Manager, etc.)
- Rotate secrets regularly
- Use different secrets for each environment
- Audit secret access
- Implement secrets rotation policy
- Use strong, random secrets (32+ characters)

**DON'T:**
- Use default/example secrets
- Store secrets in plain text files
- Share production secrets
- Allow test-client in production

---

## Troubleshooting

### Issue: Script can't connect to Keycloak
**Error:** "Failed to get admin token"

**Solutions:**
1. Verify Keycloak is running:
   ```bash
   docker-compose ps keycloak
   ```

2. Check Keycloak URL:
   ```bash
   curl http://localhost:8180/health/ready
   ```

3. Verify admin credentials are correct

---

### Issue: jq command not found (Linux/Mac)
**Error:** "jq: command not found"

**Solutions:**
```bash
# Ubuntu/Debian
sudo apt-get install jq

# macOS
brew install jq

# CentOS/RHEL
sudo yum install jq
```

---

### Issue: PowerShell execution policy (Windows)
**Error:** "cannot be loaded because running scripts is disabled"

**Solutions:**
```powershell
# Check current policy
Get-ExecutionPolicy

# Set policy (as Administrator)
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

---

### Issue: Secret rotation fails
**Error:** "Failed to update secret"

**Solutions:**
1. Check that client exists:
   - Login to Admin Console (http://localhost:8180)
   - Navigate to Clients
   - Verify client is present

2. Check permissions:
   - Verify admin user has realm-admin role
   - Check user has permissions to manage clients

3. Check API access:
   ```bash
   # Get admin token
   curl -X POST http://localhost:8180/realms/master/protocol/openid-connect/token \
     -d "username=admin" \
     -d "password=admin" \
     -d "grant_type=password" \
     -d "client_id=admin-cli"
   ```

---

## Manual Secret Rotation (Alternative)

If scripts don't work, rotate manually:

### Via Keycloak Admin Console

1. Login to Admin Console (http://localhost:8180)
2. Select realm: `api-gateway-poc`
3. Navigate to: Clients
4. Click on client (e.g., `api-gateway`)
5. Go to: Credentials tab
6. Click: Regenerate Secret
7. Copy new secret
8. Update .env file
9. Restart services

### Via Keycloak CLI

```bash
# Enter Keycloak container
docker-compose exec keycloak bash

# Set admin credentials
export KEYCLOAK_URL=http://localhost:8080
export KEYCLOAK_REALM=master
export KEYCLOAK_USER=admin
export KEYCLOAK_PASSWORD=admin

# Login
/opt/keycloak/bin/kcadm.sh config credentials \
  --server $KEYCLOAK_URL \
  --realm $KEYCLOAK_REALM \
  --user $KEYCLOAK_USER \
  --password $KEYCLOAK_PASSWORD

# Generate new secret
NEW_SECRET=$(openssl rand -base64 32 | tr -d "=+/")

# Update client
/opt/keycloak/bin/kcadm.sh update clients/<CLIENT_UUID> \
  -r api-gateway-poc \
  -s "secret=$NEW_SECRET"
```

---

## Environment Variables

Scripts use these environment variables (with defaults):

| Variable | Default | Description |
|----------|---------|-------------|
| `KEYCLOAK_URL` | `http://localhost:8180` | Keycloak base URL |
| `REALM` | `api-gateway-poc` | Keycloak realm name |
| `ADMIN_USER` | `admin` | Admin username |
| `ADMIN_PASSWORD` | `admin` | Admin password |

**Override example:**
```bash
# Linux/Mac
export KEYCLOAK_URL=http://keycloak.example.com
./scripts/rotate-secrets.sh

# Windows
$env:KEYCLOAK_URL="http://keycloak.example.com"
.\scripts\rotate-secrets.ps1
```

---

## Adding New Scripts

When adding new scripts:

1. **Create script file:**
   ```bash
   touch scripts/my-new-script.sh
   chmod +x scripts/my-new-script.sh
   ```

2. **Add shebang:**
   ```bash
   #!/bin/bash
   set -e  # Exit on error
   ```

3. **Document it here** in this README

4. **Test thoroughly**

5. **Create Windows version** if needed (.ps1)

---

## Resources
- [Security Guide](../docs/security/security-guide.md) - Complete security documentation
- [Keycloak Setup](../docs/setup/keycloak-setup.md) - Keycloak setup guide

---

## Contributing

When contributing scripts:
- Follow existing patterns
- Add error handling
- Add helpful output messages
- Test on both Linux and Windows (if applicable)
- Update this README
- Add examples

---

*Last updated: 27 October, 2025*
*Maintained by: Development Team*
