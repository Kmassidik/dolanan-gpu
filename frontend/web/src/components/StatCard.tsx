export function StatCard({
  label,
  value,
  note,
}: {
  label: string;
  value: string;
  note?: string;
}) {
  return (
    <article className="stat-card">
      <span className="stat-label">{label}</span>
      <strong>{value}</strong>
      {note && <span className="stat-note">{note}</span>}
    </article>
  );
}
