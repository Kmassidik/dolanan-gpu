export function StatCard({
  label,
  value,
  note,
  icon,
}: {
  label: string;
  value: string;
  note?: string;
  icon?: string;
}) {
  return (
    <article className="stat-card">
      <div className="stat-head">
        <span className="stat-label">{label}</span>
        {icon && <img className="stat-icon" src={`/icons/${icon}.webp`} alt="" />}
      </div>
      <strong>{value}</strong>
      {note && <span className="stat-note">{note}</span>}
    </article>
  );
}
