# Customer Service

**Version**: 1.0.0
**Description**: Microservice for managing customers

## Base URL
```
http://localhost:8001
```

## Endpoints

### `/customers/health`

**GET** Health Check

Health check endpoint

**Responses:**

- `200`: Successful Response

---

### `/customers`

**GET** Get Customers

Get all customers

**Responses:**

- `200`: Successful Response

---

### `/customers/{customer_id}`

**GET** Get Customer

Get a specific customer by ID

**Parameters:**

- `customer_id` (path) (required): No description

**Responses:**

- `200`: Successful Response

- `422`: Validation Error

---
