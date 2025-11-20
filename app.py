from flask import Flask, render_template, request
import folium, json, networkx as nx, os
from collections import deque
import osmnx as ox

# --- Cấu hình Flask ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, template_folder=os.path.join(BASE_DIR, "templates"))

# --- Đọc dữ liệu bản đồ ---
with open(os.path.join(BASE_DIR, "map_data.json"), "r", encoding="utf-8") as f:
    data = json.load(f)

nodes = data["nodes"]
edges = data["edges"]

# --- Tạo đồ thị logic (dùng cho BFS/DFS) ---
G = nx.Graph()
for a, b in edges:
    x1, y1 = nodes[a]
    x2, y2 = nodes[b]
    G.add_edge(a, b, weight=((x1 - x2)**2 + (y1 - y2)**2)**0.5)

# --- Tạo bản đồ thực tế (OSM) ---
print("Đang tải bản đồ TP.HCM...")
avg_lat = sum(v[0] for v in nodes.values()) / len(nodes)
avg_lon = sum(v[1] for v in nodes.values()) / len(nodes)

# Tải bản đồ quanh khu vực các điểm
G_osm = ox.graph_from_point((avg_lat, avg_lon), dist=8000, network_type="drive")
G_osm = ox.add_edge_speeds(G_osm)
G_osm = ox.add_edge_travel_times(G_osm)
print("Tải bản đồ hoàn tất!")

# --- Hàm tìm đường thực tế giữa 2 tọa độ ---
def real_route(start, end):
    s_node = ox.distance.nearest_nodes(G_osm, start[1], start[0])
    e_node = ox.distance.nearest_nodes(G_osm, end[1], end[0])
    route = nx.shortest_path(G_osm, s_node, e_node, weight="travel_time")
    return [(G_osm.nodes[n]["y"], G_osm.nodes[n]["x"]) for n in route]

# --- BFS ---
def bfs(start, goal):
    queue = deque([[start]])
    visited = set()
    while queue:
        path = queue.popleft()
        node = path[-1]
        if node == goal:
            return path
        if node not in visited:
            visited.add(node)
            for nb in G.neighbors(node):
                if nb not in visited:
                    queue.append(path + [nb])
    return None

# --- DFS ---
def dfs(start, goal):
    stack = [[start]]
    visited = set()
    while stack:
        path = stack.pop()
        node = path[-1]
        if node == goal:
            return path
        if node not in visited:
            visited.add(node)
            for nb in reversed(list(G.neighbors(node))):
                if nb not in visited:
                    stack.append(path + [nb])
    return None

# --- Trang chính ---
@app.route("/", methods=["GET", "POST"])
def index():
    path = []
    algo = None

    if request.method == "POST":
        start = request.form["start"]
        goal = request.form["goal"]
        algo = request.form["algorithm"]

        path = bfs(start, goal) if algo == "bfs" else dfs(start, goal)

    # --- Vẽ bản đồ ---
    m = folium.Map(location=[avg_lat, avg_lon], zoom_start=13)

    # Vẽ các điểm
    for name, coord in nodes.items():
        folium.Marker(coord, tooltip=name).add_to(m)

    # Vẽ đường đi thực tế
    if path and len(path) >= 2:
        route = real_route(nodes[path[0]], nodes[path[-1]])
        color = "green" if algo == "bfs" else "blue"
        folium.PolyLine(route, color=color, weight=5, opacity=0.8).add_to(m)

    return render_template("index.html",map_html=m._repr_html_(),nodes=nodes.keys(),path=path,algo=algo)

if __name__ == "__main__":
    app.run(debug=True)

