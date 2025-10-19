# Keycloak Client Setup Instructions for MCP Server

## 📋 **Client Configuration**

### **Access Keycloak Admin Console**
- URL: https://keycloak.ai-servicers.com
- Navigate to realm: `main` (not `master`)
- Go to: Clients → Create Client

### **Client Settings**
```
Client ID: mcp-server
Client Type: OpenID Connect
Client Authentication: ON
Authorization: OFF (using groups for authorization)
```

### **Authentication Flow Settings**
```
Standard Flow: ON
Direct Access Grants: OFF
Service Accounts Roles: OFF
OAuth 2.0 Device Authorization Grant: OFF
OIDC CIBA Grant: OFF
```

### **Login Settings**
```
Root URL: https://mcp.ai-servicers.com
Home URL: https://mcp.ai-servicers.com
Valid Redirect URIs:
  - https://mcp.ai-servicers.com/oauth2/callback
Valid Post Logout Redirect URIs:
  - https://mcp.ai-servicers.com
Web Origins:
  - https://mcp.ai-servicers.com
Admin URL: (leave empty)
```

## 🔐 **Client Secret**

After creating the client:

1. Go to: **Credentials** tab
2. Copy the **Client Secret** value
3. Update the environment file:

```bash
# Edit this file:
sudo nano $HOME/projects/secrets/mcp-server.env

# Replace this line:
OAUTH2_PROXY_CLIENT_SECRET=CHANGE_ME_AFTER_KEYCLOAK_SETUP

# With:
OAUTH2_PROXY_CLIENT_SECRET=<your-actual-client-secret>
```

## 👥 **Group Configuration**

### **Required Groups in Keycloak**
Ensure these groups exist in the `main` realm:
- `administrators` - Full infrastructure access
- `developers` - Development and debugging access

### **User Assignment**
1. Go to: **Groups** → Select group → **Members**
2. Add appropriate users to each group
3. Verify users have correct group membership

### **Client Scope Mapping** (Optional Advanced Config)
If you want to customize claims:
1. Go to: **Client Scopes** → `groups` → **Mappers**
2. Ensure `Group Membership` mapper is enabled
3. Set `Token Claim Name` to `groups`

## 🚀 **Deployment After Setup**

Once client is configured:

```bash
# Navigate to MCP server directory
cd /home/administrator/projects/mcp/server

# Restart OAuth2 proxy with new configuration
docker compose restart mcp-server-auth-proxy

# Wait 10 seconds for startup
sleep 10

# Test authentication
curl -I https://mcp.ai-servicers.com/health
# Should return 302 redirect to Keycloak login
```

## ✅ **Verification Steps**

### **Test Administrator Access**
1. Open: https://mcp.ai-servicers.com
2. Should redirect to Keycloak login
3. Login with administrator account
4. Should redirect back to MCP server
5. Verify access to: `/docs`, `/tools`, `/health`

### **Test Developer Access**
1. Use different browser or incognito mode
2. Open: https://mcp.ai-servicers.com
3. Login with developer account
4. Should have same access as administrators
5. Test tool execution via API docs

### **Test Unauthorized Access**
1. Try with user NOT in administrators or developers groups
2. Should be denied access after Keycloak login
3. OAuth2 proxy should show "Authorization Required" error

## 🔧 **Troubleshooting**

### **OAuth2 Proxy Logs**
```bash
docker logs mcp-server-auth-proxy --tail 20
```

### **Common Issues**
- **"Invalid client"**: Check client ID matches exactly
- **"Unauthorized redirect_uri"**: Verify redirect URL is exact
- **"Access denied"**: User not in administrators or developers group
- **"Invalid cookie secret"**: Ensure 32-character hex secret

### **Test Direct Access (Development)**
For debugging, temporarily bypass auth:
```bash
# Direct container access (internal only)
curl http://localhost:8000/health
curl http://localhost:8000/tools
```

## 📊 **Expected Result**

After successful setup:
- ✅ https://mcp.ai-servicers.com redirects to Keycloak
- ✅ Administrators and developers can login
- ✅ Users get access to MCP server tools
- ✅ Unauthorized users are blocked
- ✅ Sessions persist across browser tabs
- ✅ Single sign-on with other ai-servicers.com services

---
*Created: 2025-09-14*
*Purpose: Complete Keycloak client setup for MCP server internet exposure*
*Security: OAuth2 proxy + group-based authorization*