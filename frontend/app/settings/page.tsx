import Link from "next/link";
import { Card } from "../../components/Card";
import { PageHeader } from "../../components/layout/PageHeader";

export default function SettingsPage() {
  return <div className="page-stack">
    <PageHeader eyebrow="Configuration" title="Settings" description="Configure platform integrations without exposing credentials to the presentation layer." />
    <Card eyebrow="Runtime" title="AI Runtime"><p>Check Codex installation and connection status.</p><Link href="/settings/ai">Open AI Runtime settings</Link></Card>
  </div>;
}
