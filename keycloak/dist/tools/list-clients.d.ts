/**
 * list_clients MCP Tool
 * Lists Keycloak clients with optional filtering
 */
import { z } from 'zod';
import { KeycloakClient } from '../keycloak/client.js';
/**
 * Tool name for MCP registration
 */
export declare const name = "list_clients";
/**
 * Tool description for MCP
 */
export declare const description = "List Keycloak clients with optional filtering.\n\nReturns a list of clients with their basic information (id, clientId, name, enabled, protocol).\nSupports pagination and search filtering.";
/**
 * Input schema for validation
 */
export declare const inputSchema: z.ZodObject<{
    search: z.ZodOptional<z.ZodString>;
    first: z.ZodDefault<z.ZodOptional<z.ZodNumber>>;
    max: z.ZodDefault<z.ZodOptional<z.ZodNumber>>;
}, "strip", z.ZodTypeAny, {
    first: number;
    max: number;
    search?: string | undefined;
}, {
    search?: string | undefined;
    first?: number | undefined;
    max?: number | undefined;
}>;
export type ListClientsToolInput = z.infer<typeof inputSchema>;
/**
 * Execute the list_clients tool
 */
export declare function execute(client: KeycloakClient, input: ListClientsToolInput): Promise<string>;
//# sourceMappingURL=list-clients.d.ts.map