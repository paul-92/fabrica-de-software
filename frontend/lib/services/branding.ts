import type { PlatformClients } from "../api";
import { ApiClient } from "../api/client";
import type { RuntimeBrandingDto } from "../api/dtos";
import { ApiResponseError } from "../api/errors";

const FIELDS = [
  "product_name",
  "short_name",
  "logo_url",
  "workspace_label",
  "footer_text",
] as const;

export class BrandingClient {
  constructor(private readonly api: ApiClient) {}

  async get(): Promise<RuntimeBrandingDto> {
    return parseRuntimeBranding(
      await this.api.request<unknown>({ path: "/api/v1/branding" }),
    );
  }
}

export function parseRuntimeBranding(payload: unknown): RuntimeBrandingDto {
  if (typeof payload !== "object" || payload === null || Array.isArray(payload)) {
    throw new ApiResponseError("Branding response is invalid.", payload);
  }
  const record = payload as Record<string, unknown>;
  if (
    Object.keys(record).length !== FIELDS.length ||
    FIELDS.some((field) => !(field in record)) ||
    typeof record.product_name !== "string" ||
    typeof record.short_name !== "string" ||
    (record.logo_url !== null && typeof record.logo_url !== "string") ||
    typeof record.workspace_label !== "string" ||
    typeof record.footer_text !== "string"
  ) {
    throw new ApiResponseError("Branding response is invalid.", payload);
  }
  return Object.freeze({
    product_name: record.product_name,
    short_name: record.short_name,
    logo_url: record.logo_url,
    workspace_label: record.workspace_label,
    footer_text: record.footer_text,
  });
}

type BrandingClients = Pick<PlatformClients, "branding">;

export interface BrandingLoader {
  getBranding(): Promise<RuntimeBrandingDto>;
}

export class BrandingService implements BrandingLoader {
  constructor(private readonly clients: BrandingClients) {}

  getBranding(): Promise<RuntimeBrandingDto> {
    return this.clients.branding.get();
  }
}

export function createBrandingLoader(
  clientsFactory: () => BrandingClients,
): BrandingLoader {
  let service: BrandingService | undefined;
  const getService = () => (service ??= new BrandingService(clientsFactory()));
  return { getBranding: () => getService().getBranding() };
}
