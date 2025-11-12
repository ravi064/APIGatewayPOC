# Security Documentation

This section contains all security-related documentation for the APIGatewayPOC project.

## Documents

### [Security Guide](security-guide.md)
Comprehensive security documentation covering:
- Understanding the 4 Keycloak clients
- Security concerns addressed
- Client authentication mechanisms
- Preventing spoofing attacks
- Production security checklist
- Secrets management
- Network security
- Monitoring and auditing

### [Security Quick Start](security-quick-start.md)
Quick reference for:
- Authentication flow
- Getting started in 3 steps
- Available roles
- Test users
- Security best practices

## Quick Links

**For Developers:**
- [Get Started with Security](security-quick-start.md#get-started-in-3-steps)
- [Rotate Client Secrets](../../scripts/README.md#secret-rotation-workflow)

**For Security Team:**
- [Security Checklist](security-guide.md#production-security-checklist)
- [Attack Prevention](security-guide.md#preventing-spoofing-attacks)

**For DevOps:**
- [Production Requirements](security-guide.md#production-security-checklist)
- [Secrets Management](security-guide.md#secrets-management)

## Important Warnings

- **Default Secrets**: Change all client secrets before production deployment
- **Test Client**: Disable `test-client` in production environments
- **HTTPS**: Enable SSL/TLS for production deployments
- **Secrets Management**: Use a secrets manager (Azure Key Vault, AWS Secrets Manager, etc.)

## Security Best Practices

1. **Never commit secrets to git**
2. **Use environment variables for configuration**
3. **Rotate secrets regularly**
4. **Enable audit logging**
5. **Monitor for suspicious activity**
6. **Keep Keycloak updated**
7. **Use HTTPS in production**
8. **Implement rate limiting**

## Getting Help

If you discover a security issue:
1. Do not create a public GitHub issue
2. Contact the project maintainer directly
3. Follow responsible disclosure practices

---

**Last Updated**: October 2025
