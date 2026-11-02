import type { KeyRow } from "../types";

function compact(value: number) {
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `${(value / 1_000).toFixed(1)}k`;
  return value.toString();
}

export function KeyUsageTable({ keys }: { keys: KeyRow[] }) {
  if (!keys.length) {
    return <p className="empty">No API keys yet. Usage totals appear here once one is created.</p>;
  }
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Key</th>
            <th>Requests</th>
            <th>Tokens</th>
            <th>Last used</th>
          </tr>
        </thead>
        <tbody>
          {keys.map((key) => (
            <tr key={key.name}>
              <td>{key.name}</td>
              <td className="mono">{compact(key.total_requests)}</td>
              <td className="mono">{compact(key.total_tokens)}</td>
              <td>{key.last_used_at ? new Date(key.last_used_at * 1000).toLocaleString() : "never"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
