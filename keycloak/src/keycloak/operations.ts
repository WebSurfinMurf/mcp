/**
 * Keycloak Admin API Operations
 * High-level functions for client management
 */

import { KeycloakClient, KeycloakApiError } from './client.js';
import {
  KeycloakClient as ClientRepresentation,
  ClientListItem,
  ClientSecret,
  ProtocolMapper,
  CreateClientInput,
  CreateClientResult,
  GetClientSecretResult,
  AddGroupsMapperInput,
  AddGroupsMapperResult,
  ListClientsInput,
  ListClientsResult,
} from './types.js';
import {
  clientsEndpoint,
  clientsSearchEndpoint,
  clientSecretEndpoint,
  protocolMappersEndpoint,
} from './endpoints.js';

/**
 * Find a client by clientId (the human-readable identifier)
 * Returns the internal UUID if found, null otherwise
 */
export async function findClientByClientId(
  client: KeycloakClient,
  clientId: string
): Promise<string | null> {
  const url = clientsSearchEndpoint(client.baseUrl, client.realm, { clientId });
  const clients = await client.get<ClientListItem[]>(url);

  // Find exact match (search is case-insensitive and partial)
  const match = clients.find((c) => c.clientId === clientId);
  return match?.id ?? null;
}

/**
 * Create a new OIDC client in Keycloak
 */
export async function createClient(
  client: KeycloakClient,
  input: CreateClientInput
): Promise<CreateClientResult> {
  const url = clientsEndpoint(client.baseUrl, client.realm);

  // Build client representation
  const clientRep: ClientRepresentation = {
    clientId: input.clientId,
    name: input.name ?? input.clientId,
    description: input.description,
    enabled: true,
    protocol: 'openid-connect',
    publicClient: false, // Confidential client
    clientAuthenticatorType: 'client-secret',
    redirectUris: input.redirectUris ?? [],
    webOrigins: input.webOrigins ?? [],
    standardFlowEnabled: input.standardFlowEnabled ?? true,
    directAccessGrantsEnabled: input.directAccessGrantsEnabled ?? false,
    serviceAccountsEnabled: input.serviceAccountsEnabled ?? false,
    fullScopeAllowed: true,
  };

  try {
    // Create the client and get location header
    const location = await client.postAndGetLocation(url, clientRep);

    // Extract internal ID from location header
    // Location format: .../admin/realms/{realm}/clients/{uuid}
    const internalId = location?.split('/').pop();

    if (!internalId) {
      throw new Error('Failed to get internal client ID from response');
    }

    // Fetch the client secret
    const secretUrl = clientSecretEndpoint(client.baseUrl, client.realm, internalId);
    const secretResponse = await client.get<ClientSecret>(secretUrl);

    return {
      success: true,
      clientId: input.clientId,
      internalId,
      secret: secretResponse.value,
      message: `Client '${input.clientId}' created successfully`,
    };
  } catch (error) {
    if (error instanceof KeycloakApiError && error.isConflict()) {
      // Client already exists - find it and return its info
      const existingId = await findClientByClientId(client, input.clientId);
      if (existingId) {
        const secretUrl = clientSecretEndpoint(client.baseUrl, client.realm, existingId);
        const secretResponse = await client.get<ClientSecret>(secretUrl);

        return {
          success: true,
          clientId: input.clientId,
          internalId: existingId,
          secret: secretResponse.value,
          message: `Client '${input.clientId}' already exists (idempotent success)`,
        };
      }
    }
    throw error;
  }
}

/**
 * Get the secret for an existing client
 */
export async function getClientSecret(
  client: KeycloakClient,
  clientId: string
): Promise<GetClientSecretResult> {
  // Find the client by clientId
  const internalId = await findClientByClientId(client, clientId);

  if (!internalId) {
    return {
      success: false,
      clientId,
      secret: '',
      message: `Client '${clientId}' not found`,
    };
  }

  // Get the secret
  const url = clientSecretEndpoint(client.baseUrl, client.realm, internalId);
  const secretResponse = await client.get<ClientSecret>(url);

  return {
    success: true,
    clientId,
    secret: secretResponse.value,
    message: `Secret retrieved for client '${clientId}'`,
  };
}

/**
 * Add a groups mapper to a client's protocol mappers
 * This adds group membership to the token claims
 */
export async function addGroupsMapper(
  client: KeycloakClient,
  input: AddGroupsMapperInput
): Promise<AddGroupsMapperResult> {
  // Find the client
  const internalId = await findClientByClientId(client, input.clientId);

  if (!internalId) {
    return {
      success: false,
      clientId: input.clientId,
      mapperName: input.mapperName ?? 'groups',
      alreadyExists: false,
      message: `Client '${input.clientId}' not found`,
    };
  }

  const mapperName = input.mapperName ?? 'groups';
  const claimName = input.claimName ?? 'groups';
  const fullPath = input.fullPath ?? false;

  // Build the protocol mapper
  const mapper: ProtocolMapper = {
    name: mapperName,
    protocol: 'openid-connect',
    protocolMapper: 'oidc-group-membership-mapper',
    consentRequired: false,
    config: {
      'claim.name': claimName,
      'full.path': fullPath.toString(),
      'id.token.claim': 'true',
      'access.token.claim': 'true',
      'userinfo.token.claim': 'true',
    },
  };

  const url = protocolMappersEndpoint(client.baseUrl, client.realm, internalId);

  try {
    await client.post(url, mapper);

    return {
      success: true,
      clientId: input.clientId,
      mapperName,
      alreadyExists: false,
      message: `Groups mapper '${mapperName}' added to client '${input.clientId}'`,
    };
  } catch (error) {
    // 409 Conflict means mapper already exists - treat as success (idempotent)
    if (error instanceof KeycloakApiError && error.isConflict()) {
      return {
        success: true,
        clientId: input.clientId,
        mapperName,
        alreadyExists: true,
        message: `Groups mapper '${mapperName}' already exists on client '${input.clientId}' (idempotent success)`,
      };
    }
    throw error;
  }
}

/**
 * List clients with optional filtering
 */
export async function listClients(
  client: KeycloakClient,
  input: ListClientsInput = {}
): Promise<ListClientsResult> {
  const url = clientsSearchEndpoint(client.baseUrl, client.realm, {
    search: input.search,
    first: input.first ?? 0,
    max: input.max ?? 100,
  });

  const clients = await client.get<ClientListItem[]>(url);

  return {
    success: true,
    clients: clients.map((c) => ({
      id: c.id,
      clientId: c.clientId,
      name: c.name,
      enabled: c.enabled,
      protocol: c.protocol,
    })),
    total: clients.length,
    message: `Found ${clients.length} client(s)`,
  };
}
