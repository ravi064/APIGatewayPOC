# API Documentation Generation Guide

## Overview

FastAPI automatically generates OpenAPI (Swagger) specifications. We've created scripts to extract these specs and convert them to markdown documentation.

---

## Available Options

### Option 1: Use FastAPI's Built-in Interactive Docs (Easiest!)

FastAPI provides beautiful, interactive API documentation out of the box:

**Customer Service:**
- Swagger UI: http://localhost:8001/docs
- ReDoc: http://localhost:8001/redoc

**Product Service:**
- Swagger UI: http://localhost:8002/docs
- ReDoc: http://localhost:8002/redoc

**No installation needed!** Just start your services and visit these URLs.

---

### Option 2: Generate Markdown Files (Automated)

We've created three scripts to generate markdown documentation:

#### Python Script (Recommended - No Dependencies)

```bash
# Make sure services are running
docker-compose up -d

# Run the Python script
python scripts/generate-api-docs.py
```

**Pros:**
- [x] No additional dependencies (uses Python's built-in libraries + requests)
- [x] Works on Windows, Linux, Mac
- [x] Generates clean, readable markdown

**Output:**
- `docs/api/README.md` - API documentation index
- `docs/api/customer-service.md` - Customer API docs
- `docs/api/product-service.md` - Product API docs
- JSON OpenAPI specs

---

#### PowerShell Script (Windows)

```powershell
# Make sure services are running
docker-compose up -d

# Run PowerShell script
.\scripts\generate-api-docs.ps1
```

**Pros:**
- [x] Native Windows PowerShell
- [x] Can use widdershins if installed for better output
- [x] Falls back to basic markdown if widdershins not available

---

#### Bash Script (Linux/Mac)

```bash
# Make sure services are running
docker-compose up -d

# Run bash script
chmod +x scripts/generate-api-docs.sh
./scripts/generate-api-docs.sh
```

**Pros:**
- [x] Native Linux/Mac bash
- [x] Can use widdershins if installed for better output
- [x] Can use jq for basic markdown generation

---

### Option 3: Enhanced Output with Widdershins (Optional)

For richer markdown output, install widdershins:

```bash
npm install -g widdershins
```

Then run any of the scripts above. They'll automatically detect and use widdershins for better formatting.

---

## Quick Start

### 1. Start Your Services

```bash
docker-compose up -d
```

### 2. Generate Documentation

**Choose your preferred method:**

```bash
# Python (recommended)
python scripts/generate-api-docs.py

# PowerShell (Windows)
.\scripts\generate-api-docs.ps1

# Bash (Linux/Mac)
./scripts/generate-api-docs.sh
```

### 3. View Generated Documentation

```bash
# View the index
cat docs/api/README.md

# Or open in your editor
code docs/api/
```

---

## What Gets Generated

### docs/api/README.md
Index file with links to all API documentation and interactive docs.

### docs/api/customer-service.md
Markdown documentation for Customer Service API including:
- Base URL
- All endpoints (GET /customers, GET /customers/{id}, etc.)
- Parameters
- Request/Response schemas
- Status codes

### docs/api/product-service.md
Markdown documentation for Product Service API including:
- Base URL
- All endpoints (GET /products, GET /products/{id}, etc.)
- Parameters
- Request/Response schemas
- Status codes

### OpenAPI Specs (JSON)
- `customer-service-openapi.json` - Full OpenAPI 3.0 spec
- `product-service-openapi.json` - Full OpenAPI 3.0 spec

---

## Example Output

### Sample from customer-service.md:

```markdown
# Customer Service

**Version**: 1.0.0  
**Description**: Microservice for managing customers

## Base URL
```
http://localhost:8001
```

## Endpoints

### `/customers`

**GET** Get all customers

Get a list of all customers

**Responses:**
- `200`: Successful Response

---

### `/customers/{customer_id}`

**GET** Get a specific customer by ID

**Parameters:**
- `customer_id` (path) (required): Customer ID

**Responses:**
- `200`: Successful Response
- `404`: Customer not found
```

---

## Customization

### Update Service Metadata

Edit your FastAPI app configuration in `main.py`:

```python
app = FastAPI(
    title="Customer Service",
    description="Microservice for managing customer data",
    version="1.0.0",
    # Add more metadata
)
```

### Add Endpoint Documentation

Add docstrings and descriptions to your endpoints:

```python
@app.get("/customers/{customer_id}", 
         response_model=CustomerResponse,
  summary="Get customer by ID",
         description="Retrieve a specific customer by their unique ID")
def get_customer(customer_id: int):
    """
    Get a customer by ID.
    
  - **customer_id**: The unique identifier for the customer
    
  Returns the customer data if found, 404 otherwise.
"""
    # ...
```

The documentation will automatically include this information!

---

## Integration with Main Documentation

The generated files are placed in `docs/api/` which is already part of your documentation structure:

```
docs/
??? README.md
??? setup/
??? security/
??? development/
??? api/     # Generated API docs go here
    ??? README.md
    ??? customer-service.md
    ??? product-service.md
    ??? *.openapi.json
```

---

## Automated Generation

### Add to CI/CD Pipeline

You can automate documentation generation in your CI/CD:

```yaml
# GitHub Actions example
- name: Generate API Documentation
  run: |
    docker-compose up -d
  sleep 10  # Wait for services to be ready
    python scripts/generate-api-docs.py
    git add docs/api/
  git commit -m "docs: update API documentation" || true
```

### Pre-commit Hook

Or add to a pre-commit hook:

```bash
# .git/hooks/pre-commit
#!/bin/bash
python scripts/generate-api-docs.py
git add docs/api/
```

---

## Troubleshooting

### Services Not Running

**Error**: "Customer service is not running"

**Solution**:
```bash
docker-compose up -d
docker-compose logs customer-service
```

### Python Requests Module Missing

**Error**: "No module named 'requests'"

**Solution**:
```bash
pip install requests
```

### widdershins Not Found (Optional)

**Warning**: "widdershins not installed. Generating basic markdown..."

**Solution** (optional):
```bash
npm install -g widdershins
```

This is optional - the scripts work fine without it, just with simpler formatting.

---

## Comparison of Methods

| Method | Pros | Cons | Best For |
|--------|------|------|----------|
| **Built-in Swagger UI** | Interactive, automatic, beautiful | Browser-only | Development & testing |
| **Python Script** | Simple, no dependencies | Basic formatting | Quick markdown generation |
| **PowerShell/Bash** | Native shell integration | Requires Node.js for best output | Scripting & automation |
| **Widdershins** | Rich formatting, detailed | Requires Node.js | Production documentation |

---

## Recommendation

**For your POC:**

1. **Use Built-in Swagger UI** for development and testing
   - Visit http://localhost:8001/docs
- Interactive, always up-to-date

2. **Run Python script** when you need markdown files
   ```bash
   python scripts/generate-api-docs.py
   ```

3. **Optionally install widdershins** for richer output
   ```bash
   npm install -g widdershins
   ```

---

## Next Steps

1. **Try it now:**
   ```bash
   docker-compose up -d
   python scripts/generate-api-docs.py
   cat docs/api/README.md
   ```

2. **Enhance your endpoints** with better docstrings and descriptions

3. **Commit generated docs** to your repository

4. **Update main docs** to link to API documentation

---

**Generated**: October 2025  
**Scripts Location**: `scripts/generate-api-docs.*`  
**Output Location**: `docs/api/`

