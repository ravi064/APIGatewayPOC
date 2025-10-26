# Generate API Documentation from FastAPI OpenAPI specs
# This script fetches OpenAPI specs from running services and converts them to markdown

Write-Host "=== API Documentation Generator ===" -ForegroundColor Green
Write-Host ""

# Configuration
$CUSTOMER_SERVICE_URL = "http://localhost:8001"
$PRODUCT_SERVICE_URL = "http://localhost:8002"
$OUTPUT_DIR = "docs/api"

# Check if services are running
Write-Host "Checking if services are running..." -ForegroundColor Yellow

try {
    $customerHealth = Invoke-RestMethod -Uri "$CUSTOMER_SERVICE_URL/customers/health" -Method Get -TimeoutSec 5
    Write-Host "? Customer service is running" -ForegroundColor Green
} catch {
    Write-Host "? Customer service is not running. Please start it first." -ForegroundColor Red
    Write-Host "Run: docker-compose up -d customer-service" -ForegroundColor Yellow
    exit 1
}

try {
    $productHealth = Invoke-RestMethod -Uri "$PRODUCT_SERVICE_URL/products/health" -Method Get -TimeoutSec 5
  Write-Host "? Product service is running" -ForegroundColor Green
} catch {
    Write-Host "? Product service is not running. Please start it first." -ForegroundColor Red
    Write-Host "Run: docker-compose up -d product-service" -ForegroundColor Yellow
    exit 1
}

# Create output directory
Write-Host ""
Write-Host "Creating output directory..." -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path $OUTPUT_DIR | Out-Null

# Fetch OpenAPI specs
Write-Host ""
Write-Host "Fetching OpenAPI specifications..." -ForegroundColor Yellow

try {
    $customerSpec = Invoke-RestMethod -Uri "$CUSTOMER_SERVICE_URL/openapi.json" -Method Get
    $customerSpec | ConvertTo-Json -Depth 100 | Out-File "$OUTPUT_DIR/customer-service-openapi.json"
    Write-Host "? Customer service OpenAPI spec saved" -ForegroundColor Green
} catch {
    Write-Host "? Failed to fetch customer service OpenAPI spec" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
 exit 1
}

try {
    $productSpec = Invoke-RestMethod -Uri "$PRODUCT_SERVICE_URL/openapi.json" -Method Get
    $productSpec | ConvertTo-Json -Depth 100 | Out-File "$OUTPUT_DIR/product-service-openapi.json"
    Write-Host "? Product service OpenAPI spec saved" -ForegroundColor Green
} catch {
    Write-Host "? Failed to fetch product service OpenAPI spec" -ForegroundColor Red
 Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}

# Generate markdown documentation
Write-Host ""
Write-Host "Generating markdown documentation..." -ForegroundColor Yellow

# Check if widdershins is installed
$widdershinsInstalled = $null -ne (Get-Command widdershins -ErrorAction SilentlyContinue)

if ($widdershinsInstalled) {
    # Use widdershins to generate markdown
 widdershins "$OUTPUT_DIR/customer-service-openapi.json" -o "$OUTPUT_DIR/customer-service.md"
    Write-Host "? Customer service markdown generated using widdershins" -ForegroundColor Green
    
    widdershins "$OUTPUT_DIR/product-service-openapi.json" -o "$OUTPUT_DIR/product-service.md"
    Write-Host "? Product service markdown generated using widdershins" -ForegroundColor Green
} else {
    Write-Host "? widdershins not installed. Generating basic markdown..." -ForegroundColor Yellow
    
    # Generate basic markdown from the spec
    $customerMd = @"
# Customer Service API

**Version**: $($customerSpec.info.version)  
**Description**: $($customerSpec.info.description)

## Base URL
``````
$CUSTOMER_SERVICE_URL
``````

## Endpoints

"@

    foreach ($path in $customerSpec.paths.PSObject.Properties) {
     $customerMd += "`n### $($path.Name)`n`n"
        foreach ($method in $path.Value.PSObject.Properties) {
    $operation = $method.Value
            $customerMd += "**$($method.Name.ToUpper())**`n`n"
    if ($operation.summary) {
              $customerMd += "$($operation.summary)`n`n"
    }
            if ($operation.description) {
                $customerMd += "$($operation.description)`n`n"
            }
        }
    }

    $customerMd | Out-File "$OUTPUT_DIR/customer-service.md"
    Write-Host "? Basic customer service markdown generated" -ForegroundColor Green
    
    # Similar for product service
    $productMd = @"
# Product Service API

**Version**: $($productSpec.info.version)
**Description**: $($productSpec.info.description)

## Base URL
``````
$PRODUCT_SERVICE_URL
``````

## Endpoints

"@

    foreach ($path in $productSpec.paths.PSObject.Properties) {
$productMd += "`n### $($path.Name)`n`n"
        foreach ($method in $path.Value.PSObject.Properties) {
      $operation = $method.Value
     $productMd += "**$($method.Name.ToUpper())**`n`n"
            if ($operation.summary) {
            $productMd += "$($operation.summary)`n`n"
            }
            if ($operation.description) {
          $productMd += "$($operation.description)`n`n"
}
        }
    }

    $productMd | Out-File "$OUTPUT_DIR/product-service.md"
    Write-Host "? Basic product service markdown generated" -ForegroundColor Green
}

# Create index file
$indexContent = @"
# API Documentation

Auto-generated API documentation for all microservices.

## Services

### Customer Service
- [Customer Service API Documentation](customer-service.md)
- [OpenAPI Spec (JSON)](customer-service-openapi.json)
- Interactive Docs: http://localhost:8001/docs
- ReDoc: http://localhost:8001/redoc

### Product Service
- [Product Service API Documentation](product-service.md)
- [OpenAPI Spec (JSON)](product-service-openapi.json)
- Interactive Docs: http://localhost:8002/docs
- ReDoc: http://localhost:8002/redoc

## Authentication

All endpoints require JWT authentication. See [Security Guide](../security/security-guide.md) for details.

### Getting a Token

``````bash
curl -X POST http://localhost:8180/realms/api-gateway-poc/protocol/openid-connect/token \
  -d "client_id=test-client" \
  -d "username=testuser" \
  -d "password=testpass" \
  -d "grant_type=password"
``````

### Using a Token

``````bash
curl -H "Authorization: Bearer <TOKEN>" http://localhost:8080/customers
``````

---

**Last Updated**: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")  
**Generated by**: generate-api-docs.ps1

**Note**: For better markdown output, install widdershins:
``````bash
npm install -g widdershins
``````
"@

$indexContent | Out-File "$OUTPUT_DIR/README.md"
Write-Host "? API documentation index created" -ForegroundColor Green

# Summary
Write-Host ""
Write-Host "=== Documentation Generated Successfully ===" -ForegroundColor Green
Write-Host ""
Write-Host "Generated files:" -ForegroundColor Yellow
Write-Host "  - $OUTPUT_DIR/README.md"
Write-Host "  - $OUTPUT_DIR/customer-service.md"
Write-Host "  - $OUTPUT_DIR/customer-service-openapi.json"
Write-Host "  - $OUTPUT_DIR/product-service.md"
Write-Host "  - $OUTPUT_DIR/product-service-openapi.json"
Write-Host ""
Write-Host "View documentation: cat $OUTPUT_DIR/README.md" -ForegroundColor Cyan
Write-Host ""
Write-Host "For better markdown output, install widdershins:" -ForegroundColor Yellow
Write-Host "  npm install -g widdershins" -ForegroundColor Cyan
Write-Host ""
