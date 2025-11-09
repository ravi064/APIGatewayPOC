# System Architecture Overview

This document provides a high-level view of the API Gateway POC system architecture, showing the major components, their relationships, and key technical details.

## Architecture Diagram (High Level)

```mermaid
graph LR
    Client[Client/React UI]
    Gateway[API Gateway - Envoy:8080]
    Keycloak[Keycloak:8180]
    AuthZ[Authorization Service:9000]
    Customer[Customer Service:8001]
    Product[Product Service:8002]
    
    Client -->|1. Login| Keycloak
    Keycloak -->|2. JWT Token| Client
    Client -->|3. Get User Info /auth/me| Gateway
    Gateway -->|Validate JWT| Keycloak
    Gateway -->|Role Lookup| AuthZ
    Gateway -->|Route /auth/me| AuthZ
    Gateway -->|Route /customers| Customer
    Gateway -->|Route /products| Product
    
    classDef clientStyle fill:#e3f2fd,stroke:#1976d2,stroke-width:2px
    classDef gatewayStyle fill:#e1f5fe,stroke:#0277bd,stroke-width:3px
    classDef authStyle fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px
    classDef serviceStyle fill:#e8f5e8,stroke:#2e7d32,stroke-width:2px
    
    class Client clientStyle
    class Gateway gatewayStyle
    class Keycloak,AuthZ authStyle
    class Customer,Product serviceStyle
```

## Architecture Diagram (Detailed)

```mermaid
graph TB
    %% External Users
    User[**Client/User** - Web Browser, Mobile App, API Client]
    
    %% External Internet
    Internet[**Internet** - External Network]
    
    %% API Gateway Layer
    subgraph "**API Gateway Layer**"
        Envoy[**Envoy** Proxy - API Gateway - Port 8080 API - Port 9901 Admin - JWT Validation & Routing - External Authorization]
    end
    
    %% Authentication & Authorization Layer
    subgraph "**Identity & Access Management**"
        Keycloak[**Keycloak** - Identity Provider - Port 8180 - OAuth 2.0 / OpenID Connect - JWT Token Issuance]
        AuthZService[**Authorization Service** - Role Lookup - Port 9000 - ext_authz Integration - Redis Caching]
    end

    %% Caching Layer
    subgraph "**Caching Layer**"
        Redis[**Redis** - Role Cache - Port 6379 - 5-minute TTL - LRU Eviction]
    end

    %% Microservices Layer
    subgraph "**Microservices Layer**"
        subgraph "**Customer Domain**"
            CustomerAPI[**Customer Service** - FastAPI Application - Port 8001 - RBAC Authorization - Customer Data Management]
            CustomerData[**Customer Data Access** - Mock Database Layer - Business Logic - Future: PostgreSQL]
        end      
        subgraph "**Product Domain**"
            ProductAPI[**Product Service** - FastAPI Application - Port 8002 - Product Catalog - Category Management]
            ProductData[**Product Data Access** - Mock Database Layer - Business Logic - Future: PostgreSQL]
        end
        subgraph "**Authorization Domain**"
            AuthZData[**AuthZ Data Access** - User Role Database - Mock Layer - Future: PostgreSQL]
        end
    end
    
    %% Shared Infrastructure
    subgraph "**Shared Infrastructure**"
        AuthModule[**JWT Auth Module** - shared/auth.py - Token Validation - User Context Extraction]
        CommonUtils[**Common Utilities** - shared/common.py - Logging, Health Checks - Error Handling]
    end
    
    %% Network
    subgraph "**Container Network**"
        Network[**Docker Bridge Network** - microservices-network - Internal Service Discovery]
    end
    
    %% Data Flow Connections
    User -->|HTTPS Requests with Bearer Token| Internet
    Internet -->|Port 8080| Envoy
    
    %% Authentication Flow
    User -.->|1. Login Request POST /token| Keycloak
    Keycloak -.->|2. JWT Token| User
    
    %% Authorization Flow
    Envoy -->|JWT Validation| Keycloak
    Envoy -->|ext_authz Role Check| AuthZService
    AuthZService -->|Cache Lookup| Redis
    AuthZService -->|DB Query on Cache Miss| AuthZData
    
    %% API Gateway Routing
    Envoy -->|/customers/* Authorized Requests| CustomerAPI
    Envoy -->|/products/* Authorized Requests| ProductAPI
    Envoy -->|/auth/me User Info| AuthZService

    %% Service Internal Flow
    CustomerAPI --> AuthModule
    CustomerAPI --> CustomerData
    CustomerAPI --> CommonUtils
    
    ProductAPI --> AuthModule
    ProductAPI --> ProductData
    ProductAPI --> CommonUtils
    
    AuthZService --> CommonUtils
    
    %% Network Connections
    Envoy -.-> Network
    CustomerAPI -.-> Network
    ProductAPI -.-> Network
    AuthZService -.-> Network
    Redis -.-> Network
    Keycloak -.-> Network
    
    %% Admin Access
    User -.->|Admin Console Port 8180| Keycloak
    User -.->|Envoy Admin Port 9901| Envoy
    User -.->|Service Docs Port 8001/docs| CustomerAPI
    User -.->|Service Docs Port 8002/docs| ProductAPI
    User -.->|Service Docs Port 9000/docs| AuthZService
    
    %% Styling
    classDef gateway fill:#e1f5fe,stroke:#0277bd,stroke-width:3px
    classDef auth fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px
    classDef cache fill:#fff9c4,stroke:#f57f17,stroke-width:2px
    classDef service fill:#e8f5e8,stroke:#2e7d32,stroke-width:2px
    classDef data fill:#fff3e0,stroke:#f57c00,stroke-width:2px
    classDef shared fill:#fce4ec,stroke:#c2185b,stroke-width:2px
    classDef network fill:#f1f8e9,stroke:#558b2f,stroke-width:2px
    classDef external fill:#e3f2fd,stroke:#1976d2,stroke-width:2px
    
    class Envoy gateway
    class Keycloak,AuthZService auth
    class Redis cache
    class CustomerAPI,ProductAPI service
    class CustomerData,ProductData,AuthZData data
    class AuthModule,CommonUtils shared
    class Network network
    class User,Internet external
```

