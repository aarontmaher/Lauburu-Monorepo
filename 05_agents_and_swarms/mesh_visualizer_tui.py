#!/usr/bin/env python3
import curses
import json
import time
import subprocess
import sys

def draw_tui(stdscr):
    curses.curs_set(0)
    stdscr.nodelay(1)
    
    curses.start_color()
    curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK) # Start
    curses.init_pair(2, curses.COLOR_RED, curses.COLOR_BLACK)   # End
    curses.init_pair(3, curses.COLOR_BLUE, curses.COLOR_BLACK)  # Visited
    curses.init_pair(4, curses.COLOR_YELLOW, curses.COLOR_BLACK)# Optimal Path
    curses.init_pair(5, curses.COLOR_WHITE, curses.COLOR_BLACK) # Default
    
    grid_coords = {
        "L1_Mac_Node": (5, 10),
        "L2_MacBook_Pro": (5, 30),
        "L5_MacBook_Air": (5, 50),
        "GW_Router": (10, 30),
        "L3_Linux_Head": (15, 10),
        "L4_Linux_Tablet": (15, 30),
        "L6_Pixel_10_Pro": (15, 50),
        "L7_Samsung_S20": (15, 70)
    }

    while True:
        stdscr.clear()
        stdscr.addstr(1, 2, "Lauburu Mesh: Genetic BFS Optimizer Visualizer (Data from Router)", curses.A_BOLD)
        stdscr.addstr(2, 2, "Target: Routing from L1_Mac_Node -> L6_Pixel_10_Pro")
        
        # Fetch the JSON from the router's /tmp dir via SSH
        try:
            res = subprocess.run(["ssh", "root@192.168.8.1", "cat /tmp/ga_optimized_path.json"], capture_output=True, text=True, timeout=2)
            if res.returncode == 0:
                data = json.loads(res.stdout)
                best_path = data.get("best_path", [])
                telemetry = data.get("telemetry_used", {}).get("nodes", {})
                fitness = data.get("fitness", 0)
                
                stdscr.addstr(3, 2, f"Generation Fitness: {fitness:.4f} | Optimal Hops: {len(best_path)-1}")
                
                for node, (y, x) in grid_coords.items():
                    lat = telemetry.get(node, {}).get("latency", "--")
                    color = curses.color_pair(5)
                    if node == best_path[0]: color = curses.color_pair(1)
                    elif node == best_path[-1]: color = curses.color_pair(2)
                    elif node in best_path: color = curses.color_pair(4)
                    
                    stdscr.attron(color)
                    stdscr.addstr(y, x, f"[{node}]")
                    stdscr.attroff(color)
                    stdscr.addstr(y+1, x, f" Latency: {lat}ms")
            else:
                stdscr.addstr(4, 2, "Waiting for Genetic Optimizer data from router /tmp/ga_optimized_path.json...")
        except Exception as e:
            stdscr.addstr(4, 2, f"Error fetching from router: {e}")
            
        stdscr.refresh()
        if stdscr.getch() == ord('q'): break
        time.sleep(1)

if __name__ == "__main__":
    curses.wrapper(draw_tui)
