import { useEffect, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { api, ApiError } from "../api";
import { useAuth } from "../auth";

type KeyRow = {
  name: string;
  prefix: string;
  rpm: number;
  created_at: number | null;
  enabled: boolean;
  admin: boolean;
};

export function Keys() {
  const { user, logout } = useAuth();
  const [keys, setKeys] = useState<KeyRow[]>([]);
  const [name, setName] = useState("");
  const [rpm, setRpm] = useState(60);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [created, setCreated] = useState<string>("");
  const [copied, setCopied] = useState(false);

  async function load() {
    try {
      const data = await api<{ keys: KeyRow[] }>("/api/keys");
      setKeys(data.keys);
      setError("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to load keys.");
    }
  }

  useEffect(() => {
    void load();
  }, []);

  async function create(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setCreated("");
    try {
      const data = await api<{ key: string }>("/api/keys", {
        method: "POST",
        body: JSON.stringify({ name, rpm }),
      });
      setCreated(data.key);
      setName("");
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to create key.");
    } finally {
      setBusy(false);
    }
  }

  async function revoke(keyName: string) {
    setError("");
    try {
      await api(`/api/keys/${encodeURIComponent(keyName)}`, { method: "DELETE" });
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to revoke key.");
    }
  }

  async function copy() {
    await navigator.clipboard.writeText(created);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1800);
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand">
          <img className="brand-icon" src="/icons/gpu.webp" alt="" />
          <span>gliccOps</span>
        </div>
        <div className="topbar-actions">
          <Link className="ghost" to="/">Dashboard</Link>
          <span className="user">{user?.username}</span>
          <button className="ghost" onClick={() => void logout()}>
            <img className="button-icon" src="/icons/logout.webp" alt="" /> Sign out
          </button>
        </div>
      </header>

      <main>
        <section className="hero">
          <div>
            <p className="eyebrow">Access control</p>
            <h1>API keys</h1>
            <p className="muted">Per-client keys for the OpenAI-compatible endpoint.</p>
          </div>
          <span className="fleet-state">gateway</span>
        </section>

        <section className="split">
          <div className="panel">
            <div className="panel-head">
              <h2><img className="panel-icon" src="/icons/shield.webp" alt="" /> Active keys</h2>
              <span className="muted">{keys.length} total</span>
            </div>
            {keys.length === 0 ? (
              <p className="empty">No keys yet. Create one to connect a harness.</p>
            ) : (
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr><th>Name</th><th>Prefix</th><th>RPM</th><th>Created</th><th /></tr>
                  </thead>
                  <tbody>
                    {keys.map((key) => (
                      <tr key={key.name}>
                        <td>{key.name}</td>
                        <td className="mono">{key.prefix}…</td>
                        <td className="mono">{key.rpm}</td>
                        <td>{key.created_at ? new Date(key.created_at * 1000).toLocaleDateString() : "—"}</td>
                        <td><button className="danger" onClick={() => void revoke(key.name)}>Revoke</button></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          <div className="panel">
            <div className="panel-head">
              <h2><img className="panel-icon" src="/icons/login.webp" alt="" /> Create key</h2>
            </div>
            <form className="stack" onSubmit={create}>
              <label>
                Client name
                <input
                  placeholder="opencode-laptop"
                  value={name}
                  onChange={(event) => setName(event.target.value)}
                  required
                />
              </label>
              <label>
                Requests / minute
                <input
                  type="number"
                  min={1}
                  max={600}
                  value={rpm}
                  onChange={(event) => setRpm(Number(event.target.value))}
                  required
                />
              </label>
              {error && <p className="form-error" role="alert">{error}</p>}
              <button className="primary" disabled={busy}>
                {busy ? "Creating…" : "Create API key"}
              </button>
            </form>

            {created && (
              <div className="secret-box">
                <span className="eyebrow">Copy now — shown once</span>
                <code>{created}</code>
                <button className="ghost" onClick={() => void copy()}>
                  {copied ? "Copied" : "Copy"}
                </button>
              </div>
            )}
          </div>
        </section>
      </main>
    </div>
  );
}