## Component Details

### **Envoy API Gateway** 
- **Purpose**: Single entry point for all API requests
- **Ports**: 
  - `8080` - Main API endpoint (public)
  - `9901` - Admin interface (internal)
- **Responsibilities**:
  - JWT token validation via Keycloak JWKS
  - Request routing to appropriate microservices
  - Load balancing and circuit breaking
  - Rate limiting and request/response transformation
- **Technology**: Envoy Proxy v1.31

### **Keycloak Identity Provider**
- **Purpose**: Centralized authentication and authorization
- **Port**: `8180` - HTTP interface
- **Responsibilities**:
  - User authentication (OAuth 2.0 / OpenID Connect)
  - JWT token issuance and validation
  - Role and permission management
  - JWKS endpoint for token verification
- **Technology**: Keycloak 23.0
- **Default Admin**: admin/admin (development only)

### **Authorization Service**
- **Purpose**: External authorization and role lookup service
- **Port**: `9000` - FastAPI application
- **Responsibilities**:
  - Role lookup via Envoy ext_authz filter
  - User information endpoint for React UI (/auth/me)
  - Redis-backed role caching (5-minute TTL)
  - Database query on cache miss
- **Technology**: FastAPI 0.111.0 + Python 3.12 + Redis 5.2.1
- **Data Layer**: Mock role database (future PostgreSQL)
- **Key Endpoints**:
  - `/authz/roles` - ext_authz role lookup (Envoy only)
  - `/auth/me` - User info for React UI (public with JWT)
  - `/authz/health` - Health check with cache status

### **Redis Cache**
- **Purpose**: Role lookup caching for performance
- **Port**: `6379` - Redis server
- **Responsibilities**:
  - Cache user roles with 5-minute TTL
  - Reduce database load
  - LRU eviction policy
- **Technology**: Redis 7 Alpine
- **Cache Key Format**: `user:platform-roles:{email}`
- **Configuration**: 256MB max memory, allkeys-lru policy

### **Customer Service**
- **Purpose**: Customer data management with RBAC
- **Port**: `8001` - FastAPI application
- **Authorization Rules**:
  - `customer-manager` role: Access all customer data
  - `user` role: Access only own customer record
- **Technology**: FastAPI 0.111.0 + Python 3.12
- **Data Layer**: Mock data (future PostgreSQL)

### **Product Service**
- **Purpose**: Product catalog and category management
- **Port**: `8002` - FastAPI application
- **Authorization**: All users with `user` role (via Envoy)
- **Technology**: FastAPI 0.111.0 + Python 3.12
- **Data Layer**: Mock data (future PostgreSQL)

