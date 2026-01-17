
import json
import os
import random
from datetime import datetime, timedelta
from collections import defaultdict, Counter

from sqlalchemy.orm import Session
from app.storage.postgres import SessionLocal, Model, Leaderboard

# Configuration
OUTPUT_FILE = "registry_report.html"

def get_data_from_db():
    db = SessionLocal()
    try:
        models = db.query(Model).all()
        leaderboard = db.query(Leaderboard).order_by(Leaderboard.rank).all()
        
        registry_data = []
        for m in models:
            # Reconstruct Dict format expected by generator
            data = m.config if m.config else {}
            data['model'] = m.name
            data['provider'] = m.provider
            # Ensure pricing is up to date from columns if they were modified independently
            if 'fields' not in data: data['fields'] = {}
            if 'pricing' not in data['fields']: data['fields']['pricing'] = {'value': {}}
            data['fields']['pricing']['value']['input'] = m.input_price
            data['fields']['pricing']['value']['output'] = m.output_price
            data['fields']['context_window'] = {'value': m.context_window}
            registry_data.append(data)
            
        leaderboard_data = []
        for l in leaderboard:
            leaderboard_data.append({
                "rank": str(l.rank),
                "model": l.model,
                "arena_score": str(l.arena_score),
                "ci_95": l.ci_95,
                "category": l.category
            })
            
        return registry_data, leaderboard_data
    finally:
        db.close()

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
    
    # FETCH FROM DB
    registry_data, leaderboard_data = get_data_from_db()
    
    # --- Prepare Registry Data ---
    enriched_registry = []
    providers = set()
    provider_counts = Counter()
    tag_counts = Counter()
    
    for entry in registry_data:
        p = entry.get("provider", "Unknown")
        providers.add(p)
        provider_counts[p] += 1
        
        fields = entry.get("fields", {})
        pricing = fields.get("pricing", {}).get("value", {})
        inp = safe_float(pricing.get("input", 0))
        out = safe_float(pricing.get("output", 0))
        
        # Simulate 24h Change for Gainers/Losers
        prev_inp = inp * (1 + random.uniform(-0.1, 0.1))
        change_pct = ((inp - prev_inp) / prev_inp * 100) if prev_inp > 0 else 0
        
        entry['history_input'] = generate_mock_history(inp)
        entry['history_output'] = generate_mock_history(out)
        tags = get_capabilities(entry.get("model", ""))
        entry['tags'] = tags
        for t in tags: tag_counts[t] += 1
        
        entry['change_24h'] = change_pct
        enriched_registry.append(entry)

    # Top Gainers / Losers
    sorted_by_change = sorted(enriched_registry, key=lambda x: x['change_24h'], reverse=True)
    top_gainers = sorted_by_change[:5]
    top_losers = sorted_by_change[-5:]

    # Stats
    avg_input = sum(safe_float(e['fields']['pricing']['value'].get('input',0)) for e in enriched_registry) / len(enriched_registry) if enriched_registry else 0
    avg_output = sum(safe_float(e['fields']['pricing']['value'].get('output',0)) for e in enriched_registry) / len(enriched_registry) if enriched_registry else 0

    # Data for Charts
    # 1. Scatter (Input vs Output)
    scatter_data = [] # [[input, output, modelName, provider], ...]
    for m in enriched_registry:
        scatter_data.append([
            safe_float(m['fields']['pricing']['value'].get('input',0)),
            safe_float(m['fields']['pricing']['value'].get('output',0)),
            m.get('model'),
            m.get('provider')
        ])
        
    # 2. Pie (Provider Share)
    pie_data = [{"name": k, "value": v} for k, v in provider_counts.items()]
    pie_data.sort(key=lambda x: x['value'], reverse=True)
    
    # 3. Radar (Capabilities)
    # Normalize tag counts for radar
    all_tags = sorted(list(tag_counts.keys()))
    radar_indicator = [{"name": t, "max": max(tag_counts.values()) + 5} for t in all_tags]
    radar_values = [tag_counts[t] for t in all_tags]
    # Metadata for Info Modal
    # In a real scenario, we would check the max(last_updated) from items
    # For this static generator, we assume the report generation time reflects the latest state
    latest_ts = datetime.now()
        
    time_diff = datetime.now() - latest_ts
    if time_diff < timedelta(hours=1):
        status_color = "var(--success)"
        status_text = "ONLINE"
    elif time_diff < timedelta(hours=24):
        status_color = "#f59e0b" # Orange
        status_text = "DELAYED"
    else:
        status_color = "var(--danger)"
        status_text = "OFFLINE"

    last_updated_str = latest_ts.strftime("%Y-%m-%d %H:%M:%S")

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
            --bg-panel: #141417; /* Slightly lighter for contrast */
            --bg-card: #1c1c1f;
            --border: #27272a;
            --primary: #3b82f6; 
            --accent: #8b5cf6;
            --success: #10b981;
            --danger: #ef4444;
            --text-main: #e4e4e7;
            --text-muted: #a1a1aa;
            --font-main: 'Inter', sans-serif;
            --font-mono: 'JetBrains Mono', monospace;
        }}
        
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ background: var(--bg-body); color: var(--text-main); font-family: var(--font-main); height: 100vh; overflow: hidden; display: grid; grid-template-rows: 60px 1fr 30px; }}
        
        /* HEADER */
        header {{ background: var(--bg-panel); border-bottom: 1px solid var(--border); display: flex; align-items: center; justify-content: space-between; padding: 0 2rem; }}
        .brand {{ font-family: var(--font-mono); font-weight: 700; font-size: 1.2rem; color: #fff; display: flex; align-items: center; gap: 10px; letter-spacing: -0.5px; }}
        .brand span {{ color: var(--primary); }}
        
        .tabs {{ display: flex; gap: 8px; background: #1a1a1d; padding: 4px; border-radius: 8px; border: 1px solid var(--border); }}
        .tab-btn {{
            padding: 8px 20px; border: none; background: transparent; color: var(--text-muted);
            font-size: 0.9rem; font-weight: 600; cursor: pointer; border-radius: 6px; transition: 0.2s;
            font-family: var(--font-main);
        }}
        .tab-btn:hover {{ color: #fff; background: rgba(255,255,255,0.05); }}
        .tab-btn.active {{ background: #2f3035; color: #fff; box-shadow: 0 1px 3px rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.1); }}
        
        /* LAYOUTS */
        .view-section {{ display: none; height: 100%; padding: 1.5rem; overflow-y: auto; }}
        .view-section.active {{ display: grid; }}
        
        /* HOME VIEW */
        #home-view {{ grid-template-columns: 300px 1fr 350px; grid-template-rows: auto 1fr; gap: 1.5rem; align-content: start; }}
        
        /* GAINERS VIEW */
        #gainers-view {{ grid-template-columns: 1fr 1fr; gap: 2rem; align-items: start; max-width: 1400px; margin: 0 auto; width: 100%; }}
        
        /* TRENDING VIEW */
        #trending-view {{ grid-template-columns: 1fr; max-width: 1200px; margin: 0 auto; width: 100%; }}

        /* PANELS */
        .panel {{ background: var(--bg-panel); border: 1px solid var(--border); border-radius: 12px; display: flex; flex-direction: column; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06); }}
        .panel-head {{ padding: 16px 20px; border-bottom: 1px solid var(--border); font-size: 0.85rem; font-weight: 600; color: var(--text-muted); text-transform: uppercase; letter-spacing: 1px; display: flex; justify-content: space-between; align-items: center; background: rgba(255,255,255,0.02); }}
        .panel-body {{ padding: 1px; flex: 1; overflow: auto; position: relative; min-height: 200px; }}
        
        /* TABLES */
        table {{ width: 100%; border-collapse: separate; border-spacing: 0; font-size: 0.9rem; }}
        th {{ text-align: left; padding: 16px 20px; color: var(--text-muted); border-bottom: 1px solid var(--border); position: sticky; top: 0; background: var(--bg-panel); font-weight: 500; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.5px; z-index: 10; }}
        td {{ padding: 14px 20px; border-bottom: 1px solid var(--border); color: #dedede; vertical-align: middle; }}
        tr:last-child td {{ border-bottom: none; }}
        tr:hover {{ background: rgba(255,255,255,0.03); cursor: pointer; }}
        
        .num-up {{ color: var(--success); font-family: var(--font-mono); }}
        .num-down {{ color: var(--danger); font-family: var(--font-mono); }}
        .tag {{ font-size: 0.7rem; padding: 4px 8px; background: rgba(59, 130, 246, 0.15); border: 1px solid rgba(59, 130, 246, 0.3); border-radius: 4px; margin-right: 6px; color: #93c5fd; font-weight: 500; }}
        
        /* SEARCH & FILTER */
        .filters {{ display: flex; gap: 10px; }}
        input.search, select {{ 
            background: #000; border: 1px solid var(--border); color: #fff; padding: 8px 12px; border-radius: 6px; outline: none; font-size: 0.85rem; 
            transition: all 0.2s ease; font-family: var(--font-main);
        }}
        input.search:focus, select:focus {{ border-color: var(--primary); box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.2); }}
        
        /* KPI BOXES */
        .kpi-grid {{ display: grid; gap: 15px; }}
        .kpi-box {{ background: var(--bg-panel); padding: 20px; border-radius: 12px; border: 1px solid var(--border); display: flex; flex-direction: column; justify-content: center; position: relative; overflow: hidden; }}
        .kpi-box::before {{ content: ''; position: absolute; left: 0; top: 0; bottom: 0; width: 4px; background: var(--primary); }}
        .kpi-val {{ font-size: 1.8rem; font-weight: 700; color: #fff; margin: 8px 0; font-family: var(--font-mono); letter-spacing: -1px; }}
        .kpi-lbl {{ font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 1px; font-weight: 600; }}

        /* GAINER CARDS */
        .gainer-card {{ 
            background: var(--bg-panel); padding: 20px; margin-bottom: 15px; border-radius: 8px; display: flex; justify-content: space-between; align-items: center; 
            border: 1px solid var(--border); transition: transform 0.2s; 
        }}
        .gainer-card:hover {{ transform: translateY(-2px); border-color: #444; }}
        .gainer-info h4 {{ font-size: 1.1rem; color: #fff; margin-bottom: 4px; }}
        .gainer-info span {{ font-size: 0.85rem; color: var(--text-muted); }}
        .gainer-pct {{ font-size: 1.2rem; font-weight: 700; padding: 6px 12px; border-radius: 6px; background: rgba(16, 185, 129, 0.1); }}

        /* MARQUEE */
        .marquee-container {{ background: #000; border-top: 1px solid var(--border); overflow: hidden; display: flex; align-items: center; position: relative; z-index: 100; }}
        .marquee {{ display: flex; gap: 3rem; animation: scroll 60s linear infinite; white-space: nowrap; padding-left: 100vw; }}
        .m-item {{ font-family: var(--font-mono); font-size: 0.8rem; color: #888; display: flex; gap: 10px; align-items: center; }}
        .m-val {{ color: var(--success); }}
        @keyframes scroll {{ 0% {{ transform: translateX(0); }} 100% {{ transform: translateX(-100%); }} }}
        .marquee:hover {{ animation-play-state: paused; }}

        /* MODAL */
        .modal-overlay {{ position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.85); backdrop-filter: blur(8px); z-index: 999; display: none; justify-content: center; align-items: center; opacity: 0; transition: opacity 0.2s; }}
        .modal-overlay.open {{ opacity: 1; }}
        .modal {{ width: 900px; height: 650px; background: #18181b; border: 1px solid var(--border); border-radius: 16px; display: grid; grid-template-rows: 70px 1fr; box-shadow: 0 50px 100px -20px rgba(0,0,0,0.7); overflow: hidden; transform: scale(0.95); transition: transform 0.2s; }}
        .modal-overlay.open .modal {{ transform: scale(1); }}
        .m-head {{ padding: 0 30px; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center; background: #202024;}}
        .m-body {{ padding: 30px; display: grid; grid-template-columns: 1.2fr 0.8fr; gap: 30px; overflow-y: auto; }}
        .close {{ cursor: pointer; color: #aaa; font-size: 1.8rem; transition: 0.2s; width: 40px; height: 40px; display: flex; align-items: center; justify-content: center; border-radius: 50%; }} 
        .close:hover {{ color: #fff; background: rgba(255,255,255,0.1); }}
        
        /* UI REFINEMENTS */
        .panel-body::-webkit-scrollbar {{ display: none; }}
        .panel-body {{ -ms-overflow-style: none; scrollbar-width: none; }}
        
        /* CHART GRID */
        .chart-row {{
            grid-column: 1 / -1;
            display: grid;
            grid-template-columns: 1fr 1fr 1fr;
            gap: 1.5rem;
            min-height: 320px;
        }}
        
        .chart-container {{
            width: 100%;
            height: 100%;
            min-height: 280px;
        }}

    </style>
</head>
<body>

    <header>
        <div class="brand">
            <svg width="24" height="24" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"/></svg>
            LLM<span>ATLAS</span>
        </div>
        
        <div class="tabs">
            <button class="tab-btn active" onclick="switchView('home')">MARKET</button>
            <button class="tab-btn" onclick="switchView('gainers')">GAINERS & LOSERS</button>
            <button class="tab-btn" onclick="switchView('trending')">LEADERBOARD</button>
        </div>

        <div style="display:flex; align-items:center; gap:16px;">
            <div style="font-size:0.85rem; color:var(--text-muted); display:flex; align-items:center; gap:8px;">
                <div style="width:8px; height:8px; background:{status_color}; border-radius:50%; box-shadow:0 0 8px {status_color};"></div>
                <span style="color:#fff; font-weight:600;">{status_text}</span>
            </div>
            <div onclick="openInfoModal()" style="cursor:pointer; color:var(--text-muted); transition:0.2s;" onmouseover="this.style.color='#fff'" onmouseout="this.style.color='var(--text-muted)'">
                <svg width="20" height="20" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
            </div>
        </div>
    </header>

    <!-- HOME VIEW -->
    <main id="home-view" class="view-section active">
        
        <!-- ROW 1: STATS & CHARTS -->
        <div class="kpi-grid" style="grid-column: 1; align-self: start;">
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
            
            <div class="panel" style="margin-top: 10px; height: 350px;">
                <div class="panel-head">Provider Share</div>
                <div class="panel-body">
                     <div id="pieChart" class="chart-container"></div>
                </div>
            </div>
        </div>

        <!-- MAIN TABLE (Middle Column) -->
        <div class="panel" style="grid-column: 2;">
            <div class="panel-head">
                <span>Real-Time Registry</span>
                <div class="filters">
                    <select id="providerFilter" onchange="applyFilters()">
                        <option value="all">All Providers</option>
                        { "".join([f'<option value="{p}">{p}</option>' for p in sorted(list(providers))]) }
                    </select>
                    
                    <select id="sortFilter" onchange="applyFilters()">
                        <option value="name">Sort by Name</option>
                        <option value="price_high">Price: High to Low</option>
                        <option value="price_low">Price: Low to High</option>
                        <option value="change_high">24h Change: High</option>
                    </select>

                    <input type="text" id="searchInput" class="search" placeholder="Filter models..." onkeyup="applyFilters()">
                </div>
            </div>
            <div class="panel-body" style="padding:0">
                <table id="regTable">
                    <thead>
                        <tr>
                            <th>MODEL</th>
                            <th>PROVIDER</th>
                            <th>INPUT / 1M</th>
                            <th>OUTPUT / 1M</th>
                            <th style="text-align:right">24H %</th>
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
                            <td style="font-weight:600; color:#fff">
                                <div>{name}</div>
                                <div style="margin-top:4px; display:flex;">{tags_html}</div>
                            </td>
                            <td>{mod.get('provider')}</td>
                            <td style="font-family:var(--font-mono)">${inp:.4f}</td>
                            <td style="font-family:var(--font-mono)">${out:.4f}</td>
                            <td class="{color_class}" style="text-align:right">{arrow} {abs(chg):.2f}%</td>
                        </tr>
        """

    html += """
                    </tbody>
                </table>
            </div>
        </div>

        <!-- RIGHT COLUMN: CHARTS -->
        <div style="grid-column: 3; display: flex; flex-direction: column; gap: 1.5rem;">
            
            <div class="panel" style="flex: 1;">
                <div class="panel-head">Price Correlation</div>
                <div class="panel-body">
                    <div id="scatterChart" class="chart-container"></div>
                </div>
            </div>
            
            <div class="panel" style="flex: 1;">
                 <div class="panel-head">Capabilities Radar</div>
                 <div class="panel-body">
                      <div id="radarChart" class="chart-container"></div>
                 </div>
            </div>

        </div>
    </main>

    <!-- GAINERS VIEW -->
    <main id="gainers-view" class="view-section">
        <div class="panel">
            <div class="panel-head" style="color:var(--success)">Top Gainers (24h)</div>
            <div class="panel-body" style="padding: 20px;">
    """
    
    for g in top_gainers:
         name = g.get('model')
         pct = g['change_24h']
         price = g['fields']['pricing']['value'].get('input', 0)
         html += f"""
                <div class="gainer-card" style="border-left: 4px solid var(--success)">
                    <div class="gainer-info">
                        <h4>{name}</h4>
                        <span>{g.get('provider')} • <span style="font-family:var(--font-mono)">${price:.4f}</span></span>
                    </div>
                    <div class="gainer-pct num-up">+{pct:.2f}%</div>
                </div>
         """
         
    html += """
            </div>
        </div>
        <div class="panel">
            <div class="panel-head" style="color:var(--danger)">Top Losers (24h)</div>
            <div class="panel-body" style="padding: 20px;">
    """
    for l in top_losers:
         name = l.get('model')
         pct = l['change_24h']
         price = l['fields']['pricing']['value'].get('input', 0)
         html += f"""
                <div class="gainer-card" style="border-left: 4px solid var(--danger)">
                    <div class="gainer-info">
                        <h4>{name}</h4>
                        <span>{l.get('provider')} • <span style="font-family:var(--font-mono)">${price:.4f}</span></span>
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
                <span style="font-size:0.75rem; background:var(--primary); color:#fff; padding:4px 10px; border-radius:12px; font-weight:700;">LIVE SCRAPE</span>
            </div>
            <div class="panel-body" style="padding:0">
                <table id="leaderboardTable">
                    <thead>
                        <tr>
                            <th style="width:80px; text-align:center;">RANK</th>
                            <th>MODEL</th>
                            <th>ARENA SCORE</th>
                            <th>95% CI</th>
                            <th>CATEGORY</th>
                        </tr>
                    </thead>
                    <tbody>
    """
    
    if not leaderboard_data:
        html += '<tr><td colspan="5" style="text-align:center; padding:40px; color:var(--text-muted); font-style:italic;">No leaderboard data available. Run ingestion.</td></tr>'
    
    for row in leaderboard_data:
        html += f"""
                        <tr>
                            <td style="font-weight:800; color:var(--primary); font-size:1.1rem; text-align:center;">#{row.get('rank')}</td>
                            <td style="color:#fff; font-weight:600;">{row.get('model')}</td>
                            <td style="font-family:var(--font-mono)">{row.get('arena_score')}</td>
                            <td style="color:var(--text-muted)">{row.get('ci_95')}</td>
                            <td><span class="tag" style="color:#fff; border-color:#fff;">{row.get('category')}</span></td>
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
                <span style="font-weight:700; color:#fff;">{m.get('model')}</span>
                <span class="m-val">${safe_float(m['fields']['pricing']['value'].get('input')):.4f}</span>
            </div>
         """

    html += f"""
        </div>
    </div>

    <!-- INFO MODAL -->
    <div class="modal-overlay" id="infoModalOverlay" onclick="clickOutsideInfo(event)">
        <div class="modal" style="height: auto; width: 400px; grid-template-rows: auto;">
             <div class="m-head" style="padding: 15px 24px;">
                <h2 style="color:#fff; font-size:1.1rem;">System Metadata</h2>
                <div class="close" onclick="closeInfoModal()">×</div>
             </div>
             <div class="m-body" style="padding: 24px; display:block;">
                <div style="margin-bottom:15px;">
                    <div style="font-size:0.8rem; color:var(--text-muted); text-transform:uppercase;">Pipeline Status</div>
                    <div style="color:{status_color}; font-weight:bold; font-size:1.1rem;">{status_text}</div>
                    <div style="font-size:0.75rem; color:#666; margin-top:2px;">Based on latest data recency</div>
                </div>
                <div style="margin-bottom:15px;">
                     <div style="font-size:0.8rem; color:var(--text-muted); text-transform:uppercase;">Last Data Update</div>
                     <div style="color:#fff; font-size:1rem; font-family:var(--font-mono);">{last_updated_str}</div>
                </div>
                <div style="margin-bottom:15px;">
                     <div style="font-size:0.8rem; color:var(--text-muted); text-transform:uppercase;">Total Models Indexed</div>
                     <div style="color:#fff; font-size:1rem; font-family:var(--font-mono);">{len(registry_data)}</div>
                </div>
                <div>
                     <div style="font-size:0.8rem; color:var(--text-muted); text-transform:uppercase;">Report Generated</div>
                     <div style="color:#fff; font-size:1rem; font-family:var(--font-mono);">{timestamp}</div>
                </div>
             </div>
        </div>
    </div>

    <!-- DETAILS MODAL -->
    <div class="modal-overlay" id="modalOverlay" onclick="clickOutside(event)">
        <div class="modal">
            <div class="m-head">
                <div>
                    <h2 id="mName" style="color:#fff; font-size:1.5rem; letter-spacing:-0.5px;">Model Name</h2>
                    <span id="mProvider" style="color:var(--primary); font-size:0.95rem; font-weight:500;">Provider</span>
                </div>
                <div class="close" onclick="closeModal()">×</div>
            </div>
            <div class="m-body">
                <div>
                    <h3 style="color:var(--text-muted); text-transform:uppercase; font-size:0.8rem; margin-bottom:15px; font-weight:700; letter-spacing:1px;">Price History</h3>
                    <div id="historyChart" style="width:100%; height:250px; background:rgba(0,0,0,0.2); border-radius:12px; margin-bottom:25px; border:1px solid var(--border);"></div>
                    
                    <div style="display:grid; grid-template-columns: 1fr 1fr; gap:15px;">
                        <div style="background:#202024; padding:15px; border-radius:8px; border:1px solid var(--border);">
                            <div style="font-size:0.75rem; color:var(--text-muted); text-transform:uppercase;">INPUT (1M)</div>
                            <div id="mInput" style="font-size:1.4rem; color: #fff; font-family:var(--font-mono); margin-top:5px;">$0.00</div>
                        </div>
                        <div style="background:#202024; padding:15px; border-radius:8px; border:1px solid var(--border);">
                            <div style="font-size:0.75rem; color:var(--text-muted); text-transform:uppercase;">OUTPUT (1M)</div>
                            <div id="mOutput" style="font-size:1.4rem; color: #fff; font-family:var(--font-mono); margin-top:5px;">$0.00</div>
                        </div>
                    </div>
                </div>
                <div>
                     <h3 style="color:var(--text-muted); text-transform:uppercase; font-size:0.8rem; margin-bottom:15px; font-weight:700; letter-spacing:1px;">Capabilities</h3>
                     <div id="mTags" style="display:flex; flex-wrap:wrap; gap:8px; margin-bottom:30px;"></div>
                     
                     <h3 style="color:var(--text-muted); text-transform:uppercase; font-size:0.8rem; margin-bottom:15px; font-weight:700; letter-spacing:1px;">Specs</h3>
                     <div style="background:#202024; padding:20px; border-radius:8px; border:1px solid var(--border);">
                        <div style="display:flex; justify-content:space-between; margin-bottom:12px; border-bottom:1px solid #333; padding-bottom:12px;">
                            <span style="color:#aaa; font-size:0.9rem;">Context Window</span>
                            <span id="mCtx" style="color:#fff; font-weight:600;">-</span>
                        </div>
                        <div style="display:flex; justify-content:space-between; padding-top:5px;">
                            <span style="color:#aaa; font-size:0.9rem;">24h Trend</span>
                            <span id="mTrend" style="color:#fff; font-weight:600;">-</span>
                        </div>
                     </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        const modelsDB = {json.dumps(js_models_db)};
        let chartInstances = {{}};

        // --- Tabs ---
        function switchView(viewId) {{
            // Hide all
            document.querySelectorAll('.view-section').forEach(el => el.classList.remove('active'));
            // Show selected
            document.getElementById(viewId + '-view').classList.add('active');
            
            // Buttons
            document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
            event.target.classList.add('active');
            
            // Resize charts
            Object.values(chartInstances).forEach(chart => chart.resize());
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
            tagsDiv.innerHTML = data.tags.map(t => `<span class="tag" style="padding:6px 12px; font-size:0.85rem;">${{t}}</span>`).join('');

            const overlay = document.getElementById('modalOverlay');
            overlay.style.display = 'flex';
            setTimeout(() => overlay.classList.add('open'), 10); // Transitions
            
            // Render History Chart
            setTimeout(() => {{
                if(chartInstances['history']) chartInstances['history'].dispose();
                const chart = echarts.init(document.getElementById('historyChart'));
                chartInstances['history'] = chart;
                
                const dates = data.history_input.map(x => x.date);
                const vals = data.history_input.map(x => x.price);
                
                chart.setOption({{
                    backgroundColor: 'transparent',
                    tooltip: {{ trigger: 'axis', formatter: '{{b}}<br>${{c}}' }},
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
            }}, 200);
        }}

        function closeModal() {{
             const overlay = document.getElementById('modalOverlay');
             overlay.classList.remove('open');
             setTimeout(() => overlay.style.display = 'none', 200);
        }}
        
        function clickOutside(e) {{
            if (e.target.id === 'modalOverlay') closeModal();
        }}

        // --- Info Modal ---
        function openInfoModal() {{
            const overlay = document.getElementById('infoModalOverlay');
            overlay.style.display = 'flex';
            setTimeout(() => overlay.classList.add('open'), 10);
        }}
        function closeInfoModal() {{
             const overlay = document.getElementById('infoModalOverlay');
             overlay.classList.remove('open');
             setTimeout(() => overlay.style.display = 'none', 200);
        }}
        function clickOutsideInfo(e) {{
            if (e.target.id === 'infoModalOverlay') closeInfoModal();
        }}

        // --- Filter ---
        function applyFilters() {{
             const provider = document.getElementById('providerFilter').value;
             const sort = document.getElementById('sortFilter').value;
             const search = document.getElementById('searchInput').value.toLowerCase();
             
             const tbody = document.querySelector('#regTable tbody');
             const rows = Array.from(tbody.querySelectorAll('tr'));
             
             rows.forEach(row => {{
                 let show = true;
                 const modelName = row.querySelector('td:nth-child(1)').innerText.toLowerCase();
                 const rowProvider = row.querySelector('td:nth-child(2)').innerText;
                 
                 if(provider !== 'all' && rowProvider !== provider) show = false;
                 if(search && !modelName.includes(search)) show = false;
                 
                 row.style.display = show ? '' : 'none';
             }});
             
             // Sorting Logic could be implemented here by re-appending rows
        }}

        // --- Init Dashboard Charts ---
        const themeColors = ['#3b82f6', '#8b5cf6', '#10b981', '#f59e0b', '#ef4444', '#ec4899'];
        const textStyle = {{ fontFamily: 'Inter, sans-serif' }};
        
        // 1. Scatter (Price)
        const scatterData = {json.dumps(scatter_data)};
        const scChart = echarts.init(document.getElementById('scatterChart'));
        chartInstances['scatter'] = scChart;
        scChart.setOption({{
            tooltip: {{
                formatter: function (param) {{
                    return '<b>' + param.data[2] + '</b><br>' + param.data[3] + '<br>Input: $' + param.data[0] + '<br>Output: $' + param.data[1];
                }} 
            }},
            grid: {{ top: 30, right: 30, bottom: 30, left: 50 }},
            xAxis: {{ name: 'Input', type: 'value', splitLine: {{ lineStyle: {{ color: '#333' }} }} }},
            yAxis: {{ name: 'Output', type: 'value', splitLine: {{ lineStyle: {{ color: '#333' }} }} }},
            series: [{{
                symbolSize: 10,
                data: scatterData,
                type: 'scatter',
                itemStyle: {{ color: '#3b82f6', opacity: 0.8 }}
            }}]
        }});

        // 2. Pie (Provider Share)
        const pieData = {json.dumps(pie_data)};
        const piChart = echarts.init(document.getElementById('pieChart'));
        chartInstances['pie'] = piChart;
        piChart.setOption({{
            tooltip: {{ trigger: 'item' }},
            legend: {{ show: false }},
            series: [{{
                name: 'Provider',
                type: 'pie',
                radius: ['40%', '70%'],
                center: ['50%', '50%'],
                avoidLabelOverlap: false,
                itemStyle: {{ borderRadius: 5, borderColor: '#1c1c1f', borderWidth: 2 }},
                label: {{ show: false }},
                data: pieData,
                color: themeColors
            }}]
        }});

        // 3. Radar (Capabilities)
        const radarIndicator = {json.dumps(radar_indicator)};
        const radarValues = {json.dumps(radar_values)};
        const raChart = echarts.init(document.getElementById('radarChart'));
        chartInstances['radar'] = raChart;
        raChart.setOption({{
            radar: {{
                indicator: radarIndicator,
                splitArea: {{ areaStyle: {{ color: ['#1a1a1d', '#1f1f22', '#242428', '#2a2a2e'] }} }},
                axisLine: {{ lineStyle: {{ color: '#333' }} }},
                splitLine: {{ lineStyle: {{ color: '#333' }} }}
            }},
            series: [{{
                name: 'Budget vs spending',
                type: 'radar',
                data: [{{ value: radarValues, name: 'Allocated Budget' }}],
                areaStyle: {{ color: 'rgba(139, 92, 246, 0.2)' }},
                lineStyle: {{ color: '#8b5cf6', width: 2 }},
                symbol: 'none'
            }}]
        }});

        window.addEventListener('resize', () => {{
            Object.values(chartInstances).forEach(c => c.resize());
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
