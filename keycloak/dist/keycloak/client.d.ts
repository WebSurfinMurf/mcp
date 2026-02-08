/**
 * Keycloak HTTP Client with Token Management
 *
 * Features:
 * - Automatic token acquisition and refresh
 * - Mutex-protected token operations (thread-safe)
 * - Configurable refresh buffer (default 30 seconds before expiry)
 * - Automatic retry on 401 Unauthorized
 */
import { KeycloakError, ServerConfig } from './types.js';
/**
 * Keycloak HTTP client with automatic token management
 */
export declare class KeycloakClient {
    private config;
    private cachedToken;
    private tokenMutex;
    private refreshBuffer;
    constructor(config: ServerConfig);
    /**
     * Get a valid access token, refreshing if necessary
     * Thread-safe: uses mutex to prevent concurrent refresh requests
     */
    getToken(): Promise<string>;
    /**
     * Check if the cached token is expired or about to expire
     */
    private isTokenExpired;
    /**
     * Fetch a new admin token from Keycloak
     */
    private fetchToken;
    /**
     * Make an authenticated request to the Keycloak Admin API
     * Automatically handles token refresh and 401 retries
     *
     * @param url - Full URL to request
     * @param options - Fetch options (method, body, etc.)
     * @param retryOn401 - Whether to retry once on 401 (default true)
     */
    request<T>(url: string, options?: RequestInit, retryOn401?: boolean): Promise<T>;
    /**
     * Make a POST request
     */
    post<T>(url: string, body: unknown): Promise<T>;
    /**
     * Make a GET request
     */
    get<T>(url: string): Promise<T>;
    /**
     * Get the Location header from a response (for 201 Created)
     * Useful for getting the internal ID after creating a resource
     */
    postAndGetLocation(url: string, body: unknown): Promise<string | null>;
    /**
     * Parse error response from Keycloak
     */
    private parseError;
    /**
     * Get the configured realm
     */
    get realm(): string;
    /**
     * Get the base Keycloak URL
     */
    get baseUrl(): string;
}
/**
 * Custom error class for Keycloak API errors
 */
export declare class KeycloakApiError extends Error {
    readonly status: number;
    readonly details?: KeycloakError | undefined;
    constructor(status: number, message: string, details?: KeycloakError | undefined);
    /**
     * Check if this is a "not found" error
     */
    isNotFound(): boolean;
    /**
     * Check if this is a "conflict" error (resource already exists)
     */
    isConflict(): boolean;
    /**
     * Check if this is an authorization error
     */
    isUnauthorized(): boolean;
}
/**
 * Create a KeycloakClient instance from environment variables
 */
export declare function createClientFromEnv(): KeycloakClient;
//# sourceMappingURL=client.d.ts.map