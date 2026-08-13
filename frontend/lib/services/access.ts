import type { ApiClient } from "../api/client";

export type AccessPrincipal = Readonly<{ user_id: string; organization_id: string; role: "admin" | "member" }>;

export class AccessClient {
  constructor(private readonly api: ApiClient) {}
  session() { return this.api.request<AccessPrincipal>({ path: "api/v1/access/session" }); }
  login(email: string, password: string) { return this.api.request<AccessPrincipal>({ path: "api/v1/access/login", method: "POST", body: { email, password } }); }
  logout() { return this.api.request<unknown>({ path: "api/v1/access/logout", method: "POST" }); }
}
