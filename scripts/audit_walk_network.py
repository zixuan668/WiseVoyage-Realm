"""Offline connectivity/geometry audit, not live access certification."""
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from server.base.modules import walking_network as w
from server.base.modules.walk_access import pedestrian_access_allowed

def audit():
    anchors={**w.NETWORK['anchors'],**w.NETWORK['gates']}
    disconnected=[[n,m] for n,a in anchors.items() for m,b in anchors.items() if n<m and w._path(a['node_id'],b['node_id'],False,w.rules()) is None]
    invalid=[i for i,e in enumerate(w.NETWORK['edges']) if e['a'] not in w.NODES or e['b'] not in w.NODES or abs(w.haversine(w.NODES[e['a']],w.NODES[e['b']])-e['meters'])>1]
    return {'network_version':w.network_version(),'nodes':len(w.NODES),'edges':len(w.NETWORK['edges']),'anchors':len(anchors),'checked_pairs':len(anchors)*(len(anchors)-1)//2,'disconnected_pairs':disconnected,'invalid_geometry_edges':invalid,'restricted_edges_excluded_at_runtime':sum(not pedestrian_access_allowed(e) for e in w.NETWORK['edges']),'access_points_requiring_field_review':[{'name':n,'offset_meters':a.get('offset_meters',0)} for n,a in anchors.items() if a.get('offset_meters',0)>30],'limitation':'Connectivity and geometry only; projected entrances and live closures require field verification.'}
if __name__=='__main__':
    report=audit();text=json.dumps(report,ensure_ascii=False,indent=2)
    if len(sys.argv)>1: Path(sys.argv[1]).write_text(text+'\n',encoding='utf8')
    print(text)
    sys.exit(1 if report['invalid_geometry_edges'] or report['disconnected_pairs'] else 0)
