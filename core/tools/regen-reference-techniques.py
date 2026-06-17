import json
MEDIA = {"Instructional video", "Live video", "Notes"}

def flatten_techniques(node):
    children = node.get("c", []) if isinstance(node, dict) else []
    out = []
    for c in children:
        if not isinstance(c, dict): continue
        name = c.get("t", "").strip()
        if not name or name in MEDIA: continue
        sub = c.get("c", [])
        non_media = [x for x in sub if isinstance(x, dict) and x.get("t","") not in MEDIA]
        if not non_media:
            out.append(name)
        else:
            out.extend(flatten_techniques(c))
    return out

def extract_position(pos_node):
    pname = pos_node.get("t", "")
    result = {}
    children = pos_node.get("c", [])
    for persp in children:
        if not isinstance(persp, dict): continue
        pspname = persp.get("t", "")
        headings = persp.get("c", [])
        hmap = {}
        for h in headings:
            if not isinstance(h, dict): continue
            hname = h.get("t", "")
            techs = flatten_techniques(h)
            if techs:
                hmap[hname] = techs
        if hmap:
            result[pspname] = hmap
    return pname, result

d = json.load(open("/tmp/refseed/sections.json"))
out = {}
for section in d:
    for pos_node in section.get("nodes", []):
        pname = pos_node.get("t", "")
        children = pos_node.get("c", [])
        if pname in ("Hand fighting", "Shots"):
            for inner in children:
                if not isinstance(inner, dict): continue
                ipname, imap = extract_position(inner)
                if ipname and imap:
                    out[ipname] = imap
        else:
            ipname, imap = extract_position(pos_node)
            if ipname and imap:
                out[ipname] = imap
print(json.dumps(out, indent=2, ensure_ascii=False))
