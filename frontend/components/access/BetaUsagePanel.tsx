"use client";
import { useEffect, useState } from "react";
import type { AccessClient, AccessPrincipal, AccessUser, QuotaView } from "../../lib/services/access";

export function BetaUsagePanel({access,principal}:{access:AccessClient;principal:AccessPrincipal}) {
  const [quota,setQuota]=useState<QuotaView|null>(null); const [users,setUsers]=useState<AccessUser[]>([]);
  useEffect(()=>{if(typeof access.quota!=="function") return; access.quota().then(setQuota,()=>setQuota(null)); if(principal.role==="admin" && typeof access.users==="function") access.users().then(v=>setUsers(v.items),()=>setUsers([]));},[access,principal]);
  const usage=quota?.usage; const policy=quota?.quota;
  return <details><summary>Consumo de IA</summary><p>{usage ? `${usage.calls} / ${policy?.call_limit ?? "sem limite"} chamadas; ${usage.known_total_tokens} / ${policy?.token_limit ?? "sem limite"} tokens conhecidos.` : "Quota não configurada."}</p>{usage?.calls_with_unknown_usage ? <p>{usage.calls_with_unknown_usage} chamada(s) têm uso desconhecido; o saldo de tokens não é exato.</p>:null}{principal.role==="admin" ? users.map(user=><div key={user.user_id}><span>{user.email} · {user.role} · {user.status}</span> <button type="button" onClick={async()=>{await access.setStatus(user.user_id,user.status==="active"?"suspended":"active");setUsers((await access.users()).items);}}>{user.status==="active"?"Suspender":"Reativar"}</button> <button type="button" onClick={async()=>{const calls=window.prompt("Limite mensal de chamadas (vazio = ilimitado)");const tokens=window.prompt("Limite mensal de tokens conhecidos (vazio = ilimitado)");await access.setQuota(user.user_id,{enabled:true,call_limit:calls?Number(calls):null,token_limit:tokens?Number(tokens):null});}}>Editar quota</button></div>) : null}</details>;
}
