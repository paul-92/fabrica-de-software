import { Card } from "../Card";

type MetricCardProps = {
  label: string;
  value: string;
  detail?: string;
};

export function MetricCard({ label, value, detail }: MetricCardProps) {
  return (
    <Card title={label} eyebrow="Métrica">
      <p className="dashboard-metric__value">{value}</p>
      {detail ? <p className="dashboard-metric__detail">{detail}</p> : null}
    </Card>
  );
}
