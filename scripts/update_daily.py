#!/usr/bin/env python3
"""Fetch public AI RSS feeds, create a dated JSON edition, and refresh latest.json."""
from __future__ import annotations
import argparse, datetime as dt, email.utils, hashlib, html, json, os, re, sys, urllib.request, xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
UTC = dt.timezone.utc

def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "Global-AI-Daily/1.0 (local RSS reader)"})
    with urllib.request.urlopen(request, timeout=20) as response:
        return response.read(5_000_000)

def text(node, *paths):
    for path in paths:
        found = node.find(path)
        if found is not None and found.text:
            return html.unescape(re.sub(r"<[^>]+>", " ", found.text)).strip()
    return ""

def parse_date(value):
    if not value: return None
    try:
        value = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        try: value = email.utils.parsedate_to_datetime(value)
        except (TypeError, ValueError): return None
    if value.tzinfo is None: value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC)

def entries(feed):
    root = ET.fromstring(fetch(feed["url"]))
    found=[]
    for item in root.findall(".//item"):
        title=text(item,"title"); link=text(item,"link"); published=parse_date(text(item,"pubDate","{http://purl.org/dc/elements/1.1/}date")); desc=text(item,"description")
        if title and link and published: found.append((title,link,published,desc))
    ns={"a":"http://www.w3.org/2005/Atom"}
    for item in root.findall(".//a:entry",ns):
        title=text(item,"{http://www.w3.org/2005/Atom}title"); published=parse_date(text(item,"{http://www.w3.org/2005/Atom}published","{http://www.w3.org/2005/Atom}updated")); desc=text(item,"{http://www.w3.org/2005/Atom}summary","{http://www.w3.org/2005/Atom}content")
        link_node=item.find("a:link",ns); link=link_node.get("href","") if link_node is not None else ""
        if title and link and published: found.append((title,link,published,desc))
    return found

def translate(title, description):
    """Optional OpenAI-compatible translation. Without API config, preserve source text honestly."""
    endpoint=os.getenv("AI_API_BASE_URL", "https://api.openai.com/v1/chat/completions")
    key=os.getenv("AI_API_KEY")
    if not key: return title, "摘要待生成：当前未配置 AI_API_KEY，请阅读原文。"
    model=os.getenv("AI_MODEL", "gpt-4o-mini")
    payload={"model":model,"temperature":0.2,"messages":[{"role":"system","content":"将 AI 新闻翻译并总结为简体中文。仅返回 JSON：{title_zh,summary_zh,highlights(3条),impact,keywords(3-5个)}。忠实原文，不补充未给出的事实。summary_zh 为150-300个汉字。"},{"role":"user","content":f"标题：{title}\n正文：{description[:6000]}"}],"response_format":{"type":"json_object"}}
    req=urllib.request.Request(endpoint,data=json.dumps(payload).encode(),headers={"Authorization":f"Bearer {key}","Content-Type":"application/json"})
    with urllib.request.urlopen(req,timeout=60) as r: result=json.loads(r.read())
    content=json.loads(result["choices"][0]["message"]["content"])
    return content.get("title_zh",title),content

def main():
    parser=argparse.ArgumentParser(); parser.add_argument("--hours",type=int); parser.add_argument("--demo",action="store_true",help="Use the bundled verified example edition"); args=parser.parse_args()
    if args.demo:
        demo=ROOT/"data/news/2025-08-07.json"; data=json.loads(demo.read_text()); write(data); print(f"Loaded verified demo: {demo}"); return
    config=json.loads((ROOT/"config/sources.json").read_text()); now=dt.datetime.now(UTC); hours=args.hours or config["lookback_hours"]; collected=[]
    for feed in config["feeds"]:
        try:
            for title,url,published,desc in entries(feed):
                if now-dt.timedelta(hours=hours) <= published <= now+dt.timedelta(minutes=10): collected.append((feed,title,url,published,desc))
        except Exception as exc: print(f"WARN {feed['name']}: {exc}",file=sys.stderr)
    if not collected and hours < config["fallback_hours"]:
        hours=config["fallback_hours"]
        print(f"No items in 24h; extending to {hours}h.")
        for feed in config["feeds"]:
            try:
                for title,url,published,desc in entries(feed):
                    if now-dt.timedelta(hours=hours) <= published <= now+dt.timedelta(minutes=10): collected.append((feed,title,url,published,desc))
            except Exception as exc: print(f"WARN {feed['name']}: {exc}",file=sys.stderr)
    if not collected:
        print(f"No RSS items found in the {hours}h window; keeping the current latest edition unchanged.")
        return
    collected.sort(key=lambda x:x[3],reverse=True); seen=set(); news=[]
    for feed,title,url,published,desc in collected:
        key=urlparse(url).netloc+urlparse(url).path.rstrip("/").lower()
        if key in seen: continue
        seen.add(key); title_zh,generated=translate(title,desc)
        if isinstance(generated,str): summary=generated; highlights=[]; impact=""; keywords=[]
        else: summary=generated.get("summary_zh",""); highlights=generated.get("highlights",[]); impact=generated.get("impact",""); keywords=generated.get("keywords",[])
        digest=hashlib.sha1(url.encode()).hexdigest()[:12]
        news.append({"id":digest,"title_zh":title_zh,"title_original":title,"published_at":published.isoformat(),"source":feed["name"],"url":url,"category":feed["default_category"],"importance":feed["importance"],"status":"来源 RSS 发布","summary_zh":summary,"highlights":highlights,"impact":impact,"keywords":keywords})
        if len(news)>=config["max_items"]: break
    # Merge today's new items into the existing edition, preserving previously collected stories.
    day=now.date().isoformat(); archive=ROOT/f"data/news/{day}.json"
    old=json.loads(archive.read_text()).get("news",[]) if archive.exists() else []
    ids={n["id"] for n in news}; news.extend(n for n in old if n.get("id") not in ids)
    edition={"date":day,"generated_at":now.isoformat(),"edition_type":"rss","summary":f"采集 {len(news)} 条资讯；窗口 {hours} 小时。","news":news}
    write(edition)
    print(f"Saved {len(news)} stories to {archive}")

def write(data):
    day=data["date"]; archive=ROOT/f"data/news/{day}.json"; archive.parent.mkdir(parents=True,exist_ok=True)
    archive.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n")
    (ROOT/"data/latest.json").write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n")
    (ROOT/"data/archive").mkdir(parents=True,exist_ok=True)
    editions=sorted(p.stem for p in (ROOT/"data/news").glob("????-??-??.json"))
    (ROOT/"data/editions.json").write_text(json.dumps(editions,ensure_ascii=False,indent=2)+"\n")
    (ROOT/f"data/archive/{day}.html").write_text(f'<!doctype html><meta charset="utf-8"><title>Global AI Daily {day}</title><h1>Global AI Daily · {day}</h1><p>{html.escape(data.get("summary", ""))}</p><ol>'+''.join(f'<li><h2>{html.escape(n.get("title_zh", ""))}</h2><p>{html.escape(n.get("summary_zh", ""))}</p><a href="{html.escape(n.get("url", ""), quote=True)}">{html.escape(n.get("source", "原文"))}</a></li>' for n in data.get("news",[]))+'</ol>\n')

if __name__=="__main__": main()
