"""Preview or apply the eight enriched Summer Palace presets without reseeding other data.

Run from the repository root: .venv/Scripts/python.exe scripts/sync_recommended_routes.py --apply
Existing matching presets keep their IDs. Custom routes, spots and guides are preserved.
"""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dotenv import load_dotenv
load_dotenv(ROOT / '.env', override=True)
from sqlmodel import Session, select
from server.base.database.init_db import DB_ENGINE
from server.base.models.user_model import UserInfo
from server.base.models.tour_models import ScenicSpotInfo, TourRoute, TourRouteSpot
from server.base.modules.recommended_routes import route_profiles
from server.base.modules.route_presentation import route_overview


def sync(apply=False):
    with Session(DB_ENGINE) as session:
        owner = session.exec(select(UserInfo).where(UserInfo.delete == False)
                             .order_by(UserInfo.user_id)).first()
        if not owner:
            raise ValueError('Initialize the configured database before syncing routes')
        available = session.exec(select(ScenicSpotInfo).where(
            ScenicSpotInfo.user_id == owner.user_id, ScenicSpotInfo.delete == False)).all()
        by_name = {}
        for spot in available:
            if spot.city in ('北京', '北京市', 'Beijing'):
                if spot.spot_name in by_name:
                    raise ValueError('Duplicate spot name: ' + spot.spot_name)
                by_name[spot.spot_name] = spot
        plans = []
        for profile in route_profiles():
            names = [s[0] for s in profile['stops']]
            if len(set(names)) != len(names) or any(n not in by_name for n in names):
                raise ValueError('Missing or duplicate curated stops: ' + profile['name'])
            spots = [by_name[n] for n in names]
            overview = route_overview([s.model_dump() for s in spots])
            if not overview['complete'] or not overview['total_minutes']:
                raise ValueError('Walking graph cannot complete route: ' + profile['name'])
            plans.append((profile, spots, overview))
        # Snapshot only route tables; this command never updates scenic knowledge or avatars.
        routes = session.exec(select(TourRoute).where(TourRoute.user_id == owner.user_id)).all()
        route_ids = [r.route_id for r in routes]
        links = session.exec(select(TourRouteSpot).where(TourRouteSpot.route_id.in_(route_ids))).all() if route_ids else []
        if apply:
            backup = ROOT / 'work_dirs/recommended-routes'
            backup.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now().strftime('%Y%m%d-%H%M%S-%f')
            (backup / f'before-{stamp}.json').write_text(json.dumps(dict(
                routes=[r.model_dump(mode='json') for r in routes],
                links=[r.model_dump(mode='json') for r in links]), ensure_ascii=False, indent=2), encoding='utf-8')
        result = []
        for profile, spots, overview in plans:
            matches = [r for r in routes if r.name == profile['name'] and not r.delete]
            if len(matches) > 1:
                raise ValueError('Duplicate preset route name: ' + profile['name'])
            route = matches[0] if matches else TourRoute(name=profile['name'], user_id=owner.user_id)
            if apply:
                route.theme = profile['theme']
                route.city = '北京'
                route.description = profile['summary']
                route.estimated_time_minutes = overview['total_minutes']
                session.add(route)
                session.flush()
                for link in session.exec(select(TourRouteSpot).where(TourRouteSpot.route_id == route.route_id)).all():
                    session.delete(link)
                session.flush()
                for order, spot in enumerate(spots):
                    session.add(TourRouteSpot(route_id=route.route_id, spot_id=spot.spot_id, spot_order=order))
            result.append(dict(name=profile['name'], stops=len(spots),
                walking_meters=overview['walking_meters'], minutes=overview['total_minutes']))
        if apply:
            session.commit()
        return dict(applied=apply, database=DB_ENGINE.url.database, routes=result)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    print(json.dumps(sync(args.apply), ensure_ascii=True, indent=2))
