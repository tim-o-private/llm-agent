// Shared UI primitives used across all wireframe scenes
const { useState, useEffect, useRef, useMemo } = React;

// Hand-drawn SVG arrow pointing from (x1,y1) to (x2,y2)
function HandArrow({ x1, y1, x2, y2, color = 'var(--accent)', curve = 20 }) {
  const mx = (x1 + x2) / 2;
  const my = (y1 + y2) / 2 - curve;
  const d = `M ${x1} ${y1} Q ${mx} ${my} ${x2} ${y2}`;
  return (
    <svg style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', pointerEvents: 'none', overflow: 'visible' }}>
      <path d={d} stroke={color} strokeWidth="1.5" fill="none" strokeDasharray="0" filter="url(#roughen)" />
      <polygon points={`${x2},${y2} ${x2-6},${y2-3} ${x2-5},${y2+4}`} fill={color} filter="url(#roughen)" />
    </svg>
  );
}

// Sketchy rectangle (roughed border via filter)
function Rough({ children, style, className = '', ...rest }) {
  return (
    <div className={`rough ${className}`} style={style} {...rest}>
      {children}
    </div>
  );
}

// Placeholder text block
function Lines({ count = 3, widths }) {
  const ws = widths || Array.from({ length: count }, (_, i) => ['long','med','long','short'][i % 4]);
  return (
    <div>
      {ws.map((w, i) => <div key={i} className={`placeholder-line ${w}`} />)}
    </div>
  );
}

// File/folder tree row
function TreeRow({ level = 0, icon = '▸', name, active, type = 'folder', badge }) {
  const ICONS = {
    folder: '▸',
    folder_open: '▾',
    file: '·',
    md: 'md',
    pdf: 'pdf',
    csv: 'csv',
    img: 'img',
    flow: '»',
  };
  return (
    <div className={`tree-row ${active ? 'active' : ''}`} style={{ paddingLeft: 8 + level * 14 }}>
      <span style={{ display: 'inline-block', width: 22, color: 'var(--ink-faint)', fontSize: 10 }}>{ICONS[type] || icon}</span>
      <span>{name}</span>
      {badge && <span style={{ marginLeft: 6, fontSize: 9, color: 'var(--accent)' }}>{badge}</span>}
    </div>
  );
}

// A labeled region box (for annotating wireframe zones)
function Zone({ label, children, style }) {
  return (
    <div style={{ position: 'relative', ...style }}>
      {label && (
        <div style={{
          position: 'absolute', top: -8, left: 10, padding: '0 6px',
          background: 'var(--panel)', fontFamily: 'JetBrains Mono, monospace',
          fontSize: 10, color: 'var(--ink-faint)', letterSpacing: '0.1em', textTransform: 'uppercase', zIndex: 2
        }}>{label}</div>
      )}
      {children}
    </div>
  );
}

// Window chrome (macOS-style, low-fi)
function AppChrome({ url = 'clarity.app/vault', right }) {
  return (
    <div className="app-chrome">
      <div className="tl" style={{ background: 'var(--danger)' }} />
      <div className="tl" style={{ background: '#c9a14a' }} />
      <div className="tl" style={{ background: 'var(--success)' }} />
      <div className="app-url">{url}</div>
      {right}
    </div>
  );
}

// Annotation with arrow (positioned absolutely)
function Annot({ top, left, width, children, arrow }) {
  return (
    <div className="annot" style={{ top, left, width }}>
      {children}
      {arrow}
    </div>
  );
}

// Sticky note
function Sticky({ children, style }) {
  return <div className="sticky" style={style}>{children}</div>;
}

Object.assign(window, { HandArrow, Rough, Lines, TreeRow, Zone, AppChrome, Annot, Sticky });
