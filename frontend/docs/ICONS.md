# Icon Sizing Options

Current CSS lives in `web/src/styles.css`.

## Option A — Compact (current)

```css
.stat-icon  { width: 28px; height: 28px; }
.gpu-icon   { width: 34px; height: 34px; }
.brand-icon { width: 36px; height: 36px; }
```

Small, dense. Best if cards must stay short.

## Option B — Soft tile (recommended)

Icon 44px inside a 56px rounded tile with a pale green background.

```css
.stat-icon {
  width: 44px;
  height: 44px;
  padding: 8px;
  box-sizing: content-box;
  background: #e9f8f1;
  border: 1px solid #d2f1e3;
  border-radius: 14px;
}
.gpu-icon {
  width: 48px;
  height: 48px;
}
```

Cards grow about 12–16px in height. Looks deliberate and still leaves room for numbers.

## Option C — Large standalone

```css
.stat-icon {
  width: 56px;
  height: 56px;
  padding: 4px;
}
.gpu-icon {
  width: 56px;
  height: 56px;
}
```

Bigger visual hit; cards get noticeably taller. Use a two-column stats grid on tablet.

## Option D — Split badge

Icon on the right as a 64px badge, value left.

```css
.stat-card {
  position: relative;
  padding-right: 86px;
}
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

Most expressive, but the card layout changes shape.

## Recommendation

Use **Option B** for stat cards and **48px** for GPU cards. It makes the icon set visible without turning the dashboard into a toy collection.
