"""
dashboard.py — Enterprise Personnel & Identity Verification Portal
High-performance personnel verification and workforce directory engine.
"""

import html
import re
from typing import List, Dict, Any


def clean_address_text(addr: str | None) -> str:
    """Format delimited address strings into readable text."""
    if not addr:
        return "Not on file"
    cleaned = re.sub(r"[!]+", ", ", addr)
    cleaned = re.sub(r"\s*,\s*", ", ", cleaned).strip(" ,")
    return html.escape(cleaned)


def _get_initials(name: str | None) -> str:
    """Generate 2-letter uppercase initials for avatar badge."""
    if not name or name.strip() in ("", "N/A", "NULL"):
        return "ID"
    parts = name.strip().split()
    if len(parts) >= 2:
        return f"{parts[0][0]}{parts[1][0]}".upper()
    return name[:2].upper()


def _query_icon(query: str) -> str:
    q = query.strip()
    if ":" in q:
        prefix = q.split(":", 1)[0].strip().lower()
        return {
            "mobile": "📱", "id": "🪪", "name": "👤",
            "fname": "👥", "address": "📍", "circle": "🌐",
            "email": "✉️", "alt": "📞", "oid": "🔗",
        }.get(prefix, "🔍")
    digits = re.sub(r"[\s\-+]", "", q)
    if digits.isdigit() and len(digits) >= 8:
        return "📱"
    return "👤"


def _render_oid(oid: str) -> str:
    """Render professional profile or auxiliary identifier chip."""
    if not oid or oid in ("N/A", "NULL", "None"):
        return ""
    clean_oid = html.escape(oid)
    is_link = clean_oid.startswith("http://") or clean_oid.startswith("https://") or "linkedin.com" in clean_oid
    link_html = f"<a href='https://{clean_oid.replace('https://', '').replace('http://', '')}' target='_blank' style='color:#38bdf8; text-decoration:none;'>{clean_oid} ↗</a>" if is_link else clean_oid

    return f"""
    <div class='detail-item full-width'>
        <span class='detail-label'>Professional / Auxiliary ID</span>
        <span class='detail-value copyable' onclick='copyText("{clean_oid}")'>{link_html}</span>
    </div>
    """


