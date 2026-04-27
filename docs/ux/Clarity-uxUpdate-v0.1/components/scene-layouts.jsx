// SCENE E — Alternate overall layouts (5 structural options)
function SceneLayouts() {
  const Mini = ({ children, title, sub }) => (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 6 }}>
        <div className="hand" style={{ fontSize: 20, color: 'var(--ink)' }}>{title}</div>
      </div>
      <div className="app-frame" style={{ height: 240 }}>
        <AppChrome url="clarity.app" />
        <div style={{ height: 'calc(100% - 28px)' }}>{children}</div>
      </div>
      <div style={{ marginTop: 6, fontSize: 13, color: 'var(--ink-dim)', fontFamily: 'Kalam, cursive', maxWidth: 360 }}>{sub}</div>
    </div>
  );

  return (
    <div className="scene">
      <div className="scene-inner">
        <h1 className="scene-title">05 · Overall layouts</h1>
        <p className="scene-sub">Five structural directions for the whole app. All share: file-based vault, chat agent, workflows as markdown. They differ in where you spend your time.</p>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 20, marginTop: 10 }}>

          <Mini title="L1 · Finder + rail" sub="Current direction. Tree + preview + docked chat. Most familiar.">
            <div style={{ display: 'grid', gridTemplateColumns: '25% 1fr 30%', height: '100%' }}>
              <div style={{ borderRight: '1.5px dashed var(--stroke)', padding: 8 }}>
                {['vault/','  finance/','  clients/','  _workflows/','  inbox/'].map((x,i) =>
                  <div key={i} className="mono" style={{ fontSize: 9, color: i===0?'var(--ink)':'var(--ink-dim)', padding: '2px 0' }}>{x}</div>
                )}
              </div>
              <div style={{ padding: 8, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 4, alignContent: 'start' }}>
                {[0,1,2,3].map(i => <div key={i} className="sk-border" style={{ height: 40 }} />)}
              </div>
              <div style={{ borderLeft: '1.5px dashed var(--stroke)', background: 'var(--panel-2)', padding: 8 }}>
                <div className="hand" style={{ fontSize: 14, color: 'var(--accent)' }}>Clarity</div>
                <div style={{ height: 20, background: 'var(--accent-ghost)', borderRadius: 4, marginTop: 6 }} />
                <div style={{ height: 14, background: 'var(--panel)', borderRadius: 4, marginTop: 4 }} />
              </div>
            </div>
          </Mini>

          <Mini title="L2 · Chat-primary" sub="Chat is the spine; files open to the side as refs. For users who direct-by-conversation.">
            <div style={{ display: 'grid', gridTemplateColumns: '55% 45%', height: '100%' }}>
              <div style={{ padding: 10, background: 'var(--panel-2)', borderRight: '1.5px dashed var(--stroke)' }}>
                <div className="hand" style={{ fontSize: 14, color: 'var(--accent)' }}>Clarity</div>
                <div style={{ height: 26, background: 'var(--accent-ghost)', borderRadius: 4, marginTop: 6 }} />
                <div style={{ height: 40, background: 'var(--panel)', borderRadius: 4, marginTop: 4 }} />
                <div style={{ height: 16, background: 'var(--accent-ghost)', borderRadius: 4, marginTop: 4, width: '60%', marginLeft: 'auto' }} />
              </div>
              <div style={{ padding: 8 }}>
                <div className="mono" style={{ fontSize: 8, color: 'var(--ink-faint)' }}>REF · Q3-board-deck.md</div>
                <div className="sk-border" style={{ height: 60, marginTop: 4 }} />
                <div className="mono" style={{ fontSize: 8, color: 'var(--ink-faint)', marginTop: 8 }}>REF · runway-model.csv</div>
                <div className="sk-border" style={{ height: 60, marginTop: 4 }} />
              </div>
            </div>
          </Mini>

          <Mini title="L3 · Columns (Finder)" sub="Drill-down columns. Good for deep hierarchies. Chat floats via ⌘K only.">
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', height: '100%' }}>
              {[0,1,2,3].map(col => (
                <div key={col} style={{ borderRight: col < 3 ? '1.5px dashed var(--stroke)' : 'none', padding: 6 }}>
                  {[0,1,2,3,4].map(r => (
                    <div key={r} className="mono" style={{ fontSize: 8, color: 'var(--ink-dim)', padding: '2px 0', background: col===2 && r===1 ? 'var(--accent-ghost)' : 'transparent' }}>
                      {['folder','file.md','file.csv','file.pdf','folder'][r]}
                    </div>
                  ))}
                </div>
              ))}
            </div>
          </Mini>

          <Mini title="L4 · Dashboard home" sub="Open to a status page. Files, workflows, recent runs, and a chat box all on one screen.">
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gridTemplateRows: '1fr 1fr', gap: 4, padding: 6, height: '100%' }}>
              <div className="sk-border" style={{ padding: 4 }}>
                <div className="mono" style={{ fontSize: 8, color: 'var(--ink-faint)' }}>RECENT FILES</div>
                <div style={{ height: 12, background: 'var(--panel-2)', marginTop: 4 }} />
                <div style={{ height: 12, background: 'var(--panel-2)', marginTop: 2 }} />
              </div>
              <div className="sk-border" style={{ padding: 4, borderColor: 'var(--accent-dim)', borderStyle: 'solid' }}>
                <div className="mono" style={{ fontSize: 8, color: 'var(--accent)' }}>✦ CHAT</div>
                <div style={{ height: 28, background: 'var(--accent-ghost)', marginTop: 4, borderRadius: 3 }} />
              </div>
              <div className="sk-border" style={{ padding: 4 }}>
                <div className="mono" style={{ fontSize: 8, color: 'var(--ink-faint)' }}>RUNS · TODAY</div>
                <div style={{ height: 8, background: 'var(--success)', opacity: 0.6, marginTop: 4, width: '40%' }} />
              </div>
              <div className="sk-border" style={{ padding: 4 }}>
                <div className="mono" style={{ fontSize: 8, color: 'var(--ink-faint)' }}>WORKFLOWS</div>
                <div style={{ height: 10, background: 'var(--panel-2)', marginTop: 4 }} />
                <div style={{ height: 10, background: 'var(--panel-2)', marginTop: 2 }} />
              </div>
            </div>
          </Mini>

          <Mini title="L5 · Terminal hybrid" sub="Dense. Split-screen: file view top, command+chat pane bottom. Power users.">
            <div style={{ display: 'grid', gridTemplateRows: '55% 45%', height: '100%' }}>
              <div style={{ padding: 6, display: 'grid', gridTemplateColumns: '25% 1fr', gap: 4 }}>
                <div style={{ borderRight: '1.5px dashed var(--stroke)' }}>
                  {['~/vault','finance/','clients/','_workflows/'].map((x,i)=>
                    <div key={i} className="mono" style={{ fontSize: 8, padding: '2px 0', color: 'var(--ink-dim)' }}>{x}</div>
                  )}
                </div>
                <div className="sk-border" style={{ padding: 4 }}><Lines count={2} widths={['long','med']} /></div>
              </div>
              <div style={{ borderTop: '1.5px dashed var(--stroke)', padding: 6, background: 'var(--panel-2)', fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: 'var(--ink-dim)' }}>
                <div><span style={{ color: 'var(--accent)' }}>✦</span> &gt; summarize inbox</div>
                <div style={{ color: 'var(--ink)', paddingLeft: 12 }}>3 new files · wrote digest-2026-04-17.md</div>
                <div style={{ marginTop: 6 }}><span style={{ color: 'var(--accent)' }}>✦</span> &gt; <span style={{ borderRight: '1px solid var(--accent)', paddingRight: 2 }}>_</span></div>
              </div>
            </div>
          </Mini>

          <div>
            <div style={{ marginBottom: 6 }} className="hand" style={{ fontSize: 20, color: 'var(--ink)' }}>recommendation</div>
            <div className="sticky" style={{ fontSize: 16, lineHeight: 1.3 }}>
              <b>L1 finder + rail</b> as default — most users find it first.
              <div style={{ fontSize: 13, color: 'var(--ink-dim)', marginTop: 6 }}>
                Ship <b>L2</b> as a "focus mode" toggle for chat-first sessions. <b>⌘K palette</b> from L5 is always available.
              </div>
            </div>
          </div>

        </div>

        <div className="row" style={{ marginTop: 24, gap: 20 }}>
          <Sticky style={{ flex: 1 }}>pick by user, not by screen<br/><span style={{ fontSize: 14, color: 'var(--ink-dim)' }}>Devs → L5. PMs → L1. Founders → L4. Let them choose.</span></Sticky>
          <Sticky style={{ flex: 1 }}>layout = muscle memory<br/><span style={{ fontSize: 14, color: 'var(--ink-dim)' }}>Commit to one. Don't make users re-learn on every visit.</span></Sticky>
          <Sticky style={{ flex: 1 }}>chat must be reachable in {`<`}1s<br/><span style={{ fontSize: 14, color: 'var(--ink-dim)' }}>Whichever layout wins — ⌘K must always summon it.</span></Sticky>
        </div>
      </div>
    </div>
  );
}

window.SceneLayouts = SceneLayouts;
