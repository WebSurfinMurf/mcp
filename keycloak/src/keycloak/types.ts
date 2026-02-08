/**
 * Keycloak Admin REST API Type Definitions
 * For client credential management operations
 */

// ============================================================================
// Client Representations
// ============================================================================

/**
 * Keycloak Client representation from Admin REST API
 * Subset of fields relevant to credential management
 */
export interface KeycloakClient {
  id?: string;
  clientId: string;
  name?: string;
  description?: string;
  enabled?: boolean;
  clientAuthenticatorType?: string;
  secret?: string;
  redirectUris?: string[];
  webOrigins?: string[];
  bearerOnly?: boolean;
  consentRequired?: boolean;
  standardFlowEnabled?: boolean;
  implicitFlowEnabled?: boolean;
  directAccessGrantsEnabled?: boolean;
  serviceAccountsEnabled?: boolean;
  publicClient?: boolean;
  frontchannelLogout?: boolean;
  protocol?: string;
  attributes?: Record<string, string>;
  fullScopeAllowed?: boolean;
  defaultClientScopes?: string[];
  optionalClientScopes?: string[];
}

/**
 * Minimal client representation for list operations
 */
export interface ClientListItem {
  id: string;
  clientId: string;
  name?: string;
  enabled?: boolean;
  protocol?: string;
}

/**
 * Client secret response from Keycloak
 */
export interface ClientSecret {
  type: string;
  value: string;
}

// ============================================================================
// Protocol Mapper Representations
// ============================================================================

/**
 * Protocol mapper configuration for client
 */
export interface ProtocolMapper {
  id?: string;
  name: string;
  protocol: string;
  protocolMapper: string;
  consentRequired?: boolean;
  config: Record<string, string>;
}

/**
 * Groups mapper specific configuration
 */
export interface GroupsMapperConfig {
  'claim.name': string;
  'full.path': string;
  'id.token.claim': string;
  'access.token.claim': string;
  'userinfo.token.claim': string;
}

// ============================================================================
// Token Representations
// ============================================================================

/**
 * OAuth2 token response from Keycloak
 */
export interface TokenResponse {
  access_token: string;
  expires_in: number;
  refresh_expires_in?: number;
  refresh_token?: string;
  token_type: string;
  'not-before-policy'?: number;
  session_state?: string;
  scope?: string;
}

/**
 * Cached token with expiration tracking
 */
export interface CachedToken {
  accessToken: string;
  expiresAt: number; // Unix timestamp in milliseconds
}

// ============================================================================
// Error Representations
// ============================================================================

/**
 * Keycloak error response
 */
export interface KeycloakError {
  error?: string;
  error_description?: string;
  errorMessage?: string;
}

// ============================================================================
// Tool Input Types
// ============================================================================

/**
 * Input for create_client tool
 */
export interface CreateClientInput {
  clientId: string;
  name?: string;
  description?: string;
  redirectUris?: string[];
  webOrigins?: string[];
  serviceAccountsEnabled?: boolean;
  standardFlowEnabled?: boolean;
  directAccessGrantsEnabled?: boolean;
}

/**
 * Input for get_client_secret tool
 */
export interface GetClientSecretInput {
  clientId: string;
}

/**
 * Input for add_groups_mapper tool
 */
export interface AddGroupsMapperInput {
  clientId: string;
  mapperName?: string;
  claimName?: string;
  fullPath?: boolean;
}

/**
 * Input for list_clients tool
 */
export interface ListClientsInput {
  search?: string;
  first?: number;
  max?: number;
}

// ============================================================================
// Tool Output Types
// ============================================================================

/**
 * Result of create_client operation
 */
export interface CreateClientResult {
  success: boolean;
  clientId: string;
  internalId: string;
  secret: string;
  message: string;
}

/**
 * Result of get_client_secret operation
 */
export interface GetClientSecretResult {
  success: boolean;
  clientId: string;
  secret: string;
  message: string;
}

/**
 * Result of add_groups_mapper operation
 */
export interface AddGroupsMapperResult {
  success: boolean;
  clientId: string;
  mapperName: string;
  alreadyExists: boolean;
  message: string;
}

/**
 * Result of list_clients operation
 */
export interface ListClientsResult {
  success: boolean;
  clients: ClientListItem[];
  total: number;
  message: string;
}

// ============================================================================
// Configuration Types
// ============================================================================

/**
 * MCP Keycloak server configuration
 */
export interface ServerConfig {
  keycloakUrl: string;
  realm: string;
  adminUsername: string;
  adminPassword: string;
  tokenRefreshBuffer?: number; // Seconds before expiry to refresh (default: 30)
}
