"use client";
import { useEffect, useState } from "react";
import type { AccessClient, AccessPrincipal, QuotaView } from "../../lib/services/access";

export function BetaUsagePanel({access,principal}:{access:AccessClient;principal:AccessPrincipal}) {
  const [quota,setQuota]=useState<QuotaView|null>(null);
  useEffect(()=>{if(typeof access.quota!=="function") return; access.quota().then(setQuota,()=>setQuota(null));},[access,principal]);
  const usage=quota?.usage; const policy=quota?.quota;
  return <details><summary>Consumo de IA</summary><p>{usage ? `${usage.calls} / ${policy?.call_limit ?? "sem limite"} chamadas; ${usage.known_total_tokens} / ${policy?.token_limit ?? "sem limite"} tokens conhecidos.` : "Quota não configurada."}</p>{usage?.calls_with_unknown_usage ? <p>{usage.calls_with_unknown_usage} chamada(s) têm uso desconhecido; o saldo de tokens não é exato.</p>:null}</details>;
}
