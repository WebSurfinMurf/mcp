/**
 * get_client_secret MCP Tool
 * Retrieves the client secret for an existing Keycloak client
 */
import { z } from 'zod';
import { getClientSecret } from '../keycloak/operations.js';
/**
 * Tool name for MCP registration
 */
export const name = 'get_client_secret';
/**
 * Tool description for MCP
 */
export const description = `Retrieve the client secret for an existing Keycloak client.

Use this to get credentials for a client that was previously created.
Returns an error if the client does not exist.`;
/**
 * Input schema for validation
 */
export const inputSchema = z.object({
    clientId: z.string()
        .min(1)
        .max(255)
        .describe('The clientId (not internal UUID) of the client'),
});
/**
 * Execute the get_client_secret tool
 */
export async function execute(client, input) {
    const result = await getClientSecret(client, input.clientId);
    if (result.success) {
        return JSON.stringify({
            success: true,
            clientId: result.clientId,
            secret: result.secret,
            message: result.message,
        }, null, 2);
    }
    return JSON.stringify({
        success: false,
        clientId: result.clientId,
        error: result.message,
    }, null, 2);
}
//# sourceMappingURL=get-client-secret.js.map