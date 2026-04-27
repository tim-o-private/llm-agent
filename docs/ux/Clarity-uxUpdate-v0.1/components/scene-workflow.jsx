// SCENE C — Workflow builder (markdown-first)
function SceneWorkflow() {
  const md = `---
name: daily-digest
triggers:
  - schedule: "0 7 * * *"      # every day at 07:00
  - event: file.added
    path: inbox/**
context:
  - vault/finance/**
  - vault/clients/acme/**
tools: [read, search, write, email]
---

# Daily digest

Every morning, skim what's new and what moved.

## Steps

1. Read every file added or edited in the last 24h.
2. Group changes by project.
3. For \`vault/finance/\` — pull the latest runway number.
4. Write a digest to \`inbox/digest-{{date}}.md\`.
5. If anything is blocking → email me at 7:05.

## Output template
> **{{project}}** — {{one-line change summary}}
> sources: {{citations}}`;

  const runs = [
    { d: 'Today · 07:00', s: 'ok', t: '1m 12s', out: 'inbox/digest-2026-04-17.md', sources: 14 },
    { d: 'Yesterday · 07:00', s: 'ok', t: '58s', out: 'inbox/digest-2026-04-16.md', sources: 11 },
    { d: 'Apr 15 · 07:00', s: 'warn', t: '2m 40s', out: 'inbox/digest-2026-04-15.md', sources: 22, note: 'slow: runway-model.csv re-parse' },
    { d: 'Apr 14 · 07:00', s: 'ok', t: '49s', out: 'inbox/digest-2026-04-14.md', sources: 9 },
  ];

  return (
    <div className="scene">
      <div className="scene-inner">
        <h1 className="scene-title">03 · Workflow</h1>
        <p className="scene-sub">Workflows are markdown files. YAML front-matter for triggers & context; prose below for intent. Edit it like a doc. Chat agent can author or modify them on your behalf.</p>

        <div className="app-frame" style={{ height: 720 }}>
          <AppChrome url="clarity.app/vault/_workflows/daily-digest.flow.md" />
          <div style={{ display: 'grid', gridTemplateColumns: '220px 1fr 360px', height: 'calc(100% - 28px)' }}>
            {/* left: workflow list */}
            <div style={{ borderRight: '1.5px dashed var(--stroke)', padding: '12px 8px', background: 'var(--panel)', overflow: 'auto' }}>
              <div className="section-tag" style={{ marginLeft: 6 }}>_workflows/</div>
              <TreeRow name="daily-digest.flow.md" type="flow" active />
              <TreeRow name="on-file-add.flow.md" type="flow" />
              <TreeRow name="weekly-investor.flow.md" type="flow" />
              <TreeRow name="extract-contacts.flow.md" type="flow" />
              <TreeRow name="translate-inbound.flow.md" type="flow" />
              <div style={{ marginTop: 14, padding: '0 6px' }}>
                <button className="sk-btn accent" style={{ width: '100%' }}>＋ new workflow</button>
              </div>

              <div style={{ marginTop: 24 }}>
                <div className="section-tag" style={{ marginLeft: 6 }}>triggers</div>
                <div style={{ fontSize: 12, color: 'var(--ink-dim)', padding: '0 6px' }}>
                  <div style={{ padding: '4px 0' }}><span className="dot on" /> schedule · 07:00</div>
                  <div style={{ padding: '4px 0' }}><span className="dot on" /> file.added → inbox/</div>
                  <div style={{ padding: '4px 0' }}><span className="dot" /> webhook · off</div>
                </div>
              </div>

              <div style={{ marginTop: 14 }}>
                <div className="section-tag" style={{ marginLeft: 6 }}>next run</div>
                <div style={{ fontSize: 12, color: 'var(--ink)', padding: '0 6px', fontFamily: 'JetBrains Mono, monospace' }}>in 14h 24m</div>
              </div>
            </div>

            {/* middle: markdown editor */}
            <div style={{ display: 'grid', gridTemplateRows: '36px 1fr auto', overflow: 'hidden' }}>
              <div style={{ borderBottom: '1.5px dashed var(--stroke)', display: 'flex', alignItems: 'center', gap: 14, padding: '0 14px', fontFamily: 'JetBrains Mono, monospace', fontSize: 11, color: 'var(--ink-dim)' }}>
                <span style={{ color: 'var(--ink)' }}>daily-digest.flow.md</span>
                <span style={{ color: 'var(--ink-faint)' }}>· markdown</span>
                <span style={{ marginLeft: 'auto', color: 'var(--ink-faint)' }}>edit · preview · diagram</span>
              </div>
              <div style={{ padding: '20px 24px', overflow: 'auto', fontFamily: 'JetBrains Mono, monospace', fontSize: 12.5, lineHeight: 1.6, color: 'var(--ink-dim)', whiteSpace: 'pre-wrap', background: 'var(--panel-2)' }}>
                {md.split('\n').map((line, i) => {
                  const isYaml = i >= 0 && i <= 10;
                  const isHeading = line.startsWith('#');
                  const isQuote = line.startsWith('>');
                  const isList = /^\s*\d+\./.test(line) || line.startsWith('- ');
                  const color = isHeading ? 'var(--ink)' : isYaml ? 'var(--accent)' : isQuote ? 'var(--ink-dim)' : isList ? 'var(--ink)' : 'var(--ink-dim)';
                  const weight = isHeading ? 600 : 400;
                  return (
                    <div key={i} style={{ color, fontWeight: weight, minHeight: 20, display: 'flex' }}>
                      <span style={{ width: 28, textAlign: 'right', marginRight: 14, color: 'var(--ink-faint)', fontSize: 10, userSelect: 'none' }}>{i + 1}</span>
                      <span>{line || ' '}</span>
                    </div>
                  );
                })}
              </div>
              <div style={{ padding: 10, borderTop: '1.5px dashed var(--stroke)', display: 'flex', gap: 8, alignItems: 'center' }}>
                <button className="sk-btn">save</button>
                <button className="sk-btn">dry-run</button>
                <button className="sk-btn accent">▶ run now</button>
                <span style={{ marginLeft: 'auto' }} className="mono" style={{ marginLeft: 'auto', fontSize: 11, color: 'var(--ink-faint)' }}>
                  valid yaml · 5 steps · uses 4 tools
                </span>
              </div>
            </div>

            {/* right: run history */}
            <div style={{ borderLeft: '1.5px dashed var(--stroke)', background: 'var(--panel)', overflow: 'auto', padding: 14 }}>
              <div className="section-tag">runs</div>
              {runs.map((r, i) => (
                <div key={i} className="sk-border" style={{
                  padding: 10, marginBottom: 8,
                  borderStyle: r.s === 'warn' ? 'solid' : 'dashed',
                  borderColor: r.s === 'warn' ? '#8a7236' : undefined
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
                    <span className="mono" style={{ fontSize: 11, color: 'var(--ink)' }}>{r.d}</span>
                    <span style={{ fontSize: 10, color: r.s === 'ok' ? 'var(--success)' : '#c9a14a' }}>{r.s === 'ok' ? '● ok' : '● warn'}</span>
                  </div>
                  <div className="mono" style={{ fontSize: 10, color: 'var(--ink-faint)', marginTop: 4 }}>{r.t} · {r.sources} sources</div>
                  <div className="mono" style={{ fontSize: 10, color: 'var(--ink-dim)', marginTop: 4 }}>→ {r.out}</div>
                  {r.note && <div style={{ fontSize: 11, color: '#c9a14a', marginTop: 4, fontFamily: 'Kalam, cursive' }}>⚠ {r.note}</div>}
                </div>
              ))}

              <div style={{ marginTop: 14 }}>
                <div className="section-tag">last output · preview</div>
                <div className="note-card" style={{ fontSize: 12, fontFamily: 'Kalam, cursive', color: 'var(--ink-dim)', lineHeight: 1.4 }}>
                  <b style={{ color: 'var(--ink)' }}>finance</b> — runway model updated, now 17mo <span className="citation">1</span><br/>
                  <b style={{ color: 'var(--ink)' }}>acme</b> — contract redline received, 2 changes <span className="citation">2</span><br/>
                  <b style={{ color: 'var(--ink)' }}>inbox</b> — 3 new files parsed <span className="citation">3</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="row" style={{ marginTop: 20, gap: 20 }}>
          <Sticky style={{ flex: 1 }}>workflows ARE files.<br/><span style={{ fontSize: 14, color: 'var(--ink-dim)' }}>Version control, diff, share, fork — all for free.</span></Sticky>
          <Sticky style={{ flex: 1 }}>prose, not boxes.<br/><span style={{ fontSize: 14, color: 'var(--ink-dim)' }}>Nodes & arrows are optional (preview mode). Source is markdown.</span></Sticky>
          <Sticky style={{ flex: 1 }}>agent can edit this.<br/><span style={{ fontSize: 14, color: 'var(--ink-dim)' }}>"make it run at 6am" in chat → a commit to this file.</span></Sticky>
        </div>
      </div>
    </div>
  );
}

window.SceneWorkflow = SceneWorkflow;
