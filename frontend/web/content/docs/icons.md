# Icons and assets

The command center uses a 2.5D clay/toy icon set in transparent PNG and WebP.

## Files

```text
web/public/icons/
  gpu       model      queue     token
  bolt      database   shield    clock
  warning   spark      login     logout
```

Each icon has a 512px PNG and a 256px WebP. The favicon is:

```text
web/public/icons/gpu.png
```

```html
<link rel="icon" type="image/png" href="/icons/gpu.png" />
<link rel="apple-touch-icon" href="/icons/gpu.png" />
```

## Sizing options

### A — Compact

```css
.stat-icon  { width: 28px; height: 28px; }
.gpu-icon   { width: 34px; height: 34px; }
.brand-icon { width: 36px; height: 36px; }
```

### B — Soft tile

```css
.stat-icon {
  width: 44px;
  height: 44px;
  padding: 8px;
  background: #e9f8f1;
  border: 1px solid #d2f1e3;
  border-radius: 14px;
}
.gpu-icon { width: 48px; height: 48px; }
```

### C — Large

```css
.stat-icon { width: 56px; height: 56px; }
.gpu-icon  { width: 56px; height: 56px; }
```

### D — Split badge

```css
.stat-card { position: relative; padding-right: 86px; }
.stat-icon {
  position: absolute;
  right: 14px;
  top: 14px;
  width: 52px;
  height: 52px;
  padding: 7px;
  background: #f1f7f4;
  border-radius: 16px;
}
```

## Recommendation

Option B for statistic cards, 48px for GPU cards. It makes the icon set readable without dominating the telemetry.

## Generation notes

Generate on a solid magenta chroma background, one object per image, consistent camera and lighting. Remove the background, trim, and export with transparent alpha.