def render_dashboard_html(
    query: str,
    search_data_list: List[Dict[str, Any]],
    limit: int = 25,
    search_time_ms: float = 0.0,
) -> str:
    escaped_query = html.escape(query)
    total_found = sum(item.get("count", 0) for item in search_data_list)

    nav_links = []
    blocks_html = []

    if not search_data_list and not query:
        content_rendered = """
        <div class='welcome-card'>
            <div class='welcome-header'>
                <div class='welcome-badge'>Enterprise Directory Intelligence</div>
                <h2>Personnel & Identity Verification System</h2>
                <p class='welcome-desc'>
                    Secure high-throughput verification platform powered by DuckDB columnar streaming.
                    Query comprehensive workforce, KYC identity indices, and personnel contact records in real-time.
                </p>
            </div>

            <div class='grid-features'>
                <div class='feature-box'>
                    <div class='feature-icon'>🪪</div>
                    <div class='feature-title'>National ID & KYC Lookup</div>
                    <div class='feature-desc'>Instant exact-match lookups across government identification numbers, Aadhaar, and national registry records.</div>
                </div>
                <div class='feature-box'>
                    <div class='feature-icon'>📱</div>
                    <div class='feature-title'>Telecom & Contact Registry</div>
                    <div class='feature-desc'>Pruned partition searching across primary and secondary telecom numbers, circles, and operators.</div>
                </div>
                <div class='feature-box'>
                    <div class='feature-icon'>👥</div>
                    <div class='feature-title'>Personnel & Lineage Index</div>
                    <div class='feature-desc'>Fuzzy and lexical scoring matching personnel names, parentage / title lineage, and regional jurisdictions.</div>
                </div>
            </div>

            <div class='quick-query-section'>
                <span class='quick-label'>Sample Verification Queries:</span>
                <div class='pill-group'>
                    <a href='/?q=9810014045' class='query-pill'>📱 <code>9810014045</code></a>
                    <a href='/?q=name:rahul%20sharma' class='query-pill'>👤 <code>name:rahul sharma</code></a>
                    <a href='/?q=address:mumbai' class='query-pill'>📍 <code>address:mumbai</code></a>
                    <a href='/?q=circle:airtel' class='query-pill'>🌐 <code>circle:airtel</code></a>
                    <a href='/?q=oid:linkedin' class='query-pill'>🔗 <code>oid:linkedin</code></a>
                </div>
            </div>
        </div>
        """
        nav_rendered = """
        <a href='/' class='nav-item active'>📊 Executive Overview</a>
        <a href='/docs' target='_blank' class='nav-item'>📡 API Swagger Schema</a>
        <a href='/health' target='_blank' class='nav-item'>🩺 Engine Telemetry</a>
        """
    else:
        nav_links.append("<a href='#top' class='nav-item'>🔝 Top of Dossier</a>")

        for item in search_data_list:
            sub_q = item.get("query", "")
            results = item.get("results", [])
            count = item.get("count", 0)
            target_id = f"target-{re.sub(r'[^a-zA-Z0-9]', '', sub_q)}"
            icon = _query_icon(sub_q)
            badge_class = "badge-success" if count > 0 else "badge-muted"

            nav_links.append(
                f"<a href='#{target_id}' class='nav-item'>"
                f"<span>{icon} {html.escape(sub_q)}</span>"
                f"<span class='badge {badge_class}'>{count}</span>"
                f"</a>"
            )

            if not results:
                blocks_html.append(f"""
                <div class='block empty-block' id='{target_id}'>
                    <div class='block-title'>
                        <span>{icon} Query: <code>{html.escape(sub_q)}</code></span>
                        <span class='badge badge-danger'>0 Matches</span>
                    </div>
                    <p class='empty-text'>No verified personnel records matched this criteria in the database index.</p>
                </div>
                """)
                continue

            records_markup = []
            for idx, r in enumerate(results, 1):
                clean_addr = clean_address_text(r.get("address"))
                mob = html.escape(str(r.get("mobile") or "N/A"))
                alt = html.escape(str(r.get("alt") or "N/A"))
                name = html.escape(str(r.get("name") or "Unnamed Individual"))
                fname = html.escape(str(r.get("fname") or "Not Specified"))
                circle = html.escape(str(r.get("circle") or "General"))
                uid = html.escape(str(r.get("id") or "N/A"))
                email = html.escape(str(r.get("email") or "N/A"))
                oid = str(r.get("oid") or "N/A")
                initials = _get_initials(name)

                email_markup = f"""
                <div class='detail-item'>
                    <span class='detail-label'>Email Contact</span>
                    <span class='detail-value copyable' onclick='copyText("{email}")'>{email}</span>
                </div>
                """ if email not in ("N/A", "NULL", "NULLLLL") else ""

                records_markup.append(f"""
                <div class='personnel-card'>
                    <div class='personnel-card-header'>
                        <div class='avatar'>{initials}</div>
                        <div class='personnel-meta'>
                            <div class='personnel-name-row'>
                                <h3 class='personnel-name'>{name}</h3>
                                <span class='badge-circle'>{circle}</span>
                            </div>
                            <div class='personnel-sub'>Parentage / Title: <b>{fname}</b></div>
                        </div>
                        <div class='record-seq'>#{idx}</div>
                    </div>

                    <div class='details-grid'>
                        <div class='detail-item'>
                            <span class='detail-label'>Primary Mobile</span>
                            <span class='detail-value copyable' onclick='copyText("{mob}")'>{mob}</span>
                        </div>
                        <div class='detail-item'>
                            <span class='detail-label'>Alternate Phone</span>
                            <span class='detail-value copyable' onclick='copyText("{alt}")'>{alt}</span>
                        </div>
                        <div class='detail-item'>
                            <span class='detail-label'>Identity / Aadhaar / Gov ID</span>
                            <span class='detail-value copyable id-highlight' onclick='copyText("{uid}")'>{uid}</span>
                        </div>
                        {email_markup}
                        <div class='detail-item full-width'>
                            <span class='detail-label'>Registered Jurisdictional Address</span>
                            <span class='detail-value address-val'>{clean_addr}</span>
                        </div>
                        {_render_oid(oid)}
                    </div>
                </div>
                """)

            blocks_html.append(f"""
            <div class='block' id='{target_id}'>
                <div class='block-header'>
                    <div class='block-title'>
                        <span>{icon} <b>Query:</b> <code>{html.escape(sub_q)}</code></span>
                        <span class='badge badge-success'>{count} Verified Records</span>
                    </div>
                </div>
                <div class='personnel-list'>
                    {''.join(records_markup)}
                </div>
            </div>
            """)

        content_rendered = "\n".join(blocks_html)
        nav_rendered = "\n".join(nav_links)

    latency_chip = f"<div class='latency-chip'>⚡ Query time: {search_time_ms:.1f}ms ({total_found} hits)</div>" if search_time_ms > 0 else ""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Enterprise Personnel & Identity Verification System</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-base: #06090e;
            --bg-surface: #0c121d;
            --bg-card: #111a29;
            --bg-card-hover: #152236;
            --border: #1e293b;
            --border-hover: #334155;
            --primary: #2563eb;
            --primary-glow: rgba(37, 99, 235, 0.25);
            --accent: #38bdf8;
            --text-main: #f1f5f9;
            --text-muted: #94a3b8;
            --text-dim: #64748b;
            --success: #10b981;
            --danger: #ef4444;
        }}

        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: var(--bg-base);
            color: var(--text-main);
            line-height: 1.5;
            -webkit-font-smoothing: antialiased;
        }}

        /* App Navbar */
        .top-nav {{
            background: rgba(12, 18, 29, 0.85);
            backdrop-filter: blur(12px);
            border-bottom: 1px solid var(--border);
            padding: 14px 28px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            position: sticky;
            top: 0;
            z-index: 100;
        }}
        .brand {{
            display: flex;
            align-items: center;
            gap: 12px;
            text-decoration: none;
            color: inherit;
        }}
        .brand-logo {{
            width: 36px;
            height: 36px;
            background: linear-gradient(135deg, #2563eb, #38bdf8);
            border-radius: 9px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 800;
            font-size: 18px;
            color: #fff;
            box-shadow: 0 4px 12px var(--primary-glow);
        }}
        .brand-text h1 {{
            font-size: 15px;
            font-weight: 700;
            letter-spacing: -0.01em;
            color: #fff;
        }}
        .brand-text span {{
            font-size: 11px;
            color: var(--accent);
            text-transform: uppercase;
            letter-spacing: 0.06em;
            font-weight: 600;
        }}
        .nav-links {{
            display: flex;
            align-items: center;
            gap: 16px;
        }}
        .nav-link {{
            font-size: 13px;
            color: var(--text-muted);
            text-decoration: none;
            padding: 6px 12px;
            border-radius: 6px;
            transition: all 0.2s;
        }}
        .nav-link:hover {{
            color: #fff;
            background: rgba(255, 255, 255, 0.05);
        }}

        /* Search Bar Area */
        .search-container {{
            background: var(--bg-surface);
            border-bottom: 1px solid var(--border);
            padding: 20px 28px;
        }}
        .search-form {{
            max-width: 1100px;
            margin: 0 auto;
            display: flex;
            gap: 10px;
        }}
        .search-input-wrapper {{
            flex: 1;
            position: relative;
        }}
        .search-input {{
            width: 100%;
            padding: 14px 18px;
            background: #090e17;
            border: 1px solid var(--border);
            border-radius: 10px;
            color: #fff;
            font-size: 14px;
            font-family: 'JetBrains Mono', monospace;
            transition: border-color 0.2s, box-shadow 0.2s;
        }}
        .search-input:focus {{
            outline: none;
            border-color: var(--accent);
            box-shadow: 0 0 0 3px rgba(56, 189, 248, 0.15);
        }}
        .search-btn {{
            padding: 14px 28px;
            background: linear-gradient(135deg, #2563eb, #1d4ed8);
            color: #fff;
            border: none;
            border-radius: 10px;
            font-weight: 600;
            font-size: 14px;
            cursor: pointer;
            transition: transform 0.15s, box-shadow 0.15s;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .search-btn:hover {{
            box-shadow: 0 6px 18px var(--primary-glow);
            transform: translateY(-1px);
        }}

        /* Filter Chips under search */
        .search-filter-pills {{
            max-width: 1100px;
            margin: 12px auto 0;
            display: flex;
            align-items: center;
            gap: 8px;
            flex-wrap: wrap;
            font-size: 12px;
            color: var(--text-dim);
        }}
        .filter-chip {{
            background: rgba(255, 255, 255, 0.04);
            border: 1px solid var(--border);
            color: var(--text-muted);
            padding: 3px 10px;
            border-radius: 6px;
            cursor: pointer;
            font-family: 'JetBrains Mono', monospace;
            text-decoration: none;
            transition: all 0.15s;
        }}
        .filter-chip:hover {{
            background: rgba(56, 189, 248, 0.1);
            color: var(--accent);
            border-color: var(--accent);
        }}

        /* Layout */
        .layout {{
            display: flex;
            max-width: 1440px;
            margin: 0 auto;
            min-height: calc(100vh - 165px);
        }}
        .sidebar {{
            width: 280px;
            background: #090e17;
            border-right: 1px solid var(--border);
            padding: 24px 18px;
            display: flex;
            flex-direction: column;
            gap: 6px;
        }}
        .sidebar-title {{
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: var(--text-dim);
            margin-bottom: 8px;
            padding: 0 8px;
        }}
        .nav-item {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 9px 12px;
            color: var(--text-muted);
            text-decoration: none;
            border-radius: 8px;
            font-size: 13px;
            font-weight: 500;
            transition: all 0.15s;
        }}
        .nav-item:hover {{
            background: var(--bg-card);
            color: #fff;
        }}
        .nav-item.active {{
            background: rgba(37, 99, 235, 0.15);
            color: var(--accent);
            border-left: 3px solid var(--accent);
        }}

        .main-content {{
            flex: 1;
            padding: 28px 36px;
            display: flex;
            flex-direction: column;
            gap: 24px;
        }}

        /* Welcome card */
        .welcome-card {{
            background: linear-gradient(180deg, var(--bg-surface), #080d15);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 36px;
        }}
        .welcome-badge {{
            display: inline-block;
            background: rgba(56, 189, 248, 0.1);
            color: var(--accent);
            font-size: 12px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            padding: 4px 12px;
            border-radius: 20px;
            margin-bottom: 12px;
        }}
        .welcome-header h2 {{
            font-size: 26px;
            font-weight: 800;
            letter-spacing: -0.02em;
            color: #fff;
            margin-bottom: 10px;
        }}
        .welcome-desc {{
            font-size: 14px;
            color: var(--text-muted);
            max-width: 780px;
            line-height: 1.6;
        }}

        .grid-features {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
            gap: 16px;
            margin: 28px 0;
        }}
        .feature-box {{
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 20px;
        }}
        .feature-icon {{
            font-size: 24px;
            margin-bottom: 10px;
        }}
        .feature-title {{
            font-weight: 700;
            font-size: 14px;
            color: #fff;
            margin-bottom: 6px;
        }}
        .feature-desc {{
            font-size: 12px;
            color: var(--text-muted);
            line-height: 1.5;
        }}

        .quick-query-section {{
            margin-top: 16px;
            padding-top: 20px;
            border-top: 1px solid var(--border);
            display: flex;
            flex-direction: column;
            gap: 10px;
        }}
        .quick-label {{
            font-size: 12px;
            font-weight: 600;
            color: var(--text-dim);
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}
        .pill-group {{
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
        }}
        .query-pill {{
            background: var(--bg-card);
            border: 1px solid var(--border);
            color: var(--text-main);
            text-decoration: none;
            padding: 6px 14px;
            border-radius: 8px;
            font-size: 13px;
            transition: all 0.15s;
        }}
        .query-pill:hover {{
            border-color: var(--accent);
            color: var(--accent);
            background: rgba(56, 189, 248, 0.08);
        }}

        /* Personnel Record Cards */
        .block {{
            background: var(--bg-surface);
            border: 1px solid var(--border);
            border-radius: 14px;
            padding: 24px;
        }}
        .block-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 18px;
            padding-bottom: 14px;
            border-bottom: 1px solid var(--border);
        }}
        .block-title {{
            font-size: 16px;
            font-weight: 700;
            color: #fff;
            display: flex;
            align-items: center;
            gap: 12px;
        }}
        .latency-chip {{
            font-size: 12px;
            color: var(--text-dim);
            font-family: 'JetBrains Mono', monospace;
        }}

        .personnel-list {{
            display: flex;
            flex-direction: column;
            gap: 16px;
        }}
        .personnel-card {{
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 20px;
            transition: border-color 0.2s, box-shadow 0.2s;
        }}
        .personnel-card:hover {{
            border-color: var(--border-hover);
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
        }}
        .personnel-card-header {{
            display: flex;
            align-items: center;
            gap: 14px;
            margin-bottom: 18px;
        }}
        .avatar {{
            width: 44px;
            height: 44px;
            border-radius: 10px;
            background: linear-gradient(135deg, #1e293b, #334155);
            border: 1px solid rgba(255, 255, 255, 0.1);
            color: #fff;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 800;
            font-size: 15px;
            letter-spacing: -0.02em;
        }}
        .personnel-meta {{
            flex: 1;
        }}
        .personnel-name-row {{
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 2px;
        }}
        .personnel-name {{
            font-size: 16px;
            font-weight: 700;
            color: #fff;
        }}
        .personnel-sub {{
            font-size: 12px;
            color: var(--text-muted);
        }}
        .badge-circle {{
            background: rgba(16, 185, 129, 0.12);
            color: var(--success);
            border: 1px solid rgba(16, 185, 129, 0.25);
            font-size: 11px;
            font-weight: 600;
            padding: 2px 8px;
            border-radius: 20px;
        }}
        .record-seq {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 12px;
            color: var(--text-dim);
            background: rgba(255, 255, 255, 0.03);
            padding: 3px 8px;
            border-radius: 6px;
        }}

        /* Details Grid inside Card */
        .details-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 12px;
            background: rgba(0, 0, 0, 0.2);
            border: 1px solid rgba(255, 255, 255, 0.03);
            border-radius: 10px;
            padding: 14px;
        }}
        .detail-item {{
            display: flex;
            flex-direction: column;
            gap: 4px;
        }}
        .detail-item.full-width {{
            grid-column: 1 / -1;
        }}
        .detail-label {{
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--text-dim);
        }}
        .detail-value {{
            font-size: 13px;
            color: var(--text-main);
            font-weight: 500;
        }}
        .id-highlight {{
            font-family: 'JetBrains Mono', monospace;
            color: #f59e0b;
        }}
        .address-val {{
            color: #cbd5e1;
            line-height: 1.4;
        }}

        .copyable {{
            cursor: pointer;
            display: inline-block;
            transition: color 0.15s;
        }}
        .copyable:hover {{
            color: var(--accent);
            text-decoration: underline;
        }}

        /* Badges */
        .badge {{
            padding: 3px 9px;
            border-radius: 20px;
            font-size: 11px;
            font-weight: 700;
            font-family: 'JetBrains Mono', monospace;
        }}
        .badge-success {{
            background: rgba(16, 185, 129, 0.15);
            color: var(--success);
        }}
        .badge-muted {{
            background: rgba(100, 116, 139, 0.2);
            color: #94a3b8;
        }}
        .badge-danger {{
            background: rgba(239, 68, 68, 0.15);
            color: var(--danger);
        }}

        /* Toast notification */
        #toast {{
            position: fixed;
            bottom: 24px;
            right: 24px;
            background: #1e293b;
            border: 1px solid var(--accent);
            color: #fff;
            padding: 10px 18px;
            border-radius: 8px;
            font-size: 13px;
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.5);
            display: none;
            z-index: 1000;
        }}
    </style>
