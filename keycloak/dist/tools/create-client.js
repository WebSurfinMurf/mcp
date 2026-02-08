/**
 * create_client MCP Tool
 * Creates a new confidential OIDC client in Keycloak
 */
import { z } from 'zod';
import { createClient } from '../keycloak/operations.js';
/**
 * Tool name for MCP registration
 */
export const name = 'create_client';
/**
 * Tool description for MCP
 */
export const description = `Create a new confidential OIDC client in Keycloak.

Returns the client secret upon successful creation. If the client already exists,
returns the existing client's secret (idempotent operation).

The client is created with:
- Protocol: openid-connect
- Client type: confidential (with client secret)
- Full scope allowed: true`;
/**
 * Input schema for validation
 */
export const inputSchema = z.object({
    clientId: z.string()
        .min(1)
        .max(255)
        .regex(/^[a-zA-Z0-9_-]+$/, 'clientId must contain only alphanumeric characters, hyphens, and underscores')
        .describe('Unique identifier for the client (e.g., "my-service")'),
    name: z.string()
        .max(255)
        .optional()
        .describe('Human-readable name for the client (defaults to clientId)'),
    description: z.string()
        .max(1000)
        .optional()
        .describe('Description of the client purpose'),
    redirectUris: z.array(z.string().url())
        .optional()
        .default([])
        .describe('List of valid redirect URIs for OAuth2 flows'),
    webOrigins: z.array(z.string())
        .optional()
        .default([])
        .describe('Allowed CORS origins'),
    serviceAccountsEnabled: z.boolean()
        .optional()
        .default(false)
        .describe('Enable service account (client credentials grant)'),
    standardFlowEnabled: z.boolean()
        .optional()
        .default(true)
        .describe('Enable authorization code flow'),
    directAccessGrantsEnabled: z.boolean()
        .optional()
        .default(false)
        .describe('Enable direct access grants (resource owner password)'),
});
/**
 * Execute the create_client tool
 */
export async function execute(client, input) {
    const createInput = {
        clientId: input.clientId,
        name: input.name,
        description: input.description,
        redirectUris: input.redirectUris,
        webOrigins: input.webOrigins,
        serviceAccountsEnabled: input.serviceAccountsEnabled,
        standardFlowEnabled: input.standardFlowEnabled,
        directAccessGrantsEnabled: input.directAccessGrantsEnabled,
    };
    const result = await createClient(client, createInput);
    if (result.success) {
        return JSON.stringify({
            success: true,
            clientId: result.clientId,
            internalId: result.internalId,
            secret: result.secret,
            message: result.message,
        }, null, 2);
    }
    return JSON.stringify({
        success: false,
        error: result.message,
    }, null, 2);
}
//# sourceMappingURL=create-client.js.map