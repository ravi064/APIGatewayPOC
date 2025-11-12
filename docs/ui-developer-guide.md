# UI Developer Guide

Quick reference for React/frontend developers integrating with the API Gateway.

## Authentication Overview

Your React app authenticates users via Keycloak and fetches roles from the authorization service:

```
React → Keycloak (login) → JWT Token → /auth/me → User Roles
```

**Key Points:**
- Keycloak handles authentication (username/password → JWT)
- Roles are NOT in JWT (IT policy restriction)
- Call `/auth/me` to get user email and roles
- **Backend always validates permissions** (client checks are UX only)

## Quick Start

> :memo: **NOTE:** The following code is provided as an example only.
>
> Understand security implications before adopting this code for production.

### 1. Login Flow

```javascript
async function login(username, password) {
  const response = await fetch('http://localhost:8080/auth/realms/api-gateway-poc/protocol/openid-connect/token', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({
      client_id: 'test-client',
      username,
      password,
      grant_type: 'password',
    }),
  });

  const data = await response.json();
  localStorage.setItem('access_token', data.access_token);
  localStorage.setItem('refresh_token', data.refresh_token);
  
  return data.access_token;
}
```

### 2. Fetch User Roles

```javascript
async function fetchUserRoles() {
  const token = localStorage.getItem('access_token');
  
  const response = await fetch('http://localhost:8080/auth/me', {
    headers: { 'Authorization': `Bearer ${token}` },
  });

  if (!response.ok) {
    if (response.status === 401) {
      // Token expired - redirect to login
      window.location.href = '/login';
      return null;
    }
    throw new Error('Failed to fetch roles');
  }

  return await response.json();
  // Returns: { email: "user@example.com", roles: ["user", "customer-manager"] }
}
```

### 3. Create Auth Context

```javascript
import { createContext, useState, useEffect, useContext } from 'react';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadUser();
  }, []);

  async function loadUser() {
    try {
      const token = localStorage.getItem('access_token');
      if (token) {
        const userData = await fetchUserRoles();
        setUser(userData);
      }
    } catch (error) {
      console.error('Failed to load user:', error);
    } finally {
      setLoading(false);
    }
  }

  function logout() {
    localStorage.clear();
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ user, loading, logout, refreshUser: loadUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
```

### 4. Use Roles in Components

```javascript
import { useAuth } from './AuthContext';

function CustomerManagement() {
  const { user } = useAuth();

  if (!user?.roles.includes('customer-manager')) {
    return <div>Access Denied</div>;
  }

  return <div>Customer Management UI</div>;
}
```

### 5. Protected Routes

```javascript
import { Navigate } from 'react-router-dom';
import { useAuth } from './AuthContext';

function ProtectedRoute({ children, requiredRoles = [] }) {
  const { user, loading } = useAuth();

  if (loading) return <div>Loading...</div>;
  if (!user) return <Navigate to="/login" />;
  
  const hasRole = requiredRoles.length === 0 || 
    requiredRoles.some(role => user.roles.includes(role));
  
  return hasRole ? children : <div>Access Denied</div>;
}

// Usage
<Route path="/customers" element={
  <ProtectedRoute requiredRoles={['user', 'customer-manager']}>
    <CustomerPage />
  </ProtectedRoute>
} />
```

## Available Roles

| Role | Description |
|------|-------------|
| `guest` | No JWT token |
| `unverified-user` | Authenticated. Given 'unverified-user' role |
| `user` | Basic access |
| `customer-manager` | Customer management |
| `product-manager` | Product management |

> :memo: **NOTE:** Role progression is from *guest -> unverified-user -> user*.
>
> After gaining *user* role, the given user can have multiple roles but not *guest* or *unverified-user*

## API Endpoints

### `/auth/me` - Get Current User

**Request:**
```
GET /auth/me
Authorization: Bearer <jwt-token>
```

**Response (200):**
```json
{
  "email": "user@example.com",
  "roles": ["user", "customer-manager"]
}
```

**Response (401):**
```json
{
  "detail": "No authorization token provided"
}
```

### Business APIs

The following require JWT token in `Authorization: Bearer <token>` header:

```
GET  /customers          - List customers
GET  /customers/{id}     - Get customer
```

The following will work with or without JWT token in the header:

```
GET  /products           - List products
GET  /products/{id}      - Get product
```

## Token Management

### Token Refresh

Tokens expire in 5 minutes. Refresh before expiration:

```javascript
async function refreshToken() {
  const refreshToken = localStorage.getItem('refresh_token');
  
  const response = await fetch('http://localhost:8080/auth/realms/api-gateway-poc/protocol/openid-connect/token', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({
      client_id: 'test-client',
      grant_type: 'refresh_token',
      refresh_token: refreshToken,
    }),
  });

  const data = await response.json();
  localStorage.setItem('access_token', data.access_token);
}
```

### Auto-Refresh Pattern

```javascript
useEffect(() => {
  const interval = setInterval(() => refreshToken(), 4 * 60 * 1000); // Every 4 min
  return () => clearInterval(interval);
}, []);
```

## Security Best Practices

1. **Client-side checks are UX only** - Backend always validates
2. **Store tokens in localStorage** - Or sessionStorage for more security
3. **Clear tokens on logout** - `localStorage.clear()`
4. **Handle 401 responses** - Redirect to login
5. **Refresh tokens before expiry** - Avoid interrupting user flow

## Common Errors

**401 Unauthorized:**
- Token missing or expired
- Redirect to login

**403 Forbidden:**
- User lacks required role
- Show access denied message

**CORS errors:**
- Ensure React and API are on same origin
- Or configure CORS in Envoy

## Testing

### Manual Test

```bash
# Get token
TOKEN=$(curl -s -X POST http://localhost:8080/auth/realms/api-gateway-poc/protocol/openid-connect/token \
  -d "client_id=test-client&username=testuser&password=testpass&grant_type=password" \
  | jq -r '.access_token')

# Test /auth/me
curl -H "Authorization: Bearer $TOKEN" http://localhost:8080/auth/me

# Test business API
curl -H "Authorization: Bearer $TOKEN" http://localhost:8080/customers
```

### Integration Tests

```javascript
// Example with jest + react-testing-library
test('shows customer management for customer-manager role', async () => {
  const mockUser = {
    email: 'manager@example.com',
    roles: ['user', 'customer-manager']
  };
  
  render(
    <AuthContext.Provider value={{ user: mockUser }}>
      <CustomerManagement />
    </AuthContext.Provider>
  );
  
  expect(screen.getByText('Customer Management UI')).toBeInTheDocument();
});
```

## Additional Resources

- [React Auth Integration](development/react-auth-integration.md) - Detailed examples
- [Security Quick Start](security/security-quick-start.md) - Authentication basics
- [API Documentation](api/README.md) - Full API reference

## Quick Reference

```javascript
// Login
const token = await login(username, password);

// Get user roles
const user = await fetchUserRoles();

// Use in component
const { user } = useAuth();
const canManage = user?.roles.includes('customer-manager');

// Make API call
const response = await fetch('/customers', {
  headers: { 'Authorization': `Bearer ${token}` }
});

// Logout
localStorage.clear();
window.location.href = '/login';
```

---

**Need help?** Check [React Auth Integration](development/react-auth-integration.md) for complete examples.
