/**
 * Keycloak Admin REST API Endpoint Builders
 * Constructs URLs for various admin operations
 */
/**
 * Build the token endpoint URL for obtaining admin tokens
 * @param baseUrl - Keycloak server base URL (e.g., https://keycloak.ai-servicers.com)
 * @param realm - The realm to authenticate against (usually 'master' for admin)
 */
export declare function tokenEndpoint(baseUrl: string, realm?: string): string;
/**
 * Build the base admin API URL for a specific realm
 * @param baseUrl - Keycloak server base URL
 * @param realm - Target realm for admin operations
 */
export declare function adminRealmUrl(baseUrl: string, realm: string): string;
/**
 * Build the clients endpoint URL (for listing and creating clients)
 * @param baseUrl - Keycloak server base URL
 * @param realm - Target realm
 */
export declare function clientsEndpoint(baseUrl: string, realm: string): string;
/**
 * Build the URL for a specific client by internal ID
 * @param baseUrl - Keycloak server base URL
 * @param realm - Target realm
 * @param clientInternalId - The internal UUID of the client (not clientId)
 */
export declare function clientEndpoint(baseUrl: string, realm: string, clientInternalId: string): string;
/**
 * Build the client secret endpoint
 * @param baseUrl - Keycloak server base URL
 * @param realm - Target realm
 * @param clientInternalId - The internal UUID of the client
 */
export declare function clientSecretEndpoint(baseUrl: string, realm: string, clientInternalId: string): string;
/**
 * Build the protocol mappers endpoint for a client
 * @param baseUrl - Keycloak server base URL
 * @param realm - Target realm
 * @param clientInternalId - The internal UUID of the client
 */
export declare function protocolMappersEndpoint(baseUrl: string, realm: string, clientInternalId: string): string;
/**
 * Build query string for client search
 * @param params - Search parameters
 */
export declare function buildClientSearchQuery(params: {
    search?: string;
    first?: number;
    max?: number;
    clientId?: string;
}): string;
/**
 * Build full URL for client listing with optional search
 * @param baseUrl - Keycloak server base URL
 * @param realm - Target realm
 * @param params - Optional search parameters
 */
export declare function clientsSearchEndpoint(baseUrl: string, realm: string, params?: {
    search?: string;
    first?: number;
    max?: number;
    clientId?: string;
}): string;
//# sourceMappingURL=endpoints.d.ts.map