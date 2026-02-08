/**
 * Keycloak module barrel export
 */

// Types (rename KeycloakClient interface to avoid collision with class)
export type {
  KeycloakClient as KeycloakClientRepresentation,
  ClientListItem,
  ClientSecret,
  ProtocolMapper,
  GroupsMapperConfig,
  TokenResponse,
  CachedToken,
  KeycloakError,
  CreateClientInput,
  GetClientSecretInput,
  AddGroupsMapperInput,
  ListClientsInput,
  CreateClientResult,
  GetClientSecretResult,
  AddGroupsMapperResult,
  ListClientsResult,
  ServerConfig,
} from './types.js';

// Endpoints
export * from './endpoints.js';

// Client (class and factory)
export { KeycloakClient, KeycloakApiError, createClientFromEnv } from './client.js';

// Operations
export * from './operations.js';
