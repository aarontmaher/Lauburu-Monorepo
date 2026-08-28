#!/usr/bin/env python3
"""
Obsidian Vault Survey & Analysis Script for Lauburu Monorepo
"""
import os
import glob
import re
import yaml
import json
from collections import defaultdict, Counter

VAULT_PATH = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/obsidian_vault"

def analyze_vault():
    md_files = glob.glob(os.path.join(VAULT_PATH, "**/*.md"), recursive=True)
    print(f"Total markdown files found: {len(md_files)}")
    
    # Path mappings
    all_stems = {}
    all_bases = {}
    case_insensitive_map = {}
    
    for f in md_files:
        rel = os.path.relpath(f, VAULT_PATH)
        stem = os.path.splitext(rel)[0]
        base = os.path.splitext(os.path.basename(f))[0]
        all_stems[stem] = rel
        all_bases[base] = rel
        case_insensitive_map[stem.lower()] = rel
        case_insensitive_map[base.lower()] = rel
        
    code_block_pattern = re.compile(r'```.*?```', re.DOTALL)
    wikilink_pattern = re.compile(r'\[\[(.*?)\]\]')
    frontmatter_pattern = re.compile(r'^---\s*\n(.*?)\n---\s*\n', re.DOTALL)
    
    parsed_vault = {}
    edge_list = []
    dangling_by_file = defaultdict(list)
    link_types = Counter()
    
    for f in sorted(md_files):
        rel = os.path.relpath(f, VAULT_PATH)
        stem = os.path.splitext(rel)[0]
        base = os.path.splitext(os.path.basename(f))[0]
        
        with open(f, "r", encoding="utf-8", errors="replace") as fp:
            raw_text = fp.read()
            
        # Frontmatter
        fm_match = frontmatter_pattern.match(raw_text)
        fm = {}
        body = raw_text
        has_fm = False
        fm_error = None
        if fm_match:
            has_fm = True
            try:
                parsed_yaml = yaml.safe_load(fm_match.group(1))
                if isinstance(parsed_yaml, dict):
                    fm = parsed_yaml
                else:
                    fm_error = f"Frontmatter is not dict: {type(parsed_yaml)}"
            except Exception as e:
                fm_error = str(e)
            body = raw_text[fm_match.end():]
            
        # Headers
        h1s = re.findall(r'^#\s+(.+)$', body, re.MULTILINE)
        h2s = re.findall(r'^##\s+(.+)$', body, re.MULTILINE)
        h3s = re.findall(r'^###\s+(.+)$', body, re.MULTILINE)
        title = fm.get("title") or (h1s[0] if h1s else base)
        
        # Tags
        tags = fm.get("tags", [])
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",") if t.strip()]
        elif isinstance(tags, list):
            tags = [str(t).strip() for t in tags if str(t).strip()]
        else:
            tags = []
            
        # Find all wikilinks
        file_links = []
        for match in wikilink_pattern.finditer(raw_text):
            raw_link = match.group(1).strip()
            
            alias = None
            target = raw_link
            heading = None
            block_id = None
            
            if "|" in raw_link:
                parts = raw_link.split("|", 1)
                target = parts[0].strip()
                alias = parts[1].strip()
                link_types["with_alias"] += 1
            else:
                link_types["simple"] += 1
                
            if "#" in target:
                t_parts = target.split("#", 1)
                target = t_parts[0].strip()
                anchor = t_parts[1].strip()
                if anchor.startswith("^"):
                    block_id = anchor[1:]
                    link_types["block_anchor"] += 1
                else:
                    heading = anchor
                    link_types["heading_anchor"] += 1
                    
            resolved = None
            clean_target = target.strip()
            if clean_target.endswith(".md"):
                clean_target = clean_target[:-3]
                link_types["has_md_extension"] += 1
                
            if not clean_target:
                resolved = stem
                link_types["anchor_only"] += 1
            elif clean_target in all_bases:
                resolved = os.path.splitext(all_bases[clean_target])[0]
            elif clean_target in all_stems:
                resolved = clean_target
            elif clean_target.lower() in case_insensitive_map:
                resolved = os.path.splitext(case_insensitive_map[clean_target.lower()])[0]
                link_types["case_insensitive_match"] += 1
            else:
                dangling_by_file[stem].append(raw_link)
                link_types["dangling"] += 1
                
            link_obj = {
                "raw": raw_link,
                "target": target,
                "clean_target": clean_target,
                "resolved": resolved,
                "alias": alias,
                "heading": heading,
                "block_id": block_id,
                "is_resolved": resolved is not None
            }
            file_links.append(link_obj)
            if resolved:
                edge_list.append((stem, resolved, raw_link, alias))
                
        # Features extraction
        features = []
        for sec_match in re.finditer(r'##\s+([^\n]+)\n(.*?)(?=\n##|\Z)', body, re.DOTALL):
            sec_title = sec_match.group(1).strip()
            sec_body = sec_match.group(2)
            if any(k in sec_title.lower() for k in ["feature", "module", "algorithm", "component", "endpoint", "protocol", "architecture", "scope", "services", "subsystem"]):
                for line in sec_body.splitlines():
                    line = line.strip()
                    m = re.match(r'^(?:\d+\.|\-|\*)\s+\*?\*?([^\*\:\n]+)\*?\*?(?:\:\s*(.*))?$', line)
                    if m:
                        name = m.group(1).strip()
                        desc = m.group(2).strip() if m.group(2) else ""
                        if len(name) > 2 and not name.startswith("[["):
                            features.append({"name": name, "description": desc, "section": sec_title})
                            
        # Specialist agent
        specialist_agent = None
        agent_match = re.search(r'Specialist Agent:\*?\*?\s*`?([a-zA-Z0-9_\-]+)`?', body)
        if agent_match:
            specialist_agent = agent_match.group(1)
            
        # Category deduction
        cat = fm.get("category", fm.get("type", None))
        if not cat:
            if re.match(r'^(0[0-9]|1[0-2])_', base):
                cat = "Canonical Module"
            elif "00_overview" in rel.lower():
                cat = "Overview"
            elif "debate" in base.lower() or "consensus" in base.lower() or "deliberation" in base.lower():
                cat = "AI Debate & Consensus"
            elif "spec" in base.lower():
                cat = "Specification"
            elif "audit" in base.lower() or "ledger" in base.lower() or "triage" in base.lower() or "crawl" in base.lower():
                cat = "Audit & Verification"
            elif "mesh" in base.lower() or "network" in base.lower() or "topology" in base.lower() or "accelerator" in base.lower() or "governor" in base.lower() or "sync" in base.lower() or "gateway" in base.lower():
                cat = "Infrastructure & Mesh"
            elif "app" in base.lower():
                cat = "Applications"
            elif base == "Index":
                cat = "Root Index"
            else:
                cat = "Documentation"
                
        parsed_vault[stem] = {
            "stem": stem,
            "rel_path": rel,
            "base_name": base,
            "title": title,
            "has_frontmatter": has_fm,
            "frontmatter_error": fm_error,
            "frontmatter": fm,
            "tags": tags,
            "category": cat,
            "h1": h1s,
            "h2": h2s,
            "h3": h3s,
            "specialist_agent": specialist_agent,
            "features": features,
            "features_count": len(features),
            "links": file_links,
            "outgoing_resolved": [l["resolved"] for l in file_links if l["resolved"]],
            "outgoing_count": len([l for l in file_links if l["resolved"]]),
            "total_links_count": len(file_links),
            "dangling_count": len([l for l in file_links if not l["resolved"]]),
            "size_bytes": len(raw_text.encode("utf-8")),
            "line_count": len(raw_text.splitlines())
        }
        
    # Inbound edges
    inbound_edges = defaultdict(list)
    for src, dst, raw, alias in edge_list:
        inbound_edges[dst].append(src)
        
    for stem, node in parsed_vault.items():
        node["incoming_resolved"] = inbound_edges[stem]
        node["incoming_count"] = len(inbound_edges[stem])
        
    print("\n========================================================")
    print("                OBSIDIAN VAULT SURVEY REPORT             ")
    print("========================================================")
    print(f"Total Markdown Files: {len(parsed_vault)}")
    print(f"Total Wikilink references: {sum(n['total_links_count'] for n in parsed_vault.values())}")
    print(f"Total Resolved Edges: {len(edge_list)}")
    print(f"Total Dangling References: {sum(len(v) for v in dangling_by_file.values())}")
    print(f"Wikilink Types: {json.dumps(dict(link_types), indent=2)}")
    
    # Categories
    categories = Counter(n["category"] for n in parsed_vault.values())
    print(f"\nCategory Distribution:\n{json.dumps(dict(categories), indent=2)}")
    
    # Top tags
    tag_counter = Counter()
    for n in parsed_vault.values():
        for t in n["tags"]:
            tag_counter[t] += 1
    print(f"\nTop 15 Tags:\n{json.dumps(tag_counter.most_common(15), indent=2)}")
    
    # Top connected nodes
    print("\nTop 10 Nodes by Outgoing Links:")
    top_out = sorted(parsed_vault.values(), key=lambda x: x["outgoing_count"], reverse=True)[:10]
    for n in top_out:
        print(f"  - {n['stem']}: {n['outgoing_count']} outgoing edges (category: {n['category']})")
        
    print("\nTop 10 Nodes by Incoming Links (Most Referenced):")
    top_in = sorted(parsed_vault.values(), key=lambda x: x["incoming_count"], reverse=True)[:10]
    for n in top_in:
        print(f"  - {n['stem']}: {n['incoming_count']} incoming references (category: {n['category']})")
        
    # Frontmatter statistics
    fm_present = [n for n in parsed_vault.values() if n["has_frontmatter"]]
    fm_missing = [n for n in parsed_vault.values() if not n["has_frontmatter"]]
    print(f"\nFrontmatter Coverage: {len(fm_present)}/{len(parsed_vault)} ({len(fm_present)/len(parsed_vault)*100:.1f}%)")
    if fm_missing:
        print(f"Files missing frontmatter: {[n['stem'] for n in fm_missing]}")
        
    # Canonical 13 Modules
    print("\nCanonical 13 Modules (00-12):")
    for i in range(13):
        prefix = f"{i:02d}_"
        match = [n for n in parsed_vault.values() if n["base_name"].startswith(prefix)]
        if match:
            m = match[0]
            print(f"  {m['base_name']}:")
            print(f"    Title: {m['title']}")
            print(f"    Specialist: {m['specialist_agent']}")
            print(f"    Tags: {m['tags']}")
            print(f"    Features count: {m['features_count']}")
            print(f"    Out edges: {m['outgoing_resolved']}")
            print(f"    In edges: {m['incoming_resolved']}")
            
    # Dangling links details
    print(f"\nDangling Links breakdown ({len(dangling_by_file)} files with dangling links):")
    for fstem, d_links in sorted(dangling_by_file.items()):
        print(f"  File '{fstem}' ({len(d_links)} dangling links):")
        for dl in d_links[:5]:
            print(f"    - [[{dl}]]")
        if len(d_links) > 5:
            print(f"    ... and {len(d_links)-5} more")

    # Save detailed JSON output for handoff and inspection
    out_json_path = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/.agents/teamwork_preview_explorer_survey_1/vault_survey_data.json"
    with open(out_json_path, "w", encoding="utf-8") as out_fp:
        json.dump({
            "nodes": parsed_vault,
            "edges": edge_list,
            "categories": dict(categories),
            "tag_counts": dict(tag_counter),
            "dangling_links": dict(dangling_by_file),
            "link_types": dict(link_types),
            "summary": {
                "total_nodes": len(parsed_vault),
                "total_edges": len(edge_list),
                "total_wikilinks": sum(n['total_links_count'] for n in parsed_vault.values()),
                "total_dangling": sum(len(v) for v in dangling_by_file.values()),
                "frontmatter_coverage_pct": len(fm_present)/len(parsed_vault)*100
            }
        }, out_fp, indent=2, default=str)
    print(f"\nSurvey data successfully written to {out_json_path}")

if __name__ == "__main__":
    analyze_vault()
