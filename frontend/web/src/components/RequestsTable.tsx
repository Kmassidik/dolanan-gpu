import type { RequestRow } from "../types";

export function RequestsTable({ requests }: { requests: RequestRow[] }) {
  if (!requests.length) {
    return <p className="empty">No request records yet. Gateway traffic will appear here.</p>;
  }
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Request</th>
            <th>Model</th>
            <th>Status</th>
            <th>Tokens</th>
            <th>Decode</th>
          </tr>
        </thead>
        <tbody>
          {requests.slice(0, 8).map((row) => (
            <tr key={row.request_id}>
              <td className="mono">{row.request_id.slice(0, 12)}</td>
              <td>{row.model ?? "—"}</td>
              <td><span className={`tag ${row.status}`}>{row.status}</span></td>
              <td className="mono">{row.completion_tokens}</td>
              <td className="mono">{row.decode_tps ? `${row.decode_tps.toFixed(1)} t/s` : "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
