/**
 * MCP Keycloak Tools Test Specifications
 *
 * These tests validate the tool implementations against expected behavior.
 * Tests use mocked HTTP responses to avoid requiring a live Keycloak instance.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// Mock fetch globally
const mockFetch = vi.fn();
global.fetch = mockFetch;

// Import after mocking
import { KeycloakClient } from '../src/keycloak/client.js';
import * as createClientTool from '../src/tools/create-client.js';
import * as getClientSecretTool from '../src/tools/get-client-secret.js';
import * as addGroupsMapperTool from '../src/tools/add-groups-mapper.js';
import * as listClientsTool from '../src/tools/list-clients.js';

// Test configuration
const TEST_CONFIG = {
  keycloakUrl: 'https://keycloak.test.com',
  realm: 'test-realm',
  adminUsername: 'admin',
  adminPassword: 'admin-password',
};

// Helper to create mock response
function mockResponse(data: unknown, status = 200, headers: Record<string, string> = {}) {
  return {
    ok: status >= 200 && status < 300,
    status,
    statusText: status === 200 ? 'OK' : 'Error',
    headers: {
      get: (name: string) => headers[name.toLowerCase()] ?? null,
    },
    json: () => Promise.resolve(data),
  };
}

// Helper to create token response
function mockTokenResponse() {
  return mockResponse({
    access_token: 'test-access-token',
    expires_in: 300,
    token_type: 'Bearer',
  });
}

describe('MCP Keycloak Tools', () => {
  let client: KeycloakClient;

  beforeEach(() => {
    vi.clearAllMocks();
    client = new KeycloakClient(TEST_CONFIG);
  });

  afterEach(() => {
    vi.resetAllMocks();
  });

  describe('create_client', () => {
    it('should have correct metadata', () => {
      expect(createClientTool.name).toBe('create_client');
      expect(createClientTool.description).toContain('confidential OIDC client');
    });

    it('should create a new client and return secret', async () => {
      // Mock token request
      mockFetch.mockResolvedValueOnce(mockTokenResponse());

      // Mock create client request (201 Created with Location header)
      mockFetch.mockResolvedValueOnce(
        mockResponse({}, 201, {
          location: 'https://keycloak.test.com/admin/realms/test-realm/clients/uuid-123',
        })
      );

      // Mock get secret request
      mockFetch.mockResolvedValueOnce(
        mockResponse({ type: 'secret', value: 'client-secret-value' })
      );

      const result = await createClientTool.execute(client, {
        clientId: 'test-client',
        redirectUris: ['http://localhost:8080/*'],
      });

      const parsed = JSON.parse(result);
      expect(parsed.success).toBe(true);
      expect(parsed.clientId).toBe('test-client');
      expect(parsed.secret).toBe('client-secret-value');
    });

    it('should handle existing client (409) idempotently', async () => {
      // Mock token request
      mockFetch.mockResolvedValueOnce(mockTokenResponse());

      // Mock create client request (409 Conflict)
      mockFetch.mockResolvedValueOnce(
        mockResponse({ errorMessage: 'Client already exists' }, 409)
      );

      // Mock search for existing client
      mockFetch.mockResolvedValueOnce(
        mockResponse([{ id: 'existing-uuid', clientId: 'test-client' }])
      );

      // Mock get secret for existing client
      mockFetch.mockResolvedValueOnce(
        mockResponse({ type: 'secret', value: 'existing-secret' })
      );

      const result = await createClientTool.execute(client, {
        clientId: 'test-client',
      });

      const parsed = JSON.parse(result);
      expect(parsed.success).toBe(true);
      expect(parsed.message).toContain('already exists');
    });

    it('should validate clientId format', () => {
      const validResult = createClientTool.inputSchema.safeParse({
        clientId: 'valid-client-123',
      });
      expect(validResult.success).toBe(true);

      const invalidResult = createClientTool.inputSchema.safeParse({
        clientId: 'invalid client!',
      });
      expect(invalidResult.success).toBe(false);
    });
  });

  describe('get_client_secret', () => {
    it('should have correct metadata', () => {
      expect(getClientSecretTool.name).toBe('get_client_secret');
      expect(getClientSecretTool.description).toContain('Retrieve the client secret');
    });

    it('should return secret for existing client', async () => {
      // Mock token request
      mockFetch.mockResolvedValueOnce(mockTokenResponse());

      // Mock search for client
      mockFetch.mockResolvedValueOnce(
        mockResponse([{ id: 'uuid-123', clientId: 'my-client' }])
      );

      // Mock get secret
      mockFetch.mockResolvedValueOnce(
        mockResponse({ type: 'secret', value: 'the-secret' })
      );

      const result = await getClientSecretTool.execute(client, {
        clientId: 'my-client',
      });

      const parsed = JSON.parse(result);
      expect(parsed.success).toBe(true);
      expect(parsed.secret).toBe('the-secret');
    });

    it('should return error for non-existent client', async () => {
      // Mock token request
      mockFetch.mockResolvedValueOnce(mockTokenResponse());

      // Mock search returns empty
      mockFetch.mockResolvedValueOnce(mockResponse([]));

      const result = await getClientSecretTool.execute(client, {
        clientId: 'nonexistent-client',
      });

      const parsed = JSON.parse(result);
      expect(parsed.success).toBe(false);
      expect(parsed.error).toContain('not found');
    });
  });

  describe('add_groups_mapper', () => {
    it('should have correct metadata', () => {
      expect(addGroupsMapperTool.name).toBe('add_groups_mapper');
      expect(addGroupsMapperTool.description).toContain('groups membership mapper');
    });

    it('should add mapper to existing client', async () => {
      // Mock token request
      mockFetch.mockResolvedValueOnce(mockTokenResponse());

      // Mock search for client
      mockFetch.mockResolvedValueOnce(
        mockResponse([{ id: 'uuid-123', clientId: 'my-client' }])
      );

      // Mock add mapper (201 Created)
      mockFetch.mockResolvedValueOnce(mockResponse({}, 201));

      const result = await addGroupsMapperTool.execute(client, {
        clientId: 'my-client',
      });

      const parsed = JSON.parse(result);
      expect(parsed.success).toBe(true);
      expect(parsed.alreadyExisted).toBe(false);
    });

    it('should handle existing mapper (409) idempotently', async () => {
      // Mock token request
      mockFetch.mockResolvedValueOnce(mockTokenResponse());

      // Mock search for client
      mockFetch.mockResolvedValueOnce(
        mockResponse([{ id: 'uuid-123', clientId: 'my-client' }])
      );

      // Mock add mapper (409 Conflict)
      mockFetch.mockResolvedValueOnce(
        mockResponse({ errorMessage: 'Mapper already exists' }, 409)
      );

      const result = await addGroupsMapperTool.execute(client, {
        clientId: 'my-client',
      });

      const parsed = JSON.parse(result);
      expect(parsed.success).toBe(true);
      expect(parsed.alreadyExisted).toBe(true);
    });

    it('should accept custom mapper and claim names', async () => {
      // Mock token request
      mockFetch.mockResolvedValueOnce(mockTokenResponse());

      // Mock search for client
      mockFetch.mockResolvedValueOnce(
        mockResponse([{ id: 'uuid-123', clientId: 'my-client' }])
      );

      // Mock add mapper
      mockFetch.mockResolvedValueOnce(mockResponse({}, 201));

      const result = await addGroupsMapperTool.execute(client, {
        clientId: 'my-client',
        mapperName: 'custom-groups',
        claimName: 'user_groups',
        fullPath: true,
      });

      const parsed = JSON.parse(result);
      expect(parsed.success).toBe(true);
      expect(parsed.mapperName).toBe('custom-groups');
    });
  });

  describe('list_clients', () => {
    it('should have correct metadata', () => {
      expect(listClientsTool.name).toBe('list_clients');
      expect(listClientsTool.description).toContain('List Keycloak clients');
    });

    it('should return list of clients', async () => {
      // Mock token request
      mockFetch.mockResolvedValueOnce(mockTokenResponse());

      // Mock list clients
      mockFetch.mockResolvedValueOnce(
        mockResponse([
          { id: 'uuid-1', clientId: 'client-1', name: 'Client One', enabled: true, protocol: 'openid-connect' },
          { id: 'uuid-2', clientId: 'client-2', name: 'Client Two', enabled: false, protocol: 'openid-connect' },
        ])
      );

      const result = await listClientsTool.execute(client, {});

      const parsed = JSON.parse(result);
      expect(parsed.success).toBe(true);
      expect(parsed.total).toBe(2);
      expect(parsed.clients).toHaveLength(2);
      expect(parsed.clients[0].clientId).toBe('client-1');
    });

    it('should support search filter', async () => {
      // Mock token request
      mockFetch.mockResolvedValueOnce(mockTokenResponse());

      // Mock filtered list
      mockFetch.mockResolvedValueOnce(
        mockResponse([
          { id: 'uuid-1', clientId: 'my-app', name: 'My App', enabled: true, protocol: 'openid-connect' },
        ])
      );

      const result = await listClientsTool.execute(client, {
        search: 'my-app',
      });

      const parsed = JSON.parse(result);
      expect(parsed.success).toBe(true);
      expect(parsed.total).toBe(1);
    });

    it('should support pagination', async () => {
      // Mock token request
      mockFetch.mockResolvedValueOnce(mockTokenResponse());

      // Mock paginated list
      mockFetch.mockResolvedValueOnce(mockResponse([]));

      await listClientsTool.execute(client, {
        first: 10,
        max: 5,
      });

      // Verify fetch was called with pagination params
      const fetchCalls = mockFetch.mock.calls;
      const listCall = fetchCalls.find((call) =>
        call[0].includes('/clients?') && call[0].includes('first=10')
      );
      expect(listCall).toBeDefined();
      expect(listCall[0]).toContain('max=5');
    });
  });
});

describe('Token Management', () => {
  it('should cache tokens and reuse them', async () => {
    const client = new KeycloakClient(TEST_CONFIG);

    // First request gets token
    mockFetch.mockResolvedValueOnce(mockTokenResponse());
    mockFetch.mockResolvedValueOnce(mockResponse([]));

    await listClientsTool.execute(client, {});

    // Second request should reuse cached token
    mockFetch.mockResolvedValueOnce(mockResponse([]));

    await listClientsTool.execute(client, {});

    // Token should only be fetched once
    const tokenCalls = mockFetch.mock.calls.filter((call) =>
      call[0].includes('/protocol/openid-connect/token')
    );
    expect(tokenCalls).toHaveLength(1);
  });

  it('should refresh token on 401', async () => {
    const client = new KeycloakClient(TEST_CONFIG);

    // First token
    mockFetch.mockResolvedValueOnce(mockTokenResponse());

    // Request fails with 401
    mockFetch.mockResolvedValueOnce(mockResponse({ error: 'invalid_token' }, 401));

    // New token
    mockFetch.mockResolvedValueOnce(mockTokenResponse());

    // Retry succeeds
    mockFetch.mockResolvedValueOnce(mockResponse([]));

    const result = await listClientsTool.execute(client, {});
    const parsed = JSON.parse(result);
    expect(parsed.success).toBe(true);
  });
});
