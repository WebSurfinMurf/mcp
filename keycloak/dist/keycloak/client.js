/**
 * Keycloak HTTP Client with Token Management
 *
 * Features:
 * - Automatic token acquisition and refresh
 * - Mutex-protected token operations (thread-safe)
 * - Configurable refresh buffer (default 30 seconds before expiry)
 * - Automatic retry on 401 Unauthorized
 */
import { tokenEndpoint } from './endpoints.js';
/**
 * Simple mutex implementation for token refresh synchronization
 * Prevents multiple concurrent token refresh requests
 */
class Mutex {
    locked = false;
    queue = [];
    async acquire() {
        return new Promise((resolve) => {
            if (!this.locked) {
                this.locked = true;
                resolve();
            }
            else {
                this.queue.push(resolve);
            }
        });
    }
    release() {
        if (this.queue.length > 0) {
            const next = this.queue.shift();
            next?.();
        }
        else {
            this.locked = false;
        }
    }
}
/**
 * Keycloak HTTP client with automatic token management
 */
export class KeycloakClient {
    config;
    cachedToken = null;
    tokenMutex = new Mutex();
    refreshBuffer; // milliseconds
    constructor(config) {
        this.config = config;
        // Default 30 second buffer before token expiry
        this.refreshBuffer = (config.tokenRefreshBuffer ?? 30) * 1000;
    }
    /**
     * Get a valid access token, refreshing if necessary
     * Thread-safe: uses mutex to prevent concurrent refresh requests
     */
    async getToken() {
        // Check if we have a valid cached token
        if (this.cachedToken && !this.isTokenExpired()) {
            return this.cachedToken.accessToken;
        }
        // Acquire mutex for token refresh
        await this.tokenMutex.acquire();
        try {
            // Double-check after acquiring mutex (another request may have refreshed)
            if (this.cachedToken && !this.isTokenExpired()) {
                return this.cachedToken.accessToken;
            }
            // Fetch new token
            const tokenResponse = await this.fetchToken();
            // Cache the token with expiration time
            this.cachedToken = {
                accessToken: tokenResponse.access_token,
                expiresAt: Date.now() + (tokenResponse.expires_in * 1000),
            };
            return this.cachedToken.accessToken;
        }
        finally {
            this.tokenMutex.release();
        }
    }
    /**
     * Check if the cached token is expired or about to expire
     */
    isTokenExpired() {
        if (!this.cachedToken)
            return true;
        // Token is considered expired if within the refresh buffer
        return Date.now() >= (this.cachedToken.expiresAt - this.refreshBuffer);
    }
    /**
     * Fetch a new admin token from Keycloak
     */
    async fetchToken() {
        const url = tokenEndpoint(this.config.keycloakUrl, 'master');
        const body = new URLSearchParams({
            grant_type: 'password',
            client_id: 'admin-cli',
            username: this.config.adminUsername,
            password: this.config.adminPassword,
        });
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: body.toString(),
        });
        if (!response.ok) {
            const error = await this.parseError(response);
            throw new Error(`Token fetch failed: ${error.error_description || error.errorMessage || response.statusText}`);
        }
        return response.json();
    }
    /**
     * Make an authenticated request to the Keycloak Admin API
     * Automatically handles token refresh and 401 retries
     *
     * @param url - Full URL to request
     * @param options - Fetch options (method, body, etc.)
     * @param retryOn401 - Whether to retry once on 401 (default true)
     */
    async request(url, options = {}, retryOn401 = true) {
        const token = await this.getToken();
        const response = await fetch(url, {
            ...options,
            headers: {
                ...options.headers,
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json',
            },
        });
        // Handle 401 by refreshing token and retrying once
        if (response.status === 401 && retryOn401) {
            // Invalidate cached token
            this.cachedToken = null;
            // Retry with fresh token (no more retries)
            return this.request(url, options, false);
        }
        // Handle error responses
        if (!response.ok) {
            const error = await this.parseError(response);
            throw new KeycloakApiError(response.status, error.error_description || error.errorMessage || response.statusText, error);
        }
        // Handle empty responses (e.g., 201 Created, 204 No Content)
        const contentLength = response.headers.get('content-length');
        if (contentLength === '0' || response.status === 204) {
            return {};
        }
        return response.json();
    }
    /**
     * Make a POST request
     */
    async post(url, body) {
        return this.request(url, {
            method: 'POST',
            body: JSON.stringify(body),
        });
    }
    /**
     * Make a GET request
     */
    async get(url) {
        return this.request(url, { method: 'GET' });
    }
    /**
     * Get the Location header from a response (for 201 Created)
     * Useful for getting the internal ID after creating a resource
     */
    async postAndGetLocation(url, body) {
        const token = await this.getToken();
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(body),
        });
        if (!response.ok) {
            const error = await this.parseError(response);
            throw new KeycloakApiError(response.status, error.error_description || error.errorMessage || response.statusText, error);
        }
        return response.headers.get('Location');
    }
    /**
     * Parse error response from Keycloak
     */
    async parseError(response) {
        try {
            return await response.json();
        }
        catch {
            return {
                error: 'unknown_error',
                error_description: response.statusText,
            };
        }
    }
    /**
     * Get the configured realm
     */
    get realm() {
        return this.config.realm;
    }
    /**
     * Get the base Keycloak URL
     */
    get baseUrl() {
        return this.config.keycloakUrl;
    }
}
/**
 * Custom error class for Keycloak API errors
 */
export class KeycloakApiError extends Error {
    status;
    details;
    constructor(status, message, details) {
        super(message);
        this.status = status;
        this.details = details;
        this.name = 'KeycloakApiError';
    }
    /**
     * Check if this is a "not found" error
     */
    isNotFound() {
        return this.status === 404;
    }
    /**
     * Check if this is a "conflict" error (resource already exists)
     */
    isConflict() {
        return this.status === 409;
    }
    /**
     * Check if this is an authorization error
     */
    isUnauthorized() {
        return this.status === 401;
    }
}
/**
 * Create a KeycloakClient instance from environment variables
 */
export function createClientFromEnv() {
    const url = process.env.KEYCLOAK_URL;
    const realm = process.env.KEYCLOAK_REALM;
    const username = process.env.KEYCLOAK_ADMIN_USERNAME;
    const password = process.env.KEYCLOAK_ADMIN_PASSWORD;
    if (!url || !realm || !username || !password) {
        throw new Error('Missing required environment variables: KEYCLOAK_URL, KEYCLOAK_REALM, KEYCLOAK_ADMIN_USERNAME, KEYCLOAK_ADMIN_PASSWORD');
    }
    return new KeycloakClient({
        keycloakUrl: url,
        realm,
        adminUsername: username,
        adminPassword: password,
    });
}
//# sourceMappingURL=client.js.map