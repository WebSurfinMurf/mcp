/**
 * list_clients MCP Tool
 * Lists Keycloak clients with optional filtering
 */
import { z } from 'zod';
import { listClients } from '../keycloak/operations.js';
/**
 * Tool name for MCP registration
 */
export const name = 'list_clients';
/**
 * Tool description for MCP
 */
export const description = `List Keycloak clients with optional filtering.

Returns a list of clients with their basic information (id, clientId, name, enabled, protocol).
Supports pagination and search filtering.`;
/**
 * Input schema for validation
 */
export const inputSchema = z.object({
    search: z.string()
        .max(255)
        .optional()
        .describe('Search filter (matches clientId and name)'),
    first: z.number()
        .int()
        .min(0)
        .optional()
        .default(0)
        .describe('Pagination offset (default: 0)'),
    max: z.number()
        .int()
        .min(1)
        .max(1000)
        .optional()
        .default(100)
        .describe('Maximum results to return (default: 100, max: 1000)'),
});
/**
 * Execute the list_clients tool
 */
export async function execute(client, input) {
    const listInput = {
        search: input.search,
        first: input.first,
        max: input.max,
    };
    const result = await listClients(client, listInput);
    return JSON.stringify({
        success: result.success,
        total: result.total,
        clients: result.clients,
        message: result.message,
    }, null, 2);
}
//# sourceMappingURL=list-clients.js.map