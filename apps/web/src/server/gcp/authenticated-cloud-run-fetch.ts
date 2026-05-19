import { GoogleAuth } from "google-auth-library";

type IdTokenClient = Awaited<ReturnType<GoogleAuth["getIdTokenClient"]>>;

const DEFAULT_LOCAL_API_BASE_URL = "http://localhost:8000";
const DEFAULT_AUTH_MODE = "auto";

const auth = new GoogleAuth();
const clientsByAudience = new Map<string, Promise<IdTokenClient>>();

function getApiBaseUrl(): URL {
  const rawBaseUrl = process.env.HOU53_API_BASE_URL || DEFAULT_LOCAL_API_BASE_URL;
  return new URL(rawBaseUrl.replace(/\/$/, ""));
}

export function shouldAuthenticateApiRequest(baseUrl: URL, authMode = process.env.HOU53_API_AUTH_MODE): boolean {
  const mode = (authMode || DEFAULT_AUTH_MODE).toLowerCase();

  if (mode === "google") {
    return true;
  }
  if (mode === "none" || mode === "false" || mode === "disabled") {
    return false;
  }

  return baseUrl.protocol === "https:" && baseUrl.hostname.endsWith(".run.app");
}

function getClientForAudience(audience: string): Promise<IdTokenClient> {
  let client = clientsByAudience.get(audience);

  if (!client) {
    client = auth.getIdTokenClient(audience);
    clientsByAudience.set(audience, client);
  }

  return client;
}

async function applyAuthHeaders(headers: Headers, audience: string): Promise<void> {
  const client = await getClientForAudience(audience);
  const authHeaders = await client.getRequestHeaders(audience);

  new Headers(authHeaders as HeadersInit).forEach((value, key) => {
    headers.set(key, value);
  });
}

export async function authenticatedCloudRunFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const baseUrl = getApiBaseUrl();
  const url = new URL(path, baseUrl);

  if (!shouldAuthenticateApiRequest(baseUrl)) {
    return fetch(url, init);
  }

  const headers = new Headers(init.headers);
  await applyAuthHeaders(headers, baseUrl.origin);

  return fetch(url, {
    ...init,
    headers,
  });
}
