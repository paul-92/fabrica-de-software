import Link from "next/link";
import { Card } from "../../components/Card";
import { PageHeader } from "../../components/layout/PageHeader";

export default function SettingsPage() {
  return <div className="page-stack">
    <PageHeader eyebrow="Preferências" title="Configurações" description="Configure integrações sem expor credenciais à camada de apresentação." />
    <Card eyebrow="Integração" title="Assistente de IA"><p>Consulte a instalação e a conexão do Codex.</p><Link href="/settings/ai">Abrir configurações do assistente</Link></Card>
  </div>;
}
