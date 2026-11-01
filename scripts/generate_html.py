#!/usr/bin/env python3
"""Render a standalone dated HTML archive from a saved JSON edition."""
import argparse, html, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser(); p.add_argument("date",help="Edition date, YYYY-MM-DD"); a=p.parse_args()
    source=ROOT/f"data/news/{a.date}.json"; data=json.loads(source.read_text()); cards=[]
    for n in data.get("news",[]): cards.append(f'<article><small>{html.escape(n.get("category",""))} · {html.escape(n.get("source",""))} · {html.escape(n.get("published_at",""))}</small><h2>{html.escape(n.get("title_zh",""))}</h2><p>{html.escape(n.get("summary_zh",""))}</p><a href="{html.escape(n.get("url",""),quote=True)}">阅读原文 ↗</a></article>')
    out=ROOT/f"data/archive/{a.date}.html"; out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Global AI Daily '+html.escape(a.date)+'</title><style>body{background:#0b0d16;color:#eee;font:16px system-ui;max-width:900px;margin:4rem auto;padding:1rem}article{background:#151a27;border:1px solid #30364a;border-radius:12px;padding:1.5rem;margin:1rem 0;line-height:1.8}small{color:#b6a5ee}a{color:#b6a5ee}</style><h1>GLOBAL AI DAILY · '+html.escape(a.date)+'</h1><p>'+html.escape(data.get("summary",""))+'</p>'+''.join(cards)+'</html>\n')
    print(out)
if __name__=="__main__": main()
