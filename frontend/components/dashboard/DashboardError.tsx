import { Button } from "../Button";

export function DashboardError({ retry }: { retry: () => void }) {
  return (
    <div className="dashboard-state dashboard-state--error" role="alert">
      <h2>Dashboard unavailable</h2>
      <p>We could not load operational data. Check the API and try again.</p>
      <Button onClick={retry}>Try again</Button>
    </div>
  );
}