### **Shared Authentication Module**
- **Location**: `services/shared/auth.py`
- **Purpose**: JWT token decoding and user context extraction
- **Features**:
  - Base64 JWT payload decoding
  - Role extraction from `realm_access.roles`
  - FastAPI dependency injection support

### **Common Utilities**
- **Location**: `services/shared/common.py`
- **Purpose**: Shared functionality across services
- **Features**:
  - Structured logging setup
  - Health check response formatting
  - Error response standardization

## Network Architecture

### Container Network
- **Name**: `microservices-network`
- **Type**: Docker Bridge Network
- **Purpose**: Internal service-to-service communication
- **DNS**: Automatic service discovery by container name

### Port Mapping

| Service | Internal Port | External Port | Purpose |
|---------|---------------|---------------|---------|
| Envoy Gateway | 8080 | 8080 | Main API |
| Envoy Admin | 9901 | 9901 | Admin Interface |
| Keycloak | 8080 | 8180 | Identity Provider |
| Authorization Service | 9000 | 9000 | Role Lookup & ext_authz |
| Redis Cache | 6379 | 6379 | Role Caching |
| Customer Service | 8000 | 8001 | Customer API |
| Product Service | 8000 | 8002 | Product API |

## Security Architecture

### Authentication Flow
1. **User Login**: Client authenticates with Keycloak
2. **Token Issuance**: Keycloak returns JWT token (roles NOT in JWT due to IT policy)
3. **API Request**: Client sends request with Bearer token
4. **Gateway Validation**: Envoy validates JWT signature and expiration
5. **Role Lookup**: Envoy calls Authorization Service via ext_authz
6. **Cache Check**: Authorization Service checks Redis cache for user roles
7. **Database Query**: On cache miss, Authorization Service queries role database
8. **Service Authorization**: Services implement business logic RBAC

### Authorization Layers
1. **Envoy JWT Validation**: Validates JWT signature and expiration via Keycloak JWKS
2. **Envoy ext_authz**: Calls Authorization Service for role lookup, injects roles in headers
3. **Envoy RBAC Filter**: Role-based routing (requires `user` role minimum)
4. **Customer Service**: Fine-grained RBAC (customer-manager vs user)
5. **Product Service**: Basic access control (user role via Envoy)

### Security Features
- JWT signature validation
- Role-based access control (RBAC)
- Client secret authentication
- Comprehensive audit logging
- Request rate limiting (Envoy)
- Secure container networking

## Data Flow Patterns

### Read Operations
```
Client -> Envoy -> JWT Validation -> ext_authz (Role Lookup) -> Service -> Data Layer -> Response
```

### Authentication
```
Client -> Keycloak -> JWT Token -> Client -> Envoy (JWT validation) -> ext_authz -> Service
```

### Authorization with Caching
```
Envoy -> AuthZ Service -> Redis Cache (hit) -> Role Headers -> Envoy RBAC -> Service
Envoy -> AuthZ Service -> Redis Cache (miss) -> Database -> Redis (cache) -> Role Headers -> Envoy RBAC -> Service
```

### React UI User Info
```
React -> /auth/me -> Envoy (JWT validation) -> AuthZ Service -> Redis/Database -> User Info JSON
```

## Future Enhancements

### Phase 3: Database Integration
- Replace mock data with PostgreSQL
- Add database connection pooling
- Implement data persistence layer

### Phase 4: CRUD Operations
- Add POST, PUT, DELETE endpoints
- Implement data validation
- Add transaction management

### Phase 5: Observability
- Jaeger distributed tracing
- Prometheus metrics collection
- Grafana dashboards

### Phase 6: Advanced Features
- Advanced rate limiting
- Request/response transformation
- API versioning

## Operational Considerations

### Health Monitoring
- All services expose `/health` endpoints
- Authorization Service health includes Redis cache status
- Envoy admin interface for gateway health
- Keycloak health endpoints available
- Redis health check via redis-cli ping

### Logging Strategy
- Structured logging across all services
- Request correlation IDs
- Security event logging
- Performance metrics

### Scalability
- Horizontal scaling ready
- Stateless service design
- Load balancing via Envoy
- Container orchestration ready

## Related Documentation

- [Authentication & Authorization Flow](authentication-authorization-flow.md)
- [Security Guide](../security/security-guide.md)
- [API Documentation](../api/README.md)
- [Quick Start Guide](../../QUICK_START.md)

---

*This architecture supports enterprise-grade security while maintaining simplicity and developer productivity.*