/**
 * Keycloak Admin REST API Endpoint Builders
 * Constructs URLs for various admin operations
 */

/**
 * Build the token endpoint URL for obtaining admin tokens
 * @param baseUrl - Keycloak server base URL (e.g., https://keycloak.ai-servicers.com)
 * @param realm - The realm to authenticate against (usually 'master' for admin)
 */
export function tokenEndpoint(baseUrl: string, realm: string = 'master'): string {
  return `${baseUrl}/realms/${realm}/protocol/openid-connect/token`;
}

/**
 * Build the base admin API URL for a specific realm
 * @param baseUrl - Keycloak server base URL
 * @param realm - Target realm for admin operations
 */
export function adminRealmUrl(baseUrl: string, realm: string): string {
  return `${baseUrl}/admin/realms/${realm}`;
}

/**
 * Build the clients endpoint URL (for listing and creating clients)
 * @param baseUrl - Keycloak server base URL
 * @param realm - Target realm
 */
export function clientsEndpoint(baseUrl: string, realm: string): string {
  return `${adminRealmUrl(baseUrl, realm)}/clients`;
}

/**
 * Build the URL for a specific client by internal ID
 * @param baseUrl - Keycloak server base URL
 * @param realm - Target realm
 * @param clientInternalId - The internal UUID of the client (not clientId)
 */
export function clientEndpoint(
  baseUrl: string,
  realm: string,
  clientInternalId: string
): string {
  return `${clientsEndpoint(baseUrl, realm)}/${clientInternalId}`;
}

/**
 * Build the client secret endpoint
 * @param baseUrl - Keycloak server base URL
 * @param realm - Target realm
 * @param clientInternalId - The internal UUID of the client
 */
export function clientSecretEndpoint(
  baseUrl: string,
  realm: string,
  clientInternalId: string
): string {
  return `${clientEndpoint(baseUrl, realm, clientInternalId)}/client-secret`;
}

/**
 * Build the protocol mappers endpoint for a client
 * @param baseUrl - Keycloak server base URL
 * @param realm - Target realm
 * @param clientInternalId - The internal UUID of the client
 */
export function protocolMappersEndpoint(
  baseUrl: string,
  realm: string,
  clientInternalId: string
): string {
  return `${clientEndpoint(baseUrl, realm, clientInternalId)}/protocol-mappers/models`;
}

/**
 * Build query string for client search
 * @param params - Search parameters
 */
export function buildClientSearchQuery(params: {
  search?: string;
  first?: number;
  max?: number;
  clientId?: string;
}): string {
  const queryParts: string[] = [];

  if (params.search) {
    queryParts.push(`search=${encodeURIComponent(params.search)}`);
  }
  if (params.clientId) {
    queryParts.push(`clientId=${encodeURIComponent(params.clientId)}`);
  }
  if (params.first !== undefined) {
    queryParts.push(`first=${params.first}`);
  }
  if (params.max !== undefined) {
    queryParts.push(`max=${params.max}`);
  }

  return queryParts.length > 0 ? `?${queryParts.join('&')}` : '';
}

/**
 * Build full URL for client listing with optional search
 * @param baseUrl - Keycloak server base URL
 * @param realm - Target realm
 * @param params - Optional search parameters
 */
export function clientsSearchEndpoint(
  baseUrl: string,
  realm: string,
  params?: {
    search?: string;
    first?: number;
    max?: number;
    clientId?: string;
  }
): string {
  const base = clientsEndpoint(baseUrl, realm);
  const query = params ? buildClientSearchQuery(params) : '';
  return `${base}${query}`;
}
