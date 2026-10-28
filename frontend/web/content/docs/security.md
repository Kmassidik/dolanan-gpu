# Security model

This page describes the public security design. Secrets and internal credentials are deliberately omitted.

## Dashboard authentication

- Passwords hashed with **Argon2id**
- Server-side sessions stored in SQLite
- Session token: 32 random bytes; only its SHA-256 hash is stored
- Session cookie: `HttpOnly`, `Secure`, `SameSite=Lax`
- Idle expiry: 12 hours
- Absolute expiry: 7 days

## CSRF

State-changing dashboard requests require:

```text
X-CSRF-Token: <glicc_csrf cookie value>
```

The CSRF cookie is readable by the frontend; the session cookie is not.

## Login rate limit

```text
5 failed attempts per IP / 15 minutes
```

Failures are recorded in `login_attempts`; successful logins are audited.

## API keys

- Per-client keys, generated in the UI
- 32 random bytes plus a `gk_` prefix
- Only SHA-256 hashes are stored
- Plaintext is shown once
- Revocation is immediate for new requests
- Per-key queue and requests/minute limits

## Network

- nginx binds to loopback only
- FastAPI binds to loopback only
- llama.cpp binds to loopback only
- Cloudflare provides public TLS
- The public UI is the only public dashboard route

## Browser hardening

- Content Security Policy
- `X-Frame-Options: DENY`
- `X-Content-Type-Options: nosniff`
- `Referrer-Policy: same-origin`
- No external CDN scripts in the compiled UI

## Operational rules

- Do not put keys or passwords in Git.
- Rotate a key immediately if it leaks.
- Keep the gateway admin/key file at mode `600`.
- Back up SQLite before schema changes.
- Treat the inference API as one-slot capacity; queue behavior is part of the security boundary.
