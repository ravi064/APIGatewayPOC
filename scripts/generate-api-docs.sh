#!/bin/bash

# Generate API Documentation from FastAPI OpenAPI specs
# This script fetches OpenAPI specs from running services and converts them to markdown

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== API Documentation Generator ===${NC}"
echo ""

# Configuration
CUSTOMER_SERVICE_URL="${CUSTOMER_SERVICE_URL:-http://localhost:8001}"
PRODUCT_SERVICE_URL="${PRODUCT_SERVICE_URL:-http://localhost:8002}"
OUTPUT_DIR="docs/api"

# Check if services are running
echo -e "${YELLOW}Checking if services are running...${NC}"

if curl -s -f "${CUSTOMER_SERVICE_URL}/customers/health" > /dev/null; then
    echo -e "${GREEN}? Customer service is running${NC}"
else
    echo -e "${RED}? Customer service is not running. Please start it first.${NC}"
    echo -e "${YELLOW}Run: docker-compose up -d customer-service${NC}"
    exit 1
fi

if curl -s -f "${PRODUCT_SERVICE_URL}/products/health" > /dev/null; then
    echo -e "${GREEN}? Product service is running${NC}"
else
    echo -e "${RED}? Product service is not running. Please start it first.${NC}"
    echo -e "${YELLOW}Run: docker-compose up -d product-service${NC}"
    exit 1
fi

# Create output directory
echo ""
echo -e "${YELLOW}Creating output directory...${NC}"
mkdir -p "$OUTPUT_DIR"

# Fetch OpenAPI specs
echo ""
echo -e "${YELLOW}Fetching OpenAPI specifications...${NC}"

if curl -s -f "${CUSTOMER_SERVICE_URL}/openapi.json" -o "$OUTPUT_DIR/customer-service-openapi.json"; then
    echo -e "${GREEN}? Customer service OpenAPI spec saved${NC}"
else
    echo -e "${RED}? Failed to fetch customer service OpenAPI spec${NC}"
    exit 1
fi

if curl -s -f "${PRODUCT_SERVICE_URL}/openapi.json" -o "$OUTPUT_DIR/product-service-openapi.json"; then
    echo -e "${GREEN}? Product service OpenAPI spec saved${NC}"
else
    echo -e "${RED}? Failed to fetch product service OpenAPI spec${NC}"
    exit 1
fi

# Generate markdown documentation
echo ""
echo -e "${YELLOW}Generating markdown documentation...${NC}"

# Check if widdershins is installed
if command -v widdershins &> /dev/null; then
    # Use widdershins to generate markdown
    widdershins "$OUTPUT_DIR/customer-service-openapi.json" -o "$OUTPUT_DIR/customer-service.md"
    echo -e "${GREEN}? Customer service markdown generated using widdershins${NC}"
    
    widdershins "$OUTPUT_DIR/product-service-openapi.json" -o "$OUTPUT_DIR/product-service.md"
    echo -e "${GREEN}? Product service markdown generated using widdershins${NC}"
else
    echo -e "${YELLOW}? widdershins not installed. Generating basic markdown...${NC}"
    
  # Generate basic markdown using jq
  if command -v jq &> /dev/null; then
        # Customer Service
        cat > "$OUTPUT_DIR/customer-service.md" <<EOF
# Customer Service API

**Version**: $(jq -r '.info.version' "$OUTPUT_DIR/customer-service-openapi.json")  
**Description**: $(jq -r '.info.description' "$OUTPUT_DIR/customer-service-openapi.json")

## Base URL
\`\`\`
$CUSTOMER_SERVICE_URL
\`\`\`

## Endpoints

EOF
      
        jq -r '.paths | to_entries[] | "### \(.key)\n\n" + (.value | to_entries[] | "**\(.key | ascii_upcase)**\n\n\(.value.summary // "")\n\n\(.value.description // "")\n\n")' \
"$OUTPUT_DIR/customer-service-openapi.json" >> "$OUTPUT_DIR/customer-service.md"
        
     echo -e "${GREEN}? Customer service markdown generated${NC}"
      
   # Product Service
        cat > "$OUTPUT_DIR/product-service.md" <<EOF
# Product Service API

**Version**: $(jq -r '.info.version' "$OUTPUT_DIR/product-service-openapi.json")  
**Description**: $(jq -r '.info.description' "$OUTPUT_DIR/product-service-openapi.json")

## Base URL
\`\`\`
$PRODUCT_SERVICE_URL
\`\`\`

## Endpoints

EOF
        
        jq -r '.paths | to_entries[] | "### \(.key)\n\n" + (.value | to_entries[] | "**\(.key | ascii_upcase)**\n\n\(.value.summary // "")\n\n\(.value.description // "")\n\n")' \
            "$OUTPUT_DIR/product-service-openapi.json" >> "$OUTPUT_DIR/product-service.md"
        
     echo -e "${GREEN}? Product service markdown generated${NC}"
    else
        echo -e "${RED}? jq not installed. Cannot generate markdown.${NC}"
        echo -e "${YELLOW}Install jq or widdershins to generate markdown documentation.${NC}"
        exit 1
    fi
fi

# Create index file
cat > "$OUTPUT_DIR/README.md" <<EOF
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

\`\`\`bash
curl -X POST http://localhost:8180/realms/api-gateway-poc/protocol/openid-connect/token \\
  -d "client_id=test-client" \\
  -d "username=testuser" \\
  -d "password=testpass" \\
  -d "grant_type=password"
\`\`\`

### Using a Token

\`\`\`bash
curl -H "Authorization: Bearer <TOKEN>" http://localhost:8080/customers
\`\`\`

---

**Last Updated**: $(date)  
**Generated by**: generate-api-docs.sh

**Note**: For better markdown output, install widdershins:
\`\`\`bash
npm install -g widdershins
\`\`\`
EOF

echo -e "${GREEN}? API documentation index created${NC}"

# Summary
echo ""
echo -e "${GREEN}=== Documentation Generated Successfully ===${NC}"
echo ""
echo -e "${YELLOW}Generated files:${NC}"
echo "  - $OUTPUT_DIR/README.md"
echo "  - $OUTPUT_DIR/customer-service.md"
echo "  - $OUTPUT_DIR/customer-service-openapi.json"
echo "  - $OUTPUT_DIR/product-service.md"
echo "  - $OUTPUT_DIR/product-service-openapi.json"
echo ""
echo -e "${CYAN}View documentation: cat $OUTPUT_DIR/README.md${NC}"
echo ""
echo -e "${YELLOW}For better markdown output, install widdershins:${NC}"
echo -e "${CYAN}npm install -g widdershins${NC}"
echo ""
