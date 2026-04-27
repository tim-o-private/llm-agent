// SCENE D — Chat modal variations (4 side-by-side placements)
function SceneChatVariants() {
  const variants = [
    {
      title: 'A · Right rail (default)',
      note: 'Docked, scoped to current folder. Keeps file view intact.',
      render: () => (
        <div style={{ position: 'relative', height: '100%' }}>
          <div style={{ position: 'absolute', inset: 0, padding: 10, opacity: 0.5 }}>
            <Lines count={5} />
            <div className="img-placeholder" style={{ height: 80, marginTop: 8 }}>file grid</div>
          </div>
          <div style={{ position: 'absolute', top: 0, right: 0, bottom: 0, width: '45%', background: 'var(--panel-2)', borderLeft: '1.5px dashed var(--stroke)', padding: 10 }}>
            <div className="hand" style={{ fontSize: 18, color: 'var(--accent)' }}>Clarity</div>
            <div className="mono" style={{ fontSize: 9, color: 'var(--ink-faint)', marginBottom: 8 }}>scope: finance/</div>
            <div style={{ background: 'var(--accent-ghost)', padding: 6, borderRadius: 4, fontSize: 10, color: 'var(--ink-dim)', marginBottom: 6 }}>what changed today?</div>
            <div style={{ background: 'var(--panel)', padding: 6, borderRadius: 4, fontSize: 10, color: 'var(--ink-dim)' }}>3 files edited<span className="citation">1</span></div>
          </div>
        </div>
      )
    },
    {
      title: 'B · Floating palette (⌘K)',
      note: 'Transient, keyboard-first. Dismisses on escape. Feels like Spotlight.',
      render: () => (
        <div style={{ position: 'relative', height: '100%' }}>
          <div style={{ position: 'absolute', inset: 0, padding: 10, opacity: 0.5 }}>
            <Lines count={4} />
            <div className="img-placeholder" style={{ height: 80, marginTop: 8 }}>file grid</div>
          </div>
          <div style={{ position: 'absolute', inset: 0, background: 'rgba(0,0,0,0.45)' }} />
          <div style={{ position: 'absolute', top: '18%', left: '10%', right: '10%', background: 'var(--panel)', border: '1.5px solid var(--accent-dim)', borderRadius: 10, padding: 10, boxShadow: '0 8px 30px rgba(0,0,0,0.5)' }}>
            <div className="mono" style={{ fontSize: 10, color: 'var(--ink-faint)', marginBottom: 6 }}>✦ clarity · ⌘K</div>
            <div className="mono" style={{ fontSize: 12, color: 'var(--ink)', borderBottom: '1px dashed var(--stroke)', paddingBottom: 6 }}>ask or /run…</div>
            <div style={{ marginTop: 6, fontSize: 10, color: 'var(--ink-dim)' }}>
              <div>↗ open finance/Q3-deck.md</div>
              <div>▶ run daily-digest</div>
              <div style={{ color: 'var(--accent)' }}>✦ summarize everything new today</div>
            </div>
          </div>
        </div>
      )
    },
    {
      title: 'C · Bottom drawer',
      note: 'Persistent chat under everything. Good for long conversations while browsing.',
      render: () => (
        <div style={{ position: 'relative', height: '100%' }}>
          <div style={{ position: 'absolute', inset: '0 0 40% 0', padding: 10 }}>
            <Lines count={3} />
            <div className="img-placeholder" style={{ height: 50, marginTop: 6 }}>file grid</div>
          </div>
          <div style={{ position: 'absolute', left: 0, right: 0, bottom: 0, height: '40%', background: 'var(--panel-2)', borderTop: '1.5px dashed var(--stroke)', padding: 10 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span className="hand" style={{ fontSize: 16, color: 'var(--accent)' }}>Clarity</span>
              <span className="mono" style={{ fontSize: 9, color: 'var(--ink-faint)' }}>▾ collapse</span>
            </div>
            <div style={{ display: 'flex', gap: 6, marginTop: 6 }}>
              <div style={{ background: 'var(--panel)', padding: 6, fontSize: 10, borderRadius: 4, color: 'var(--ink-dim)', flex: 1 }}>3 files edited<span className="citation">1</span></div>
            </div>
            <div className="sk-border" style={{ marginTop: 8, padding: 4, fontSize: 10, color: 'var(--ink-faint)', fontFamily: 'JetBrains Mono, monospace' }}>ask or /run…</div>
          </div>
        </div>
      )
    },
    {
      title: 'D · Inline bubble (contextual)',
      note: 'Chat attaches to a selection/file. For quick, targeted questions.',
      render: () => (
        <div style={{ position: 'relative', height: '100%', padding: 10 }}>
          <div style={{ color: 'var(--ink-dim)', fontSize: 10, fontFamily: 'Kalam, cursive' }}>
            Revenue was <b style={{ color: 'var(--ink)' }}>$4.2M</b>, up <span style={{ background: 'var(--accent-ghost)', borderBottom: '1px solid var(--accent)' }}>14% QoQ</span>. Churn held flat.
          </div>
          <div style={{ position: 'absolute', top: 40, left: 70, background: 'var(--panel)', border: '1.5px solid var(--accent-dim)', borderRadius: 8, padding: 8, width: '70%', boxShadow: '0 4px 12px rgba(0,0,0,0.4)' }}>
            <div className="mono" style={{ fontSize: 9, color: 'var(--accent)' }}>✦ ask about "14% QoQ"</div>
            <div style={{ marginTop: 4, fontSize: 10, color: 'var(--ink-dim)' }}>
              <div>→ where does this come from?</div>
              <div>→ is this up or down vs plan?</div>
              <div>→ draft a bullet for the deck</div>
            </div>
          </div>
        </div>
      )
    },
  ];

  return (
    <div className="scene">
      <div className="scene-inner">
        <h1 className="scene-title">04 · Chat, 4 ways</h1>
        <p className="scene-sub">The same agent, four placements. Default is right rail (A). The others coexist — each suits a different moment. B works anywhere via ⌘K.</p>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, marginTop: 10 }}>
          {variants.map((v, i) => (
            <div key={i}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 6 }}>
                <div className="hand" style={{ fontSize: 22, color: 'var(--ink)' }}>{v.title}</div>
                <div className="mono" style={{ fontSize: 10, color: 'var(--ink-faint)' }}>pattern {String.fromCharCode(65 + i)}</div>
              </div>
              <div className="app-frame" style={{ height: 260 }}>
                <AppChrome url="clarity.app/vault" />
                <div style={{ height: 'calc(100% - 28px)', position: 'relative' }}>{v.render()}</div>
              </div>
              <div style={{ marginTop: 6, fontSize: 13, color: 'var(--ink-dim)', fontFamily: 'Kalam, cursive' }}>{v.note}</div>
            </div>
          ))}
        </div>

        <div className="row" style={{ marginTop: 24, gap: 20 }}>
          <Sticky style={{ flex: 1 }}>right rail = default<br/><span style={{ fontSize: 14, color: 'var(--ink-dim)' }}>Familiar. Scoped. Coexists with file view.</span></Sticky>
          <Sticky style={{ flex: 1 }}>⌘K palette = universal<br/><span style={{ fontSize: 14, color: 'var(--ink-dim)' }}>Always one keystroke away, anywhere.</span></Sticky>
          <Sticky style={{ flex: 1 }}>bubbles = surgical<br/><span style={{ fontSize: 14, color: 'var(--ink-dim)' }}>"explain this cell" type moves, without leaving the doc.</span></Sticky>
        </div>
      </div>
    </div>
  );
}

window.SceneChatVariants = SceneChatVariants;
