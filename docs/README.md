# APIGatewayPOC Documentation

Complete documentation for the API Gateway Proof of Concept.

## Quick Start

**New to the project?** Start here:
1. [Quick Start](../QUICK_START.md) - Get running in 5 minutes
2. [System Architecture](architecture/system-architecture.md) - Understand the system
3. Pick your guide below based on your role

## Documentation by Audience

### UI Developers (React/Frontend)
- [UI Developer Guide](ui-developer-guide.md) - React authentication and roles
- [React Auth Integration](development/react-auth-integration.md) - Detailed examples
- [API Documentation](api/README.md) - API endpoints reference

### Backend Developers (FastAPI)
- [Backend Developer Guide](backend-developer-guide.md) - FastAPI service development
- [Developer Guide](developer-guide.md) - Common commands and testing
- [AuthZ Service](../services/authz-service/README.md) - External authorization
- [Shared Utilities](../services/shared/) - Common code

### DevOps/Security
- [Production Deployment](production-deployment-guide.md) - Deployment checklist
- [Security Quick Start](security/security-quick-start.md) - Security essentials
- [Security Guide](security/security-guide.md) - Comprehensive security docs
- [Keycloak Setup](setup/keycloak-setup.md) - Authentication configuration

### All Developers
- [Developer Guide](developer-guide.md) - Common commands, testing, troubleshooting
- [API Generation](api/API_GENERATION_GUIDE.md) - Generate API documentation
- [Scripts Documentation](../scripts/README.md) - Utility scripts

## Documentation Structure

### Core Guides (Start Here)
- [UI Developer Guide](ui-developer-guide.md) - React integration
- [Backend Developer Guide](backend-developer-guide.md) - FastAPI services
- [Production Deployment](production-deployment-guide.md) - Deployment guide
- [Developer Guide](developer-guide.md) - Commands and testing

### Security
- [Security Quick Start](security/security-quick-start.md) - Concise security guide
- [Security Guide](security/security-guide.md) - Detailed security documentation
- [Security Fixes](security/security-fixes.md) - Recent improvements

### Architecture
- [System Architecture](architecture/system-architecture.md) - System overview
- [Authentication & Authorization Flow](architecture/authentication-authorization-flow.md) - Auth diagrams

### API Documentation
- [API Documentation](api/README.md) - Auto-generated API docs
- [API Generation Guide](api/API_GENERATION_GUIDE.md) - How to generate docs
- Interactive docs: [Customer](http://localhost:8001/docs) | [Product](http://localhost:8002/docs)

### Development
- [React Auth Integration](development/react-auth-integration.md) - UI auth details
- [Scripts Documentation](../scripts/README.md) - Utility scripts

### Setup
- [Keycloak Setup](setup/keycloak-setup.md) - Authentication configuration

## Quick Find

**Get Started:**
- [5-minute setup](../QUICK_START.md)
- [Start services](developer-guide.md#quick-start)
- [Get access token](security/security-quick-start.md#get-started-in-3-steps)

**By Task:**
- [Add UI authentication](ui-developer-guide.md#quick-start)
- [Create new service](backend-developer-guide.md#quick-start)
- [Deploy to production](production-deployment-guide.md#pre-deployment-checklist)
- [Run tests](developer-guide.md#testing)
- [Generate API docs](api/API_GENERATION_GUIDE.md#quick-start)
- [Rotate secrets](production-deployment-guide.md#secret-management)

**By Component:**
- [Gateway (Envoy)](../services/gateway/)
- [AuthZ Service](../services/authz-service/README.md)
- [Customer Service](../services/customer-service/)
- [Product Service](../services/product-service/)
- [Keycloak](../services/keycloak/README.md)

## Documentation Updates

- **Last Updated**: November 2025
- **Status**: External authorization with Redis caching complete
- **Focus**: Production-ready API Gateway with role-based access control

---

**Need help?** Check the [Developer Guide](developer-guide.md) for common commands and troubleshooting.
