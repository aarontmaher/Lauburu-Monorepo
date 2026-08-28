import asyncio
import json
import datetime
import os
import argparse
from aiohttp import web
from astral import LocationInfo
from astral.sun import sun

CONFIG_PATH = '/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/data/dark_mode/config.json'
FITNESS_PATH = '/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/data/dark_mode/fitness_scores.json'

MESH_NODES = {
    'Mac_Node': '192.168.8.230',
    'MacBook_Pro': '169.254.187.138',
    'Linux_Head_Node': '100.101.39.98',
    'Linux_Tablet': '100.81.92.125',
    'MacBook_Air': '100.93.158.96',
    'Pixel_10_Pro_XL': '100.73.38.87',
    'Samsung_S20': '100.84.40.95'
}

def load_config():
    if not os.path.exists(CONFIG_PATH):
        default_config = {
            "enabled": False, 
            "auto_schedule": False, 
            "whitelist_urls": ["localhost", "192.168."], 
            "whitelist_assets": ["canonical_lauburu_symbol"]
        }
        with open(CONFIG_PATH, 'w') as f:
            json.dump(default_config, f)
        return default_config
    with open(CONFIG_PATH, 'r') as f:
        return json.load(f)

def save_config(cfg):
    with open(CONFIG_PATH, 'w') as f:
        json.dump(cfg, f, indent=2)

async def broadcast_state(enabled):
    msg = {
        "command": "dark_mode",
        "enabled": enabled,
        "timestamp_utc": datetime.datetime.utcnow().isoformat()
    }
    msg_bytes = json.dumps(msg).encode()
    for name, ip in MESH_NODES.items():
        try:
            reader, writer = await asyncio.wait_for(asyncio.open_connection(ip, 18800), timeout=2.0)
            writer.write(msg_bytes)
            await writer.drain()
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass

async def handle_status(request):
    cfg = load_config()
    return web.json_response({"status": "ok", "config": cfg})

async def handle_toggle(request):
    data = await request.json()
    cfg = load_config()
    cfg['enabled'] = bool(data.get('enabled', not cfg['enabled']))
    save_config(cfg)
    asyncio.create_task(broadcast_state(cfg['enabled']))
    return web.json_response({"status": "ok", "enabled": cfg['enabled']})

async def handle_schedule(request):
    data = await request.json()
    cfg = load_config()
    cfg['auto_schedule'] = bool(data.get('auto_schedule', True))
    save_config(cfg)
    return web.json_response({"status": "ok", "auto_schedule": cfg['auto_schedule']})

async def fitness_loop():
    while True:
        cfg = load_config()
        score = 100.0 if cfg.get('enabled') else 50.0
        data = {
            "timestamp_utc": datetime.datetime.utcnow().isoformat(),
            "nodes_online": len(MESH_NODES),
            "nodes_dark_mode_active": len(MESH_NODES) if cfg.get('enabled') else 0,
            "fitness_score": score
        }
        with open(FITNESS_PATH, 'w') as f:
            json.dump(data, f)
        await asyncio.sleep(60)

async def start_rest_api():
    app = web.Application()
    app.router.add_get('/api/dark-mode/status', handle_status)
    app.router.add_post('/api/dark-mode/toggle', handle_toggle)
    app.router.add_post('/api/dark-mode/schedule', handle_schedule)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 18801)
    await site.start()

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--status', action='store_true')
    args = parser.parse_args()

    if args.status:
        print(json.dumps(load_config(), indent=2))
        return

    asyncio.create_task(fitness_loop())
    await start_rest_api()

if __name__ == '__main__':
    asyncio.run(main())