</head>
<body id="top">
    <!-- Navbar -->
    <header class="top-nav">
        <a href="/" class="brand">
            <div class="brand-logo">N</div>
            <div class="brand-text">
                <h1>Nexus Personnel Intelligence</h1>
                <span>Enterprise Identity Registry</span>
            </div>
        </a>
        <div class="nav-links">
            <span style="font-size: 12px; color: var(--text-dim); display: flex; align-items: center; gap: 6px;">
                <span style="width: 8px; height: 8px; border-radius: 50%; background: #10b981; display: inline-block;"></span>
                HuggingFace Engine Active
            </span>
            <a href="/docs" target="_blank" class="nav-link">API Swagger</a>
            <a href="/health" target="_blank" class="nav-link">System Health</a>
        </div>
    </header>

    <!-- Search Section -->
    <section class="search-container">
        <form class="search-form" method="GET" action="/">
            <div class="search-input-wrapper">
                <input type="text" name="q" class="search-input" value="{escaped_query}" placeholder="Verify by Phone, National ID, Full Name, or Address (e.g. 9810014045, name:rahul, address:delhi)..." autofocus>
            </div>
            <button type="submit" class="search-btn">
                <span>🔍 Verify Record</span>
            </button>
        </form>
        <div class="search-filter-pills">
            <span>Filter Shortcuts:</span>
            <span class="filter-chip" onclick="setQueryPrefix('mobile:')">mobile:</span>
            <span class="filter-chip" onclick="setQueryPrefix('id:')">id: (Aadhaar/KYC)</span>
            <span class="filter-chip" onclick="setQueryPrefix('name:')">name:</span>
            <span class="filter-chip" onclick="setQueryPrefix('address:')">address:</span>
            <span class="filter-chip" onclick="setQueryPrefix('circle:')">circle:</span>
            <span class="filter-chip" onclick="setQueryPrefix('oid:')">oid: (LinkedIn)</span>
            {latency_chip}
        </div>
    </section>

    <!-- Layout -->
    <div class="layout">
        <aside class="sidebar">
            <div class="sidebar-title">Dossier Index</div>
            {nav_rendered}
        </aside>
        <main class="main-content">
            {content_rendered}
        </main>
    </div>

    <!-- Toast -->
    <div id="toast">Copied to clipboard</div>

    <script>
        function copyText(val) {{
            if (!val || val === 'N/A' || val === 'None') return;
            navigator.clipboard.writeText(val);
            const toast = document.getElementById('toast');
            toast.innerText = 'Copied: ' + val;
            toast.style.display = 'block';
            setTimeout(() => {{ toast.style.display = 'none'; }}, 2200);
        }}

        function setQueryPrefix(prefix) {{
            const input = document.querySelector('.search-input');
            input.value = prefix + input.value.replace(/^[a-z]+:/i, '');
            input.focus();
        }}
    </script>
</body>
</html>
"""
