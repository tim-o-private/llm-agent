// SCENE B — File detail view (reading / citations)
function SceneFileDetail() {
  return (
    <div className="scene">
      <div className="scene-inner">
        <h1 className="scene-title">02 · File Detail</h1>
        <p className="scene-sub">A single file, opened. Markdown-first, but the right rail shows AI context: summary, linked files, recent runs, suggested actions.</p>

        <div className="app-frame" style={{ height: 700 }}>
          <AppChrome url="clarity.app/vault/finance/Q3-board-deck.md" />
          <div style={{ display: 'grid', gridTemplateColumns: '48px 1fr 340px', height: 'calc(100% - 28px)' }}>
            {/* collapsed sidebar */}
            <div style={{ borderRight: '1.5px dashed var(--stroke)', padding: '12px 0', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 14, background: 'var(--panel)' }}>
              {['⌂','▦','≡','⚙','✦','▸'].map((c,i) => (
                <div key={i} className="mono" style={{ fontSize: 14, color: i===2 ? 'var(--accent)' : 'var(--ink-faint)', cursor: 'pointer' }}>{c}</div>
              ))}
            </div>

            {/* file body */}
            <div style={{ overflow: 'auto', padding: '20px 48px', background: 'var(--panel)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
                <div className="mono" style={{ fontSize: 11, color: 'var(--ink-faint)' }}>vault / finance / Q3-board-deck.md · <span style={{ color: 'var(--success)' }}>● saved</span></div>
                <div style={{ display: 'flex', gap: 6 }}>
                  <span className="chip">history</span>
                  <span className="chip">share</span>
                  <span className="chip accent">✦ ask</span>
                </div>
              </div>

              <h1 className="hand" style={{ fontSize: 32, margin: '0 0 6px', color: 'var(--ink)' }}>Q3 Board Deck</h1>
              <div className="mono" style={{ fontSize: 11, color: 'var(--ink-faint)', marginBottom: 24 }}>draft · edited 2h ago · 4 contributors (you + ✦)</div>

              <h2 className="hand" style={{ fontSize: 28, color: 'var(--ink)', margin: '8px 0' }}>Revenue</h2>
              <div style={{ color: 'var(--ink-dim)', fontFamily: 'Kalam, cursive', fontSize: 15, lineHeight: 1.55, maxWidth: 620 }}>
                Revenue was <b style={{ color: 'var(--ink)' }}>$4.2M</b>, up 14% QoQ
                <span className="citation">1</span>. The mid-market segment crossed 40% of ARR for
                the first time <span className="citation">2</span>. See <span className="underline-wavy">runway-model.csv</span> for the updated
                forecast.
                <div style={{ height: 12 }} />
                Churn held flat at 1.8% monthly <span className="citation">3</span>.
                The retention spike in August was driven by the two annual renewals we flagged in
                the last board pre-read.
              </div>

              <div style={{ marginTop: 20 }} className="img-placeholder" >
                <div style={{ padding: 60 }}>CHART · revenue by segment · Q1–Q3</div>
              </div>

              <h2 className="hand" style={{ fontSize: 28, color: 'var(--ink)', margin: '20px 0 8px' }}>Runway</h2>
              <div style={{ color: 'var(--ink-dim)', fontFamily: 'Kalam, cursive', fontSize: 15, lineHeight: 1.55, maxWidth: 620 }}>
                Runway is <b style={{ color: 'var(--ink)' }}>17 months</b> at current burn
                <span className="citation">4</span>. A pulled-forward hiring plan would shorten this
                to 14 <span className="citation">5</span>.
              </div>

              {/* inline AI suggestion */}
              <div style={{ marginTop: 16, border: '1.5px solid var(--accent-dim)', background: 'var(--accent-ghost)', borderRadius: 8, padding: '10px 14px', position: 'relative', maxWidth: 620 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                  <span className="mono" style={{ fontSize: 10, color: 'var(--accent)', letterSpacing: '0.1em' }}>✦ CLARITY SUGGESTS</span>
                  <span className="mono" style={{ fontSize: 10, color: 'var(--ink-faint)' }}>dismiss · accept</span>
                </div>
                <div style={{ fontSize: 14, fontFamily: 'Kalam, cursive', color: 'var(--ink)' }}>
                  runway-model.csv was updated 4 minutes ago — these numbers are now stale. Re-pull?
                </div>
              </div>
            </div>

            {/* right rail: AI context */}
            <div style={{ borderLeft: '1.5px dashed var(--stroke)', overflow: 'auto', background: 'var(--panel-2)', padding: 16, display: 'flex', flexDirection: 'column', gap: 18 }}>

              <div>
                <div className="section-tag">summary · auto ✦</div>
                <div style={{ fontSize: 13, color: 'var(--ink-dim)', fontFamily: 'Kalam, cursive', lineHeight: 1.4 }}>
                  Draft of the Q3 board deck. Strong revenue, flat churn, runway concern if hiring accelerates.
                </div>
                <div className="mono" style={{ fontSize: 10, color: 'var(--ink-faint)', marginTop: 6 }}>regenerate · edit</div>
              </div>

              <div>
                <div className="section-tag">citations · 5</div>
                {[
                  { n: 1, src: 'runway-model.csv', q: 'row 42 · revenue' },
                  { n: 2, src: 'arr-segments.xlsx', q: 'sheet: mid-market' },
                  { n: 3, src: 'churn-report.md', q: '§ Aug' },
                  { n: 4, src: 'runway-model.csv', q: 'row 88' },
                  { n: 5, src: 'hiring-plan.md', q: 'scenario B' },
                ].map(c => (
                  <div key={c.n} style={{ padding: '6px 8px', borderLeft: '2px solid var(--accent-dim)', marginBottom: 6 }}>
                    <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
                      <span className="citation" style={{ marginLeft: 0 }}>{c.n}</span>
                      <span className="mono" style={{ fontSize: 11, color: 'var(--ink)' }}>{c.src}</span>
                    </div>
                    <div className="mono" style={{ fontSize: 10, color: 'var(--ink-faint)', marginLeft: 18 }}>{c.q}</div>
                  </div>
                ))}
              </div>

              <div>
                <div className="section-tag">linked by</div>
                <div style={{ fontSize: 12, color: 'var(--ink-dim)' }}>
                  <div style={{ padding: '3px 0' }}>✦ daily-digest.flow.md</div>
                  <div style={{ padding: '3px 0' }}>↗ investor-memo.pdf</div>
                  <div style={{ padding: '3px 0' }}>↗ hiring-plan.md</div>
                </div>
              </div>

              <div>
                <div className="section-tag">recent activity</div>
                <div style={{ fontSize: 12, color: 'var(--ink-dim)' }}>
                  <div style={{ padding: '3px 0' }}><span style={{ color: 'var(--accent)' }}>✦</span> daily-digest ran · 7:00</div>
                  <div style={{ padding: '3px 0' }}><span style={{ color: 'var(--ink)' }}>you</span> edited §Runway · 2h</div>
                  <div style={{ padding: '3px 0' }}><span style={{ color: 'var(--accent)' }}>✦</span> pulled forecast · 2h</div>
                  <div style={{ padding: '3px 0' }}><span style={{ color: 'var(--ink)' }}>you</span> opened · 3h</div>
                </div>
              </div>

              <div>
                <div className="section-tag">actions</div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                  <button className="sk-btn" style={{ textAlign: 'left' }}>↗ export as pdf</button>
                  <button className="sk-btn" style={{ textAlign: 'left' }}>⟲ re-run summary</button>
                  <button className="sk-btn accent" style={{ textAlign: 'left' }}>✦ ask about this file</button>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="row" style={{ marginTop: 20, gap: 20 }}>
          <Sticky style={{ flex: 1 }}>the document is the thing.<br/><span style={{ fontSize: 14, color: 'var(--ink-dim)' }}>AI lives in the rail — it never takes over the page.</span></Sticky>
          <Sticky style={{ flex: 1 }}>citations are hoverable & jump-able<br/><span style={{ fontSize: 14, color: 'var(--ink-dim)' }}>hover → quote preview; click → open source file at the cited line.</span></Sticky>
          <Sticky style={{ flex: 1 }}>inline nudges, not popups<br/><span style={{ fontSize: 14, color: 'var(--ink-dim)' }}>"your data is stale" appears where the data lives.</span></Sticky>
        </div>
      </div>
    </div>
  );
}

window.SceneFileDetail = SceneFileDetail;
