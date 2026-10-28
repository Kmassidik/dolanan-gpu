import { useMemo, useState } from "react";
import DOMPurify from "dompurify";
import { marked } from "marked";
import { Link, useParams } from "react-router-dom";
import gettingStarted from "../../content/docs/getting-started.md?raw";
import harness from "../../content/docs/harness.md?raw";
import apiDoc from "../../content/docs/api.md?raw";
import operations from "../../content/docs/operations.md?raw";
import security from "../../content/docs/security.md?raw";
import icons from "../../content/docs/icons.md?raw";

type Doc = { slug: string; title: string; icon: string; body: string };

const DOCS: Doc[] = [
  { slug: "getting-started", title: "Getting started", icon: "gpu", body: gettingStarted },
  { slug: "harness", title: "Harness integration", icon: "bolt", body: harness },
  { slug: "api", title: "API reference", icon: "queue", body: apiDoc },
  { slug: "operations", title: "Operations & deploy", icon: "database", body: operations },
  { slug: "security", title: "Security model", icon: "shield", body: security },
  { slug: "icons", title: "Icons & design", icon: "spark", body: icons },
];

export function Docs() {
  const { section } = useParams();
  const [query, setQuery] = useState("");
  const active = DOCS.find((doc) => doc.slug === (section ?? "getting-started")) ?? DOCS[0];
  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (!needle) return DOCS;
    return DOCS.filter((doc) => `${doc.title} ${doc.body}`.toLowerCase().includes(needle));
  }, [query]);
  const html = useMemo(
    () => DOMPurify.sanitize(marked.parse(active.body, { async: false })),
    [active],
  );

  return (
    <div className="docs-shell">
      <header className="docs-topbar">
        <Link className="brand" to="/docs">
          <img className="brand-icon" src="/icons/gpu.webp" alt="" />
          <span>gliccOps <small>docs</small></span>
        </Link>
        <div className="topbar-actions">
          <Link className="ghost" to="/">Command center</Link>
          <Link className="ghost" to="/login">Sign in</Link>
        </div>
      </header>

      <div className="docs-layout">
        <aside className="docs-sidebar">
          <label className="docs-search">
            <span>Search docs</span>
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Find a topic…"
            />
          </label>
          <nav>
            {filtered.map((doc) => (
              <Link
                key={doc.slug}
                to={`/docs/${doc.slug}`}
                className={doc.slug === active.slug ? "active" : ""}
              >
                <img src={`/icons/${doc.icon}.webp`} alt="" />
                {doc.title}
              </Link>
            ))}
            {filtered.length === 0 && <p className="empty">No matching docs.</p>}
          </nav>
          <p className="docs-note">Public docs. Secrets and internal credentials are omitted.</p>
        </aside>

        <article className="docs-article" dangerouslySetInnerHTML={{ __html: html }} />
      </div>
    </div>
  );
}
