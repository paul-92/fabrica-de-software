import { Button } from "../Button";

export function DashboardError({ retry }: { retry: () => void }) {
  return (
    <div className="dashboard-state dashboard-state--error" role="alert">
      <h2>Visão geral indisponível</h2>
      <p>Não foi possível carregar os dados. Verifique a API e tente novamente.</p>
      <Button onClick={retry}>Tentar novamente</Button>
    </div>
  );
}
