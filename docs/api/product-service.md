# Product Service

**Version**: 1.0.0
**Description**: Microservice for managing products

## Base URL
```
http://localhost:8002
```

## Endpoints

### `/products/health`

**GET** Health Check

Health check endpoint

**Responses:**

- `200`: Successful Response

---

### `/products`

**GET** Get Products

Get all products

**Responses:**

- `200`: Successful Response

---

### `/products/{product_id}`

**GET** Get Product

Get a specific product by ID

**Parameters:**

- `product_id` (path) (required): No description

**Responses:**

- `200`: Successful Response

- `422`: Validation Error

---

### `/products/category/{category}`

**GET** Get Products By Category

Get products by category

**Parameters:**

- `category` (path) (required): No description

**Responses:**

- `200`: Successful Response

- `422`: Validation Error

---
