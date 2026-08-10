export function DashboardSkeleton() {
  return (
    <div className="dashboard-skeleton" role="status" aria-live="polite">
      <span className="sr-only">Carregando painel</span>
      <div className="dashboard-skeleton__metrics">
        {Array.from({ length: 6 }, (_, index) => (
          <div className="dashboard-skeleton__block" key={index} />
        ))}
      </div>
      <div className="dashboard-skeleton__table" />
    </div>
  );
}
