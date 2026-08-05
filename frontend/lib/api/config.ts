export type ApiConfig = Readonly<{
  baseUrl: string;
}>;

type PublicEnvironment = Readonly<Record<string, string | undefined>>;

export class ApiConfigurationError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ApiConfigurationError";
  }
}

export function createApiConfig(baseUrl: string | undefined): ApiConfig {
  if (!baseUrl?.trim()) {
    throw new ApiConfigurationError("NEXT_PUBLIC_API_URL is required.");
  }

  let parsed: URL;
  try {
    parsed = new URL(baseUrl);
  } catch {
    throw new ApiConfigurationError("NEXT_PUBLIC_API_URL must be an absolute URL.");
  }
  if (!(["http:", "https:"] as const).includes(parsed.protocol as "http:" | "https:")) {
    throw new ApiConfigurationError("NEXT_PUBLIC_API_URL must use HTTP or HTTPS.");
  }

  const normalizedBaseUrl = parsed.toString().replace(/\/+$/, "");
  return Object.freeze({ baseUrl: normalizedBaseUrl });
}

export function loadApiConfig(
  environment: PublicEnvironment = process.env,
): ApiConfig {
  return createApiConfig(environment.NEXT_PUBLIC_API_URL);
}
