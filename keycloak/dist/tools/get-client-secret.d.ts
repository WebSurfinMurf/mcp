/**
 * get_client_secret MCP Tool
 * Retrieves the client secret for an existing Keycloak client
 */
import { z } from 'zod';
import { KeycloakClient } from '../keycloak/client.js';
/**
 * Tool name for MCP registration
 */
export declare const name = "get_client_secret";
/**
 * Tool description for MCP
 */
export declare const description = "Retrieve the client secret for an existing Keycloak client.\n\nUse this to get credentials for a client that was previously created.\nReturns an error if the client does not exist.";
/**
 * Input schema for validation
 */
export declare const inputSchema: z.ZodObject<{
    clientId: z.ZodString;
}, "strip", z.ZodTypeAny, {
    clientId: string;
}, {
    clientId: string;
}>;
export type GetClientSecretToolInput = z.infer<typeof inputSchema>;
/**
 * Execute the get_client_secret tool
 */
export declare function execute(client: KeycloakClient, input: GetClientSecretToolInput): Promise<string>;
//# sourceMappingURL=get-client-secret.d.ts.map