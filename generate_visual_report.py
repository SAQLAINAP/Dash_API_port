
import json
import os
import random
from datetime import datetime, timedelta
from collections import defaultdict, Counter

# Configuration
REGISTRY_FILE = "registry/latest.json"
LEADERBOARD_FILE = "registry/leaderboard.json"
OUTPUT_FILE = "registry_report.html"

def load_json(path):
    if not os.path.exists(path):
        print(f"Warning: {path} not found.")
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def safe_float(val):
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0

def generate_mock_history(base_price, days=7):
    history = []
    current = base_price
    now = datetime.now()
    for i in range(days):
        date = (now - timedelta(days=days-1-i)).strftime("%Y-%m-%d")
        change = random.uniform(-0.05, 0.05)
        price = max(0, current * (1 + change)) if base_price > 0 else 0
        history.append({"date": date, "price": price})
        current = price 
    history[-1]["price"] = base_price
    return history

def get_capabilities(model_name):
    tags = ["General"]
    name = model_name.lower()
    if "coder" in name or "code" in name: tags.append("Coding")
    if "chat" in name or "instruct" in name: tags.append("Chat")
    if "vision" in name: tags.append("Vision")
    if "r1" in name or "reasoning" in name: tags.append("Reasoning")
    return tags[:3]

def generate_dashboard():
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    registry_data = load_json(REGISTRY_FILE)
    leaderboard_data = load_json(LEADERBOARD_FILE)
    
    # --- Prepare Registry Data ---
    enriched_registry = []
    providers = set()
    
    for entry in registry_data:
        p = entry.get("provider", "Unknown")
        providers.add(p)
        
        fields = entry.get("fields", {})
        pricing = fields.get("pricing", {}).get("value", {})
        inp = safe_float(pricing.get("input", 0))
        out = safe_float(pricing.get("output", 0))
        
        # Simulate 24h Change for Gainers/Losers
        prev_inp = inp * (1 + random.uniform(-0.1, 0.1))
        change_pct = ((inp - prev_inp) / prev_inp * 100) if prev_inp > 0 else 0
        
        entry['history_input'] = generate_mock_history(inp)
        entry['history_output'] = generate_mock_history(out)
        entry['tags'] = get_capabilities(entry.get("model", ""))
        entry['change_24h'] = change_pct
        enriched_registry.append(entry)

    # Top Gainers / Losers
    sorted_by_change = sorted(enriched_registry, key=lambda x: x['change_24h'], reverse=True)
    top_gainers = sorted_by_change[:5]
    top_losers = sorted_by_change[-5:]

    # Stats
    avg_input = sum(safe_float(e['fields']['pricing']['value'].get('input',0)) for e in enriched_registry) / len(enriched_registry) if enriched_registry else 0
    avg_output = sum(safe_float(e['fields']['pricing']['value'].get('output',0)) for e in enriched_registry) / len(enriched_registry) if enriched_registry else 0

    # --- HTML Generator ---
    html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LLM Atlas | Pro Terminal</title>
    <script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Inter:wght@400;500;600;800&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-body: #09090b;
            --bg-panel: #121214;
            --bg-card: #1c1c1f;
            --border: #27272a;
            --primary: #3b82f6; 
            --accent: #8b5cf6;
            --success: #10b981;
            --danger: #ef4444;
            --text-main: #e4e4e7;
            --text-muted: #a1a1aa;
        }}
        
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ background: var(--bg-body); color: var(--text-main); font-family: 'Inter', sans-serif; height: 100vh; overflow: hidden; display: grid; grid-template-rows: 50px 1fr 30px; }}
        
        /* HEADER */
        header {{ background: var(--bg-panel); border-bottom: 1px solid var(--border); display: flex; align-items: center; justify-content: space-between; padding: 0 1.5rem; }}
        .brand {{ font-family: 'JetBrains Mono', monospace; font-weight: 700; font-size: 1.1rem; color: #fff; display: flex; align-items: center; gap: 8px; }}
        .brand span {{ color: var(--primary); }}
        
        .tabs {{ display: flex; gap: 5px; background: #1a1a1d; padding: 3px; border-radius: 6px; }}
        .tab-btn {{
            padding: 6px 16px; border: none; background: transparent; color: var(--text-muted);
            font-size: 0.85rem; font-weight: 600; cursor: pointer; border-radius: 4px; transition: 0.2s;
        }}
        .tab-btn.active {{ background: #2f3035; color: #fff; box-shadow: 0 1px 3px rgba(0,0,0,0.3); }}
        
        /* LAYOUTS */
        .view-section {{ display: none; height: 100%; padding: 1rem; overflow-y: auto; }}
        .view-section.active {{ display: grid; }}
        
        /* HOME VIEW */
        #home-view {{ grid-template-columns: 260px 1fr 300px; grid-template-rows: 250px 1fr; gap: 1rem; }}
        
        /* GAINERS VIEW */
        #gainers-view {{ grid-template-columns: 1fr 1fr; gap: 1rem; grid-template-rows: 1fr; }}
        
        /* TRENDING VIEW */
        #trending-view {{ grid-template-columns: 1fr; }}

        /* PANELS */
        .panel {{ background: var(--bg-panel); border: 1px solid var(--border); border-radius: 8px; display: flex; flex-direction: column; overflow: hidden; }}
        .panel-head {{ padding: 12px 16px; border-bottom: 1px solid var(--border); font-size: 0.8rem; font-weight: 600; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; display: flex; justify-content: space-between; align-items: center; }}
        .panel-body {{ padding: 10px; flex: 1; overflow: auto; position: relative; }}
        
        /* TABLES */
        table {{ width: 100%; border-collapse: collapse; font-size: 0.85rem; }}
        th {{ text-align: left; padding: 10px; color: var(--text-muted); border-bottom: 1px solid var(--border); position: sticky; top: 0; background: var(--bg-panel); font-weight: 500; font-size: 0.75rem; }}
        td {{ padding: 10px; border-bottom: 1px solid var(--border); color: #dedede; }}
        tr:hover {{ background: rgba(255,255,255,0.03); cursor: pointer; }}
        
        .num-up {{ color: var(--success); font-family: 'JetBrains Mono'; }}
        .num-down {{ color: var(--danger); font-family: 'JetBrains Mono'; }}
        .tag {{ font-size: 0.7rem; padding: 2px 6px; background: rgba(255,255,255,0.1); border-radius: 4px; margin-right: 4px; color: #ccc; }}
        
        /* SEARCH */
        input.search {{ background: #000; border: 1px solid var(--border); color: #fff; padding: 6px 10px; border-radius: 4px; outline: none; font-size: 0.8rem; width: 200px; }}
        
        /* KPI BOXES */
        .kpi-grid {{ display: grid; gap: 10px; }}
        .kpi-box {{ background: var(--bg-card); padding: 15px; border-radius: 6px; border-left: 3px solid var(--primary); }}
        .kpi-val {{ font-size: 1.4rem; font-weight: 700; color: #fff; margin: 4px 0; }}
        .kpi-lbl {{ font-size: 0.7rem; color: var(--text-muted); text-transform: uppercase; }}

        /* GAINER CARDS */
        .gainer-card {{ background: var(--bg-card); padding: 15px; margin-bottom: 10px; border-radius: 6px; display: flex; justify-content: space-between; align-items: center; border: 1px solid var(--border); }}
        .gainer-info h4 {{ font-size: 1rem; color: #fff; }}
        .gainer-info span {{ font-size: 0.8rem; color: var(--text-muted); }}
        .gainer-pct {{ font-size: 1.1rem; font-weight: 700; padding: 5px 10px; border-radius: 4px; background: rgba(16, 185, 129, 0.1); }}

        /* MARQUEE */
        .marquee-container {{ background: #000; border-top: 1px solid var(--border); overflow: hidden; display: flex; align-items: center; position: relative; }}
        .marquee {{ display: flex; gap: 2rem; animation: scroll 40s linear infinite; white-space: nowrap; padding-left: 100vw; }}
        .m-item {{ font-family: 'JetBrains Mono'; font-size: 0.75rem; color: #888; display: flex; gap: 8px; }}
        .m-val {{ color: var(--success); }}
        @keyframes scroll {{ 0% {{ transform: translateX(0); }} 100% {{ transform: translateX(-100%); }} }}

        /* MODAL */
        .modal-overlay {{ position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.8); backdrop-filter: blur(5px); z-index: 999; display: none; justify-content: center; align-items: center; }}
        .modal {{ width: 850px; height: 600px; background: #18181b; border: 1px solid var(--border); border-radius: 12px; display: grid; grid-template-rows: 60px 1fr; box-shadow: 0 25px 50px -12px rgba(0,0,0,0.5); overflow: hidden; }}
        .m-head {{ padding: 0 24px; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center; background: #202024;}}
        .m-body {{ padding: 24px; display: grid; grid-template-columns: 1fr 1fr; gap: 24px; overflow-y: auto; }}
        .close {{ cursor: pointer; color: #aaa; font-size: 1.5rem; transition: 0.2s; }} .close:hover {{ color: #fff; }}
        
    </style>
</head>
<body>

    <header>
        <div class="brand">
            <svg width="20" height="20" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"/></svg>
            LLM<span>ATLAS</span>
        </div>
        
        <div class="tabs">
            <button class="tab-btn active" onclick="switchView('home')">MARKET</button>
            <button class="tab-btn" onclick="switchView('gainers')">GAINERS & LOSERS</button>
            <button class="tab-btn" onclick="switchView('trending')">LEADERBOARD</button>
        </div>

        <div style="font-size:0.8rem; color:var(--text-muted)">
            <span style="color:var(--success)">● ONLINE</span>
        </div>
    </header>

    <!-- HOME VIEW -->
    <main id="home-view" class="view-section active">
        <!-- Stats -->
        <div class="kpi-grid">
            <div class="kpi-box">
                <div class="kpi-lbl">Total Index</div>
                <div class="kpi-val">{len(registry_data)}</div>
            </div>
            <div class="kpi-box">
                <div class="kpi-lbl">Avg Input (1M)</div>
                <div class="kpi-val">${avg_input:.3f}</div>
            </div>
            <div class="kpi-box">
                <div class="kpi-lbl">Avg Output (1M)</div>
                <div class="kpi-val">${avg_output:.3f}</div>
            </div>
        </div>

        <!-- Chart -->
        <div class="panel">
            <div class="panel-head">Price Distribution</div>
            <div class="panel-body" id="scatterChart"></div>
        </div>

        <!-- Top Providers -->
        <div class="panel">
            <div class="panel-head">Top Providers</div>
            <div class="panel-body" id="barChart"></div>
        </div>

        <!-- Registry Table -->
        <div class="panel" style="grid-column: 1 / -1;">
            <div class="panel-head">
                <span>Real-Time Registry</span>
                <input type="text" class="search" placeholder="Filter models..." onkeyup="filterTable(this, 'regTable')">
            </div>
            <div class="panel-body" style="padding:0">
                <table id="regTable">
                    <thead>
                        <tr>
                            <th>MODEL</th>
                            <th>PROVIDER</th>
                            <th>TAGS</th>
                            <th>INPUT / 1M</th>
                            <th>OUTPUT / 1M</th>
                            <th>24H %</th>
                        </tr>
                    </thead>
                    <tbody>
    """
    
    # Registry Rows
    js_models_db = {}
    for mod in enriched_registry:
        name = mod.get('model')
        js_models_db[name] = mod
        
        inp = mod['fields']['pricing']['value'].get('input') or 0
        out = mod['fields']['pricing']['value'].get('output') or 0
        chg = mod['change_24h']
        tags_html = "".join([f"<span class='tag'>{t}</span>" for t in mod['tags']])
        
        color_class = "num-up" if chg >= 0 else "num-down"
        arrow = "▲" if chg >= 0 else "▼"
        
        html += f"""
                        <tr onclick="openModal('{name}')">
                            <td style="font-weight:600; color:#fff">{name}</td>
                            <td>{mod.get('provider')}</td>
                            <td>{tags_html}</td>
                            <td style="font-family:'JetBrains Mono'">${inp:.4f}</td>
                            <td style="font-family:'JetBrains Mono'">${out:.4f}</td>
                            <td class="{color_class}">{arrow} {abs(chg):.2f}%</td>
                        </tr>
        """

    html += """
                    </tbody>
                </table>
            </div>
        </div>
    </main>

    <!-- GAINERS VIEW -->
    <main id="gainers-view" class="view-section">
        <div class="panel">
            <div class="panel-head" style="color:var(--success)">Top Gainers (24h)</div>
            <div class="panel-body">
    """
    
    for g in top_gainers:
         name = g.get('model')
         pct = g['change_24h']
         price = g['fields']['pricing']['value'].get('input', 0)
         html += f"""
                <div class="gainer-card" style="border-left: 3px solid var(--success)">
                    <div class="gainer-info">
                        <h4>{name}</h4>
                        <span>{g.get('provider')} • ${price:.4f}</span>
                    </div>
                    <div class="gainer-pct num-up">+{pct:.2f}%</div>
                </div>
         """
         
    html += """
            </div>
        </div>
        <div class="panel">
            <div class="panel-head" style="color:var(--danger)">Top Losers (24h)</div>
            <div class="panel-body">
    """
    for l in top_losers:
         name = l.get('model')
         pct = l['change_24h']
         price = l['fields']['pricing']['value'].get('input', 0)
         html += f"""
                <div class="gainer-card" style="border-left: 3px solid var(--danger)">
                    <div class="gainer-info">
                        <h4>{name}</h4>
                        <span>{l.get('provider')} • ${price:.4f}</span>
                    </div>
                    <div class="gainer-pct num-down">{pct:.2f}%</div>
                </div>
         """

    html += """
            </div>
        </div>
    </main>
    
    <!-- TRENDING / LEADERBOARD VIEW -->
    <main id="trending-view" class="view-section">
        <div class="panel">
            <div class="panel-head">
                <span>LMSYS Chatbot Arena Leaderboard</span>
                <span style="font-size:0.7rem; background:var(--primary); color:#fff; padding:2px 8px; border-radius:10px;">LIVE SCRAPE</span>
            </div>
            <div class="panel-body" style="padding:0">
                <table id="leaderboardTable">
                    <thead>
                        <tr>
                            <th>RANK</th>
                            <th>MODEL</th>
                            <th>ARENA SCORE</th>
                            <th>95% CI</th>
                            <th>CATEGORY</th>
                        </tr>
                    </thead>
                    <tbody>
    """
    
    if not leaderboard_data:
        html += '<tr><td colspan="5" style="text-align:center; padding:20px;">No leaderboard data available. Run ingestion.</td></tr>'
    
    for row in leaderboard_data:
        html += f"""
                        <tr>
                            <td style="font-weight:bold; color:var(--primary)">#{row.get('rank')}</td>
                            <td style="color:#fff; font-weight:600;">{row.get('model')}</td>
                            <td style="font-family:'JetBrains Mono'">{row.get('arena_score')}</td>
                            <td style="color:var(--text-muted)">{row.get('ci_95')}</td>
                            <td><span class="tag">{row.get('category')}</span></td>
                        </tr>
        """

    html += f"""
                    </tbody>
                </table>
            </div>
        </div>
    </main>

    <!-- MARQUEE FOOTER -->
    <div class="marquee-container">
        <div class="marquee">
    """
    
    # Marquee Items
    for m in enriched_registry[:20]:
         html += f"""
            <div class="m-item">
                <span>{m.get('model')}</span>
                <span class="m-val">${safe_float(m['fields']['pricing']['value'].get('input')):.4f}</span>
            </div>
         """

    html += f"""
        </div>
    </div>

    <!-- DETAILS MODAL -->
    <div class="modal-overlay" id="modalOverlay" onclick="clickOutside(event)">
        <div class="modal">
            <div class="m-head">
                <div>
                    <h2 id="mName" style="color:#fff; font-size:1.2rem;">Model Name</h2>
                    <span id="mProvider" style="color:var(--primary); font-size:0.9rem;">Provider</span>
                </div>
                <div class="close" onclick="closeModal()">×</div>
            </div>
            <div class="m-body">
                <div>
                    <h3 style="color:#888; text-transform:uppercase; font-size:0.8rem; margin-bottom:10px;">Price Analytics</h3>
                    <div id="historyChart" style="width:100%; height:200px; background:rgba(0,0,0,0.2); border-radius:6px; margin-bottom:20px;"></div>
                    
                    <div style="display:grid; grid-template-columns: 1fr 1fr; gap:10px;">
                        <div style="background:#202024; padding:10px; border-radius:6px;">
                            <div style="font-size:0.7rem; color:#888;">INPUT (1M)</div>
                            <div id="mInput" style="font-size:1.1rem; color: #fff;">$0.00</div>
                        </div>
                        <div style="background:#202024; padding:10px; border-radius:6px;">
                            <div style="font-size:0.7rem; color:#888;">OUTPUT (1M)</div>
                            <div id="mOutput" style="font-size:1.1rem; color: #fff;">$0.00</div>
                        </div>
                    </div>
                </div>
                <div>
                     <h3 style="color:#888; text-transform:uppercase; font-size:0.8rem; margin-bottom:10px;">Capabilities</h3>
                     <div id="mTags" style="display:flex; flex-wrap:wrap; gap:5px; margin-bottom:20px;"></div>
                     
                     <h3 style="color:#888; text-transform:uppercase; font-size:0.8rem; margin-bottom:10px;">Technical Specs</h3>
                     <div style="background:#202024; padding:15px; border-radius:6px;">
                        <div style="display:flex; justify-content:space-between; margin-bottom:8px; border-bottom:1px solid #333; padding-bottom:8px;">
                            <span style="color:#aaa; font-size:0.9rem;">Context Window</span>
                            <span id="mCtx" style="color:#fff;">-</span>
                        </div>
                        <div style="display:flex; justify-content:space-between; padding-top:5px;">
                            <span style="color:#aaa; font-size:0.9rem;">24h Trend</span>
                            <span id="mTrend" style="color:#fff;">-</span>
                        </div>
                     </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        const modelsDB = {json.dumps(js_models_db)};
        let chartInstance = null;

        // --- Tabs ---
        function switchView(viewId) {{
            document.querySelectorAll('.view-section').forEach(el => el.classList.remove('active'));
            document.getElementById(viewId + '-view').classList.add('active');
            
            document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
            event.target.classList.add('active');
            
            // Resize charts if needed
            if(chartInstance) chartInstance.resize();
        }}

        // --- Modal ---
        function openModal(modelName) {{
            const data = modelsDB[modelName];
            if(!data) return;

            document.getElementById('mName').innerText = data.model;
            document.getElementById('mProvider').innerText = data.provider;
            
            const inp = data.fields?.pricing?.value?.input || 0;
            const out = data.fields?.pricing?.value?.output || 0;
            document.getElementById('mInput').innerText = '$' + inp.toFixed(5);
            document.getElementById('mOutput').innerText = '$' + out.toFixed(5);
            document.getElementById('mCtx').innerText = (data.fields?.context_window?.value || 0).toLocaleString();
            
            const trend = data.change_24h;
            const trendEl = document.getElementById('mTrend');
            trendEl.innerText = (trend > 0 ? "+" : "") + trend.toFixed(2) + "%";
            trendEl.style.color = trend >= 0 ? 'var(--success)' : 'var(--danger)';
            
            const tagsDiv = document.getElementById('mTags');
            tagsDiv.innerHTML = data.tags.map(t => `<span class="tag" style="padding:5px 10px; font-size:0.8rem;">${{t}}</span>`).join('');

            document.getElementById('modalOverlay').style.display = 'flex';
            
            // Render History Chart
            setTimeout(() => {{
                if(chartInstance) chartInstance.dispose();
                chartInstance = echarts.init(document.getElementById('historyChart'));
                
                const dates = data.history_input.map(x => x.date);
                const vals = data.history_input.map(x => x.price);
                
                chartInstance.setOption({{
                    backgroundColor: 'transparent',
                    tooltip: {{ trigger: 'axis' }},
                    grid: {{ top: 10, right: 10, bottom: 20, left: 50 }},
                    xAxis: {{ type: 'category', data: dates, show: false }},
                    yAxis: {{ type: 'value', splitLine: {{ lineStyle: {{ color: '#333' }} }} }},
                    series: [{{
                        data: vals, type: 'line', smooth: true,
                        areaStyle: {{ opacity: 0.1, color: '#3b82f6' }},
                        lineStyle: {{ color: '#3b82f6', width: 3 }},
                        symbol: 'none'
                    }}]
                }});
            }}, 50);
        }}

        function closeModal() {{
             document.getElementById('modalOverlay').style.display = 'none';
        }}
        
        function clickOutside(e) {{
            if (e.target.id === 'modalOverlay') closeModal();
        }}

        // --- Filter ---
        function filterTable(input, tableId) {{
            const term = input.value.toLowerCase();
            const rows = document.querySelectorAll('#' + tableId + ' tbody tr');
            rows.forEach(r => {{
                r.style.display = r.innerText.toLowerCase().includes(term) ? '' : 'none';
            }});
        }}

        // --- Init Dashboard Charts ---
        // Scatter
        const scatterData = {json.dumps([[
            safe_float(m['fields']['pricing']['value'].get('input',0)),
            safe_float(m['fields']['pricing']['value'].get('output',0))
        ] for m in enriched_registry])};

        const scChart = echarts.init(document.getElementById('scatterChart'));
        scChart.setOption({{
             tooltip: {{ trigger: 'item' }},
             grid: {{ top: 20, right: 20, bottom: 20, left: 40 }},
             xAxis: {{ type: 'value', splitLine: {{ show: false }} }},
             yAxis: {{ type: 'value', splitLine: {{ lineStyle: {{ color: '#333' }} }} }},
             series: [{{ type: 'scatter', symbolSize: 6, data: scatterData, itemStyle: {{ color: '#8b5cf6' }} }}]
        }});

        // Bar
        const provData = {json.dumps(list(Counter([m['provider'] for m in enriched_registry]).most_common(10)))};
        const barChart = echarts.init(document.getElementById('barChart'));
        barChart.setOption({{
            tooltip: {{ trigger: 'axis' }},
            grid: {{ top: 10, right: 10, bottom: 20, left: 10, containLabel: true }},
            yAxis: {{ type: 'category', data: provData.map(x => x[0]), axisLabel: {{ color: '#aaa' }} }},
            xAxis: {{ type: 'value', show: false }},
            series: [{{ 
                type: 'bar', data: provData.map(x => x[1]), 
                itemStyle: {{ borderRadius: [0, 4, 4, 0], color: '#3b82f6' }},
                label: {{ show: true, position: 'right', color: '#fff' }}
            }}]
        }});
        
        window.addEventListener('resize', () => {{
            scChart.resize();
            barChart.resize();
            if(chartInstance) chartInstance.resize();
        }});

    </script>
</body>
</html>
    """
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Generated v3 Dashboard: {OUTPUT_FILE}")

if __name__ == "__main__":
    generate_dashboard()
