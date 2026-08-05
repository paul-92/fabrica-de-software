import { Card } from "../Card";
import { StatusBadge } from "../StatusBadge";
import { PageHeader } from "./PageHeader";

type SectionPlaceholderProps = {
  eyebrow: string;
  title: string;
  description: string;
};

export function SectionPlaceholder({
  eyebrow,
  title,
  description,
}: SectionPlaceholderProps) {
  return (
    <div className="page-stack">
      <PageHeader eyebrow={eyebrow} title={title} description={description} />
      <div className="content-grid">
        <Card
          title="Foundation ready"
          eyebrow="Sprint 22.2"
          action={<StatusBadge status="success">Available</StatusBadge>}
        >
          Esta área já compartilha navegação, tema e identidade configurável.
          Os dados funcionais serão adicionados nas próximas sprints.
        </Card>
        <Card title="Public boundary" eyebrow="Architecture">
          A apresentação consumirá somente contratos públicos da Application/API.
        </Card>
      </div>
    </div>
  );
}
