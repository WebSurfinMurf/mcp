/**
 * add_groups_mapper MCP Tool
 * Adds a groups membership mapper to a Keycloak client
 */

import { z } from 'zod';
import { KeycloakClient } from '../keycloak/client.js';
import { addGroupsMapper } from '../keycloak/operations.js';
import { AddGroupsMapperInput } from '../keycloak/types.js';

/**
 * Tool name for MCP registration
 */
export const name = 'add_groups_mapper';

/**
 * Tool description for MCP
 */
export const description = `Add a groups membership mapper to a Keycloak client.

This mapper includes the user's group memberships in the token claims.
If the mapper already exists, the operation succeeds (idempotent).

The mapper is configured to include groups in:
- Access token
- ID token
- UserInfo endpoint`;

/**
 * Input schema for validation
 */
export const inputSchema = z.object({
  clientId: z.string()
    .min(1)
    .max(255)
    .describe('The clientId of the client to add the mapper to'),

  mapperName: z.string()
    .max(255)
    .optional()
    .default('groups')
    .describe('Name for the mapper (default: "groups")'),

  claimName: z.string()
    .max(255)
    .optional()
    .default('groups')
    .describe('Name of the claim in the token (default: "groups")'),

  fullPath: z.boolean()
    .optional()
    .default(false)
    .describe('Include full group path (e.g., "/parent/child") vs just group name'),
});

export type AddGroupsMapperToolInput = z.infer<typeof inputSchema>;

/**
 * Execute the add_groups_mapper tool
 */
export async function execute(
  client: KeycloakClient,
  input: AddGroupsMapperToolInput
): Promise<string> {
  const mapperInput: AddGroupsMapperInput = {
    clientId: input.clientId,
    mapperName: input.mapperName,
    claimName: input.claimName,
    fullPath: input.fullPath,
  };

  const result = await addGroupsMapper(client, mapperInput);

  if (result.success) {
    return JSON.stringify({
      success: true,
      clientId: result.clientId,
      mapperName: result.mapperName,
      alreadyExisted: result.alreadyExists,
      message: result.message,
    }, null, 2);
  }

  return JSON.stringify({
    success: false,
    clientId: result.clientId,
    error: result.message,
  }, null, 2);
}
