/**
 * Keycloak module barrel export
 */
export type { KeycloakClient as KeycloakClientRepresentation, ClientListItem, ClientSecret, ProtocolMapper, GroupsMapperConfig, TokenResponse, CachedToken, KeycloakError, CreateClientInput, GetClientSecretInput, AddGroupsMapperInput, ListClientsInput, CreateClientResult, GetClientSecretResult, AddGroupsMapperResult, ListClientsResult, ServerConfig, } from './types.js';
export * from './endpoints.js';
export { KeycloakClient, KeycloakApiError, createClientFromEnv } from './client.js';
export * from './operations.js';
//# sourceMappingURL=index.d.ts.map