/**
 * create_client MCP Tool
 * Creates a new confidential OIDC client in Keycloak
 */
import { z } from 'zod';
import { KeycloakClient } from '../keycloak/client.js';
/**
 * Tool name for MCP registration
 */
export declare const name = "create_client";
/**
 * Tool description for MCP
 */
export declare const description = "Create a new confidential OIDC client in Keycloak.\n\nReturns the client secret upon successful creation. If the client already exists,\nreturns the existing client's secret (idempotent operation).\n\nThe client is created with:\n- Protocol: openid-connect\n- Client type: confidential (with client secret)\n- Full scope allowed: true";
/**
 * Input schema for validation
 */
export declare const inputSchema: z.ZodObject<{
    clientId: z.ZodString;
    name: z.ZodOptional<z.ZodString>;
    description: z.ZodOptional<z.ZodString>;
    redirectUris: z.ZodDefault<z.ZodOptional<z.ZodArray<z.ZodString, "many">>>;
    webOrigins: z.ZodDefault<z.ZodOptional<z.ZodArray<z.ZodString, "many">>>;
    serviceAccountsEnabled: z.ZodDefault<z.ZodOptional<z.ZodBoolean>>;
    standardFlowEnabled: z.ZodDefault<z.ZodOptional<z.ZodBoolean>>;
    directAccessGrantsEnabled: z.ZodDefault<z.ZodOptional<z.ZodBoolean>>;
}, "strip", z.ZodTypeAny, {
    clientId: string;
    redirectUris: string[];
    webOrigins: string[];
    serviceAccountsEnabled: boolean;
    standardFlowEnabled: boolean;
    directAccessGrantsEnabled: boolean;
    name?: string | undefined;
    description?: string | undefined;
}, {
    clientId: string;
    name?: string | undefined;
    description?: string | undefined;
    redirectUris?: string[] | undefined;
    webOrigins?: string[] | undefined;
    serviceAccountsEnabled?: boolean | undefined;
    standardFlowEnabled?: boolean | undefined;
    directAccessGrantsEnabled?: boolean | undefined;
}>;
export type CreateClientToolInput = z.infer<typeof inputSchema>;
/**
 * Execute the create_client tool
 */
export declare function execute(client: KeycloakClient, input: CreateClientToolInput): Promise<string>;
//# sourceMappingURL=create-client.d.ts.map