/**
 * add_groups_mapper MCP Tool
 * Adds a groups membership mapper to a Keycloak client
 */
import { z } from 'zod';
import { KeycloakClient } from '../keycloak/client.js';
/**
 * Tool name for MCP registration
 */
export declare const name = "add_groups_mapper";
/**
 * Tool description for MCP
 */
export declare const description = "Add a groups membership mapper to a Keycloak client.\n\nThis mapper includes the user's group memberships in the token claims.\nIf the mapper already exists, the operation succeeds (idempotent).\n\nThe mapper is configured to include groups in:\n- Access token\n- ID token\n- UserInfo endpoint";
/**
 * Input schema for validation
 */
export declare const inputSchema: z.ZodObject<{
    clientId: z.ZodString;
    mapperName: z.ZodDefault<z.ZodOptional<z.ZodString>>;
    claimName: z.ZodDefault<z.ZodOptional<z.ZodString>>;
    fullPath: z.ZodDefault<z.ZodOptional<z.ZodBoolean>>;
}, "strip", z.ZodTypeAny, {
    clientId: string;
    mapperName: string;
    claimName: string;
    fullPath: boolean;
}, {
    clientId: string;
    mapperName?: string | undefined;
    claimName?: string | undefined;
    fullPath?: boolean | undefined;
}>;
export type AddGroupsMapperToolInput = z.infer<typeof inputSchema>;
/**
 * Execute the add_groups_mapper tool
 */
export declare function execute(client: KeycloakClient, input: AddGroupsMapperToolInput): Promise<string>;
//# sourceMappingURL=add-groups-mapper.d.ts.map