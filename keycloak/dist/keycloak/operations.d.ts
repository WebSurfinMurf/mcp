/**
 * Keycloak Admin API Operations
 * High-level functions for client management
 */
import { KeycloakClient } from './client.js';
import { CreateClientInput, CreateClientResult, GetClientSecretResult, AddGroupsMapperInput, AddGroupsMapperResult, ListClientsInput, ListClientsResult } from './types.js';
/**
 * Find a client by clientId (the human-readable identifier)
 * Returns the internal UUID if found, null otherwise
 */
export declare function findClientByClientId(client: KeycloakClient, clientId: string): Promise<string | null>;
/**
 * Create a new OIDC client in Keycloak
 */
export declare function createClient(client: KeycloakClient, input: CreateClientInput): Promise<CreateClientResult>;
/**
 * Get the secret for an existing client
 */
export declare function getClientSecret(client: KeycloakClient, clientId: string): Promise<GetClientSecretResult>;
/**
 * Add a groups mapper to a client's protocol mappers
 * This adds group membership to the token claims
 */
export declare function addGroupsMapper(client: KeycloakClient, input: AddGroupsMapperInput): Promise<AddGroupsMapperResult>;
/**
 * List clients with optional filtering
 */
export declare function listClients(client: KeycloakClient, input?: ListClientsInput): Promise<ListClientsResult>;
//# sourceMappingURL=operations.d.ts.map