"""
dashboard.py — High-Performance OSINT Dossier Web Dashboard for Multi-Billion Record Engine.
"""

import html
import re
from typing import List, Dict, Any


def clean_address_text(addr: str | None) -> str:
    """Format delimited address strings into readable text."""
    if not addr:
        return "N/A"
    cleaned = re.sub(r"[!]+", ", ", addr)
    cleaned = re.sub(r"\s*,\s*", ", ", cleaned).strip(" ,")
    return html.escape(cleaned)


def _query_icon(query: str) -> str:
    q = query.strip()
    if ":" in q:
        prefix = q.split(":", 1)[0].strip().lower()
        return {
            "mobile": "📱", "id": "🆔", "name": "👤",
            "fname": "👨", "address": "🏠", "circle": "🗺️",
            "email": "✉️", "alt": "📞",
        }.get(prefix, "🔍")
    digits = re.sub(r"[\s\-+]", "", q)
    if digits.isdigit() and len(digits) >= 8:
        return "📱"
    return "👤"


def _render_oid(oid: str) -> str:
    """Render the Other ID field, avoiding backslash in f-string."""
    if oid == "N/A":
        return ""
    dq = '"'
    return (
        f"<div><b>🔗 Other ID:</b> "
        f"<span class='copyable' onclick='navigator.clipboard.writeText({dq}{oid}{dq})'>"
        f"{oid} 📋</span></div>"
    )


def render_dashboard_html(
    query: str,
    search_data_list: List[Dict[str, Any]],
    limit: int = 10,
    search_time_ms: float = 0.0,
) -> str:
    escaped_query = html.escape(query)

    nav_links = []
    blocks_html = []
    total_found = sum(item.get("count", 0) for item in search_data_list)

    if not search_data_list and not query:
        content_rendered = """
        <div class='block' style='flex: 1 1 100%;'>
            <div class='block-title'><b>⚡ Data Intelligence Portal — Unified Multi-Billion Search</b></div>
            <div class='block-text'>
                <p>Welcome to the unified OSINT search system. Search through <b>3.77+ billion records</b> by Phone, Aadhaar/ID, Name, or Address.</p>
                <p><b>✨ Key Capabilities:</b></p>
                <ul>
                    <li><b>Phone Search:</b> 10-digit mobile number with instant partition pruning.</li>
                    <li><b>ID Search:</b> Aadhaar number, Government ID, or LinkedIn handle.</li>
                    <li><b>Name Search:</b> Free-text search matching full name and father's name / title.</li>
                    <li><b>Prefix Search:</b> <code>name:rahul</code> &nbsp; <code>address:delhi</code> &nbsp; <code>circle:airtel</code> &nbsp; <code>oid:linkedin</code>.</li>
                    <li><b>Batch Queries:</b> Comma-separated or multi-line queries processed concurrently.</li>
                </ul>
                <div style="margin-top: 15px; padding: 12px; background: #0f172a; border-radius: 8px; border-left: 4px solid #3b82f6;">
                    <b>💡 Quick Examples:</b><br>
                    <a href='/?q=9810014045' style='color:#60a5fa;text-decoration:none;'>&bull; 📱 <code>9810014045</code></a> &nbsp;&nbsp;
                    <a href='/?q=rahul%20sharma' style='color:#60a5fa;text-decoration:none;'>&bull; 👤 <code>rahul sharma</code></a> &nbsp;&nbsp;
                    <a href='/?q=address:mumbai' style='color:#60a5fa;text-decoration:none;'>&bull; 🏠 <code>address:mumbai</code></a>
                </div>
            </div>
        </div>
        """
        nav_rendered = """
        <a href='/'><b>🏠 Home</b></a>
        <a href='/docs' target='_blank'><b>📡 API Swagger (/docs)</b></a>
        <a href='/gradio' target='_blank'><b>🎛️ Gradio UI (/gradio)</b></a>
        """
    else:
        nav_links.append("<a href='#top'><b>🔝 Back to Top</b></a>")

        for item in search_data_list:
            sub_q = item.get("query", "")
            results = item.get("results", [])
            count = item.get("count", 0)
            target_id = f"target-{re.sub(r'[^a-zA-Z0-9]', '', sub_q)}"
            icon = _query_icon(sub_q)
            nav_badge_color = "#3b82f6" if count > 0 else "#64748b"

            nav_links.append(
                f"<a href='#{target_id}'>{icon} {html.escape(sub_q)} "
                f"<span class='badge' style='background:{nav_badge_color}; color:#fff;'>{count}</span></a>"
            )

            if not results:
                blocks_html.append(f"""
                <div class='block' id='{target_id}' style='flex: 1 1 100%; border-left: 4px solid #ef4444;'>
                    <div class='block-title'>{icon} <b>Query:</b> {html.escape(sub_q)}</div>
                    <div class='block-text' style='color: #94a3b8;'>
                        <p>❌ No matching records found in the database.</p>
                    </div>
                </div>
                """)
                continue

            records_markup = []
            for idx, r in enumerate(results, 1):
                clean_addr = clean_address_text(r.get("address"))
                mob = html.escape(str(r.get("mobile") or "N/A"))
                alt = html.escape(str(r.get("alt") or "N/A"))
                name = html.escape(str(r.get("name") or "N/A"))
                fname = html.escape(str(r.get("fname") or "N/A"))
                circle = html.escape(str(r.get("circle") or "N/A"))
                uid = html.escape(str(r.get("id") or "N/A"))
                email = html.escape(str(r.get("email") or "N/A"))
                oid = html.escape(str(r.get("oid") or "N/A"))

                records_markup.append(f"""
                <div class='record-card'>
                    <div class='record-header'>
                        <span class='record-idx'>#{idx}</span>
                        <span class='record-name'>{name}</span>
                        <span class='record-circle'>{circle}</span>
                    </div>
                    <div class='record-grid'>
                        <div><b>📱 Primary Phone:</b> <span class='copyable' onclick='navigator.clipboard.writeText("{mob}")'>{mob} 📋</span></div>
                        <div><b>📞 Alternate:</b> <span class='copyable' onclick='navigator.clipboard.writeText("{alt}")'>{alt} 📋</span></div>
                        <div><b>👨 Father / Title:</b> {fname}</div>
                        <div><b>🆔 Identifier / ID:</b> <span class='copyable' onclick='navigator.clipboard.writeText("{uid}")'>{uid} 📋</span></div>
                        <div style='grid-column: 1 / -1;'><b>🏠 Address:</b> {clean_addr}</div>
                        {f"<div><b>✉️ Email:</b> {email}</div>" if email != "N/A" and email != "NULLLLL" else ""}
                        {_render_oid(oid)}
                    </div>
                </div>
                """)

            blocks_html.append(f"""
            <div class='block' id='{target_id}' style='flex: 1 1 100%;'>
                <div class='block-title' style='display:flex; justify-content:space-between; align-items:center;'>
                    <span>{icon} <b>Query:</b> {html.escape(sub_q)} ({count} records)</span>
                </div>
                <div class='records-container'>
                    {''.join(records_markup)}
                </div>
            </div>
            """)

        content_rendered = "\n".join(blocks_html)
        nav_rendered = "\n".join(nav_links)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Data Intelligence Portal — OSINT Dossier</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: #090d16;
            color: #e2e8f0;
            line-height: 1.5;
        }}
        .header {{
            background: #0f172a;
            border-bottom: 1px solid #1e293b;
            padding: 16px 24px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 12px;
        }}
        .header h1 {{ font-size: 1.3rem; font-weight: 700; color: #f8fafc; display: flex; align-items: center; gap: 8px; }}
        .search-bar {{
            background: #0f172a;
            border-bottom: 1px solid #1e293b;
            padding: 16px 24px;
            display: flex;
            gap: 12px;
        }}
        .search-bar input {{
            flex: 1;
            padding: 12px 16px;
            background: #1e293b;
            border: 1px solid #334155;
            border-radius: 8px;
            color: #fff;
            font-size: 15px;
            font-family: monospace;
        }}
        .search-bar input:focus {{ outline: none; border-color: #3b82f6; }}
        .search-bar button {{
            padding: 12px 24px;
            background: #3b82f6;
            color: #fff;
            border: none;
            border-radius: 8px;
            font-weight: 600;
            cursor: pointer;
            transition: 0.2s;
        }}
        .search-bar button:hover {{ background: #2563eb; }}
        .layout {{ display: flex; min-height: calc(100vh - 140px); }}
        .sidebar {{
            width: 260px;
            background: #0b1120;
            border-right: 1px solid #1e293b;
            padding: 16px;
            display: flex;
            flex-direction: column;
            gap: 8px;
        }}
        .sidebar a {{
            color: #94a3b8;
            text-decoration: none;
            padding: 8px 12px;
            border-radius: 6px;
            font-size: 13px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            transition: 0.15s;
        }}
        .sidebar a:hover {{ background: #1e293b; color: #fff; }}
        .badge {{ padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: 600; }}
        .content {{ flex: 1; padding: 24px; display: flex; flex-direction: column; gap: 20px; }}
        .block {{
            background: #0f172a;
            border: 1px solid #1e293b;
            border-radius: 12px;
            padding: 20px;
        }}
        .block-title {{ font-size: 16px; font-weight: 700; color: #f8fafc; margin-bottom: 12px; }}
        .record-card {{
            background: #1e293b;
            border: 1px solid #334155;
            border-radius: 10px;
            padding: 16px;
            margin-bottom: 12px;
        }}
        .record-header {{ display: flex; align-items: center; gap: 10px; margin-bottom: 12px; }}
        .record-idx {{ background: #3b82f6; color: #fff; padding: 2px 8px; border-radius: 6px; font-size: 11px; font-weight: 700; }}
        .record-name {{ font-weight: 700; font-size: 16px; color: #f8fafc; }}
        .record-circle {{ margin-left: auto; background: rgba(16, 185, 129, 0.15); color: #34d399; padding: 2px 8px; border-radius: 6px; font-size: 12px; font-weight: 600; }}
        .record-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 10px; font-size: 13px; }}
        .copyable {{ cursor: pointer; color: #60a5fa; font-family: monospace; background: rgba(59, 130, 246, 0.1); padding: 2px 6px; border-radius: 4px; }}
        .copyable:hover {{ background: rgba(59, 130, 246, 0.25); text-decoration: underline; }}
    </style>
</head>
<body id="top">
    <div class="header">
        <h1>⚡ Data Intelligence Portal</h1>
        <div style="font-size: 13px; color: #94a3b8;">
            <b>Status:</b> 3.77B Index Active &bull; <a href="/docs" target="_blank" style="color:#60a5fa;">API Swagger</a> &bull; <a href="/gradio" target="_blank" style="color:#60a5fa;">Gradio UI</a>
        </div>
    </div>
    <form class="search-bar" method="GET" action="/">
        <input type="text" name="q" value="{escaped_query}" placeholder="Search Phone, Aadhaar, Name (e.g. 981..., name:rahul, address:delhi)..." autofocus>
        <button type="submit">Search Records</button>
    </form>
    <div class="layout">
        <div class="sidebar">
            <div style="font-size: 11px; font-weight: 700; color: #64748b; text-transform: uppercase; margin-bottom: 4px;">Navigation</div>
            {nav_rendered}
        </div>
        <div class="content">
            {content_rendered}
        </div>
    </div>
</body>
</html>
"""
