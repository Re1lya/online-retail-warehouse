"""从 dbt manifest 导出模型依赖及可独立打开的模型文档。"""
import json
from html import escape
from pathlib import Path


def portable_text(text, project_root):
    return text.replace(str(project_root), '.').replace(json.dumps(str(project_root))[1:-1], '.')


def export_lineage(target: Path, destination: Path, project_root: Path):
    manifest=json.loads((target/'manifest.json').read_text())
    nodes={k:v for k,v in {**manifest['sources'],**manifest['nodes']}.items()
           if v['resource_type'] in ('source','model')}
    ids={key:f'n{i}' for i,key in enumerate(sorted(nodes))}
    lines=['flowchart LR']
    for key,node in nodes.items():
        lines.append(f'  {ids[key]}["{node["schema"]}.{node.get("alias",node["name"])}"]')
    edges=[]
    for key,node in nodes.items():
        for parent in node.get('depends_on',{}).get('nodes',[]):
            if parent in nodes:
                lines.append(f'  {ids[parent]} --> {ids[key]}')
                edges.append({'from':nodes[parent]['name'],'to':node['name']})
    destination.mkdir(parents=True,exist_ok=True)
    (destination/'lineage.mmd').write_text('\n'.join(lines)+'\n')
    (destination/'lineage.json').write_text(json.dumps({'models':len(nodes)-len(manifest['sources']),
        'nodes':[{'name':n['name'],'relation':n['schema']+'.'+n.get('alias',n['name'])} for n in nodes.values()],
        'edges':edges},ensure_ascii=False,indent=2))
    # 按真实依赖的拓扑层级绘制可缩放血缘图。
    levels={key:0 for key,n in nodes.items() if n['resource_type']=='source'}
    while len(levels)<len(nodes):
        ready=[key for key,n in nodes.items() if key not in levels and
               all(parent in levels for parent in n.get('depends_on',{}).get('nodes',[]) if parent in nodes)]
        if not ready:raise ValueError('dbt模型依赖存在循环')
        for key in ready:
            levels[key]=1+max((levels[parent] for parent in nodes[key].get('depends_on',{}).get('nodes',[]) if parent in nodes),default=-1)
    groups={level:sorted(k for k in levels if levels[k]==level) for level in sorted(set(levels.values()))}
    width=(max(groups)+1)*285+50;height=max(len(g) for g in groups.values())*94+110
    positions={key:(25+level*285,85+(i+.5)*((height-100)/len(keys))-27)
               for level,keys in groups.items() for i,key in enumerate(keys)}
    svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
         '<rect width="100%" height="100%" fill="white"/>',
         '<defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0 0 L8 4 L0 8" fill="#71959c"/></marker></defs>',
         '<text x="25" y="35" font-family="sans-serif" font-size="25" fill="#102e3b">dbt model lineage</text>']
    for key,n in nodes.items():
        x,y=positions[key]
        for parent in n.get('depends_on',{}).get('nodes',[]):
            if parent not in positions:continue
            px,py=positions[parent];mid=(px+240+x)/2
            svg.append(f'<path d="M{px+240},{py+27} C{mid},{py+27} {mid},{y+27} {x},{y+27}" fill="none" stroke="#71959c" stroke-width="1.3" marker-end="url(#arrow)"/>')
    for key,n in nodes.items():
        x,y=positions[key];label=escape(n['schema']+'.'+n.get('alias',n['name']))
        svg.append(f'<rect x="{x}" y="{y}" width="240" height="54" rx="4" fill="#edf5f5" stroke="#91b7b8"/>')
        svg.append(f'<text x="{x+10}" y="{y+32}" font-family="sans-serif" font-size="15" fill="#102e3b">{label}</text>')
    svg.append('</svg>');(destination/'lineage.svg').write_text('\n'.join(svg)+'\n')
    # 文档中的库名对应发布后的文件，移除本机构建目录。
    html=portable_text((target/'static_index.html').read_text(),project_root).replace('retail.building','retail')
    (destination/'dbt').mkdir(exist_ok=True)
    (destination/'dbt/index.html').write_text(html)
