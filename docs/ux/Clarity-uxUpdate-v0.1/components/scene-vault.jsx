// SCENE A — Vault / File browser (3-pane: tree | grid+preview | chat)
function SceneVault() {
  const [chatOpen, setChatOpen] = useState(true);
  const [sel, setSel] = useState('Q3-board-deck.md');

  const tree = [
    { n: 'vault/', t: 'folder_open', l: 0 },
    { n: 'clients/', t: 'folder', l: 1 },
    { n: 'finance/', t: 'folder_open', l: 1 },
    { n: 'Q3-board-deck.md', t: 'md', l: 2, active: true },
    { n: 'runway-model.csv', t: 'csv', l: 2 },
    { n: 'burn-2025.xlsx', t: 'csv', l: 2 },
    { n: 'research/', t: 'folder', l: 1, badge: '24' },
    { n: 'inbox/', t: 'folder', l: 1, badge: '3 new' },
    { n: '_workflows/', t: 'folder_open', l: 1 },
    { n: 'daily-digest.flow.md', t: 'flow', l: 2 },
    { n: 'on-file-add.flow.md', t: 'flow', l: 2 },
  ];

  const files = [
    { n: 'Q3-board-deck.md', type: 'markdown', meta: '12 sections · edited 2h ago', ai: 'summarized', active: true },
    { n: 'runway-model.csv', type: 'spreadsheet', meta: '1,204 rows · imported Mon' },
    { n: 'burn-2025.xlsx', type: 'spreadsheet', meta: '4 sheets · linked to digest' },
    { n: 'investor-memo.pdf', type: 'pdf', meta: '8 pages · extracted' },
    { n: 'headcount-plan.md', type: 'markdown', meta: 'last-edit · you' },
    { n: 'cashflow-Q4.csv', type: 'spreadsheet', meta: 'updates nightly' },
  ];

  return (
    <div className="scene">
      <div className="scene-inner">
        <div className="row" style={{ alignItems: 'flex-end', justifyContent: 'space-between' }}>
          <div>
            <h1 className="scene-title">01 · The Vault</h1>
            <p className="scene-sub">File-first home. Tree on the left, preview in the middle, chat docked right. Everything is a file — including the workflows.</p>
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <button className="sk-btn" onClick={() => setChatOpen(!chatOpen)}>{chatOpen ? 'hide' : 'show'} chat ⌘K</button>
          </div>
        </div>

        <div className="app-frame" style={{ height: 640 }}>
          <AppChrome url="clarity.app/vault/finance" />
          <div style={{ display: 'grid', gridTemplateColumns: chatOpen ? '220px 1fr 360px' : '220px 1fr', height: 'calc(100% - 28px)' }}>
            {/* === LEFT: tree === */}
            <div style={{ borderRight: '1.5px dashed var(--stroke)', padding: '12px 8px', overflow: 'auto', background: 'var(--panel)' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0 6px 10px' }}>
                <span className="mono" style={{ fontSize: 11, color: 'var(--ink-faint)', letterSpacing: '0.1em', textTransform: 'uppercase' }}>vault</span>
                <span className="mono" style={{ fontSize: 11, color: 'var(--ink-faint)' }}>+ ⌘N</span>
              </div>
              <div className="sk-border" style={{ padding: 4, marginBottom: 10, fontFamily: 'JetBrains Mono, monospace', fontSize: 11, color: 'var(--ink-faint)' }}>
                <span style={{ padding: '0 6px' }}>⌕ search files & content</span>
              </div>
              {tree.map((r, i) => <TreeRow key={i} level={r.l} name={r.n} type={r.t} active={r.active} badge={r.badge} />)}

              <div style={{ marginTop: 18 }}>
                <div className="section-tag">pinned workflows</div>
                <TreeRow level={0} name="daily-digest · 7:00" type="flow" />
                <TreeRow level={0} name="on-add: summarize" type="flow" />
                <TreeRow level={0} name="weekly investor note" type="flow" />
              </div>
            </div>

            {/* === MIDDLE: file grid + preview === */}
            <div style={{ display: 'grid', gridTemplateRows: '36px 1fr 1fr', overflow: 'hidden' }}>
              {/* breadcrumb bar */}
              <div style={{ borderBottom: '1.5px dashed var(--stroke)', display: 'flex', alignItems: 'center', gap: 14, padding: '0 14px', fontFamily: 'JetBrains Mono, monospace', fontSize: 11, color: 'var(--ink-dim)' }}>
                <span>vault / finance /</span>
                <span style={{ color: 'var(--ink)' }}>Q3-board-deck.md</span>
                <span style={{ marginLeft: 'auto', color: 'var(--ink-faint)' }}>view: ▦ grid · ≡ list · ⌥ columns</span>
              </div>

              {/* file grid */}
              <div style={{ padding: 14, overflow: 'auto' }}>
                <div className="section-tag">finance · 6 files</div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 10 }}>
                  {files.map((f, i) => (
                    <div key={i} className="sk-border" style={{
                      padding: 10, position: 'relative',
                      background: f.active ? 'var(--accent-ghost)' : 'transparent',
                      borderColor: f.active ? 'var(--accent-dim)' : undefined,
                      borderStyle: f.active ? 'solid' : 'dashed',
                      cursor: 'pointer'
                    }} onClick={() => setSel(f.n)}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
                        <span className="chip">{f.type}</span>
                        {f.ai && <span className="chip accent">✦ {f.ai}</span>}
                      </div>
                      <div className="mono" style={{ fontSize: 12, color: 'var(--ink)', marginBottom: 6 }}>{f.n}</div>
                      <div className="mono" style={{ fontSize: 10, color: 'var(--ink-faint)' }}>{f.meta}</div>
                    </div>
                  ))}
                </div>
              </div>

              {/* preview pane */}
              <div style={{ borderTop: '1.5px dashed var(--stroke)', padding: 14, overflow: 'auto', background: 'var(--panel-2)', position: 'relative' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 10 }}>
                  <div className="mono" style={{ fontSize: 11, color: 'var(--ink-faint)', letterSpacing: '0.1em', textTransform: 'uppercase' }}>preview · Q3-board-deck.md</div>
                  <div style={{ display: 'flex', gap: 6 }}>
                    <span className="chip">edit</span>
                    <span className="chip">open ↗</span>
                    <span className="chip accent">✦ ask about this</span>
                  </div>
                </div>
                <div className="hand" style={{ fontSize: 22, color: 'var(--ink)' }}># Q3 Board Deck — narrative draft</div>
                <Lines count={3} widths={['long','long','med']} />
                <div className="hand" style={{ fontSize: 18, color: 'var(--ink)', marginTop: 8 }}>## Revenue</div>
                <Lines count={2} widths={['long','short']} />
                <div className="note-card" style={{ marginTop: 8 }}>
                  <div style={{ fontSize: 11, color: 'var(--accent)', marginBottom: 4 }}>✦ auto-summary · 4 sources</div>
                  <div style={{ fontSize: 12, color: 'var(--ink-dim)', fontFamily: 'Kalam, cursive' }}>
                    Revenue up 14% QoQ, driven by mid-market expansion
                    <span className="citation">1</span>
                    <span className="citation">2</span>
                    . Churn held flat <span className="citation">3</span>.
                  </div>
                </div>
              </div>
            </div>

            {/* === RIGHT: chat modal === */}
            {chatOpen && (
              <div style={{ borderLeft: '1.5px dashed var(--stroke)', display: 'grid', gridTemplateRows: 'auto 1fr auto', background: 'var(--panel)' }}>
                <div style={{ padding: '10px 14px', borderBottom: '1.5px dashed var(--stroke)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div className="hand" style={{ fontSize: 22, color: 'var(--accent)' }}>Clarity</div>
                  <span className="mono" style={{ fontSize: 10, color: 'var(--ink-faint)' }}>scope: finance/ · gpt-4o</span>
                </div>
                <div style={{ padding: 14, overflow: 'auto', display: 'flex', flexDirection: 'column', gap: 12 }}>
                  <div style={{ alignSelf: 'flex-end', maxWidth: '85%', padding: '8px 12px', border: '1.5px solid var(--stroke)', borderRadius: 10, borderBottomRightRadius: 2, fontSize: 13 }}>
                    What changed in the board deck since Monday?
                  </div>
                  <div style={{ maxWidth: '90%', padding: '10px 12px', background: 'var(--accent-ghost)', border: '1.5px solid var(--accent-dim)', borderRadius: 10, borderBottomLeftRadius: 2, fontSize: 13, color: 'var(--ink)' }}>
                    Three sections were edited:
                    <ul style={{ margin: '6px 0 6px 16px', padding: 0, color: 'var(--ink-dim)' }}>
                      <li>Revenue — new mid-market breakout <span className="citation">1</span></li>
                      <li>Hiring — added 2 roles <span className="citation">2</span></li>
                      <li>Runway — updated from model <span className="citation">3</span></li>
                    </ul>
                    <div style={{ fontSize: 11, color: 'var(--ink-faint)', marginTop: 4 }}>▸ show reasoning</div>
                  </div>
                  <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                    <span className="chip">draft email to board</span>
                    <span className="chip">diff since Monday</span>
                    <span className="chip">re-run digest</span>
                  </div>
                </div>
                <div style={{ padding: 10, borderTop: '1.5px dashed var(--stroke)' }}>
                  <div className="sk-border" style={{ padding: '6px 10px', display: 'flex', alignItems: 'center', gap: 8, fontFamily: 'JetBrains Mono, monospace', fontSize: 12, color: 'var(--ink-faint)' }}>
                    <span>@</span>
                    <span style={{ flex: 1 }}>ask or /run a workflow…</span>
                    <span className="chip accent">↵</span>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Floating annotations */}
          <div className="annot" style={{ top: 62, left: -170, width: 160, textAlign: 'right' }}>
            everything is a file —<br/>incl. _workflows/
          </div>
          <div className="annot" style={{ bottom: 160, right: -180, width: 170 }}>
            chat is scoped to<br/>the current folder
          </div>
        </div>

        <div className="row" style={{ marginTop: 20, gap: 20 }}>
          <Sticky style={{ flex: 1 }}>
            tree → preview → chat<br/>
            <span style={{ fontSize: 14, color: 'var(--ink-dim)' }}>Familiar finder pattern. Chat feels like a sidekick, not a takeover.</span>
          </Sticky>
          <Sticky style={{ flex: 1 }}>
            ✦ citations are first-class<br/>
            <span style={{ fontSize: 14, color: 'var(--ink-dim)' }}>Every AI claim links back to a file. Click to jump.</span>
          </Sticky>
          <Sticky style={{ flex: 1 }}>
            ⌘K opens chat anywhere<br/>
            <span style={{ fontSize: 14, color: 'var(--ink-dim)' }}>Toggle from header, keyboard, or deep-link.</span>
          </Sticky>
        </div>
      </div>
    </div>
  );
}

window.SceneVault = SceneVault;
