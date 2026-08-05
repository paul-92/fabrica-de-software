import { loadBrandConfig } from "../branding/config";
import { BrandMark } from "../components/BrandMark";
import { Button } from "../components/Button";
import { Card } from "../components/Card";
import { StatusBadge } from "../components/StatusBadge";
import { ThemeToggle } from "../components/ThemeToggle";

export default function Home() {
  const brand = loadBrandConfig();

  return (
    <main className="shell">
      <header className="shell__header">
        <BrandMark brand={brand} />
        <ThemeToggle />
      </header>

      <section className="hero">
        <div className="hero__copy">
          <p className="eyebrow">Engineering operations, clearly composed</p>
          <h1>Da intenção à evidência.</h1>
          <p className="hero__description">
            Uma fundação visual neutra para acompanhar planejamento, execução,
            conhecimento e qualidade sem acoplar apresentação ao Core.
          </p>
          <Button>Explorar fundação</Button>
        </div>
        <Card title="Sistema operacional" eyebrow="Prévia" action={<StatusBadge status="success">Ativo</StatusBadge>}>
          <p className="metric">24</p>
          <p>execuções rastreáveis na futura visão operacional.</p>
          <div className="signal__line" />
        </Card>
      </section>

      <section className="preview-grid" aria-label="Design system preview">
        <Card title="Planning" eyebrow="Contexto">
          Conhecimento aprendido chega como contexto, nunca como comando.
        </Card>
        <Card title="Quality gates" eyebrow="Confiança">
          <div className="status-row">
            <StatusBadge status="success">Approved</StatusBadge>
            <StatusBadge status="warning">Pending</StatusBadge>
            <StatusBadge status="danger">Blocked</StatusBadge>
          </div>
        </Card>
        <Card title="White-label" eyebrow="Identidade">
          Nome, marca e cores entram por configuração e tokens reutilizáveis.
        </Card>
      </section>
    </main>
  );
}
