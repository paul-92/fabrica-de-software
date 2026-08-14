import type { ApiClient } from "../api/client";

export type AccessPrincipal = Readonly<{ user_id: string; organization_id: string; role: "admin" | "member" }>;
export type AccessUser = Readonly<{ user_id: string; email: string; status: "active" | "suspended"; role: "admin" | "member" }>;
export type QuotaView = Readonly<{ quota: null | { enabled: boolean; call_limit: number | null; token_limit: number | null; period: "monthly" }; usage: { calls: number; known_total_tokens: number; calls_with_unknown_usage: number; period_started_at: string; period_ends_at: string } }>;

export class AccessClient {
  constructor(private readonly api: ApiClient) {}
  session() { return this.api.request<AccessPrincipal>({ path: "api/v1/access/session" }); }
  login(email: string, password: string) { return this.api.request<AccessPrincipal>({ path: "api/v1/access/login", method: "POST", body: { email, password } }); }
  logout() { return this.api.request<unknown>({ path: "api/v1/access/logout", method: "POST" }); }
  users() { return this.api.request<{ items: AccessUser[] }>({ path: "api/v1/access/users" }); }
  invite(email: string, password: string, role: "admin" | "member" = "member") { return this.api.request<AccessUser>({ path: "api/v1/access/users", method: "POST", body: { email, password, role } }); }
  quota(userId?: string) { return this.api.request<QuotaView>({ path: userId ? `api/v1/ai-quotas/users/${userId}` : "api/v1/ai-quotas/me" }); }
  setQuota(userId: string, body: { enabled:boolean; call_limit:number|null; token_limit:number|null }) { return this.api.request({ path:`api/v1/ai-quotas/users/${userId}`,method:"PUT",body }); }
  setStatus(userId:string,status:"active"|"suspended") { return this.api.request({path:`api/v1/access/users/${userId}/status`,method:"PATCH",body:{status}}); }
}
