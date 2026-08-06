export type ApiConfig = Readonly<{
  baseUrl: string;
}>;

export class ApiConfigurationError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ApiConfigurationError";
  }
}

export function createApiConfig(baseUrl: string | undefined): ApiConfig {
  const trimmedBaseUrl = baseUrl?.trim();

  if (!trimmedBaseUrl) {
    throw new ApiConfigurationError("NEXT_PUBLIC_API_URL is required.");
  }

  let parsed: URL;

  try {
    parsed = new URL(trimmedBaseUrl);
  } catch {
    throw new ApiConfigurationError(
      "NEXT_PUBLIC_API_URL must be an absolute URL.",
    );
  }

  if (parsed.protocol !== "http:" && parsed.protocol !== "https:") {
    throw new ApiConfigurationError(
      "NEXT_PUBLIC_API_URL must use HTTP or HTTPS.",
    );
  }

  const normalizedBaseUrl = parsed.toString().replace(/\/+$/, "");

  return Object.freeze({
    baseUrl: normalizedBaseUrl,
  });
}

export function loadApiConfig(
  baseUrl: string | undefined = process.env.NEXT_PUBLIC_API_URL,
): ApiConfig {
  return createApiConfig(baseUrl);
}