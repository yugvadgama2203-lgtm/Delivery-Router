"""
DeliveryRouter - delivery route optimizer with a Tkinter GUI.
Standard library only. Run:  python delivery_router.py

Controls
  Left click   : first click sets the depot, next clicks add delivery stops
  Right click  : remove the nearest stop
Algorithms: Nearest Neighbor, NN + 2-opt, Brute Force (<= 9 stops)
"""
import itertools
import math
import random
import time
import tkinter as tk
from tkinter import ttk, messagebox

KM_PER_PX = 0.02     # map scale
SPEED_KMH = 40       # average vehicle speed
STOP_MIN = 5         # service time per stop (minutes)
MAX_BRUTE = 9        # brute force limit (stops, excluding depot)
ALGOS = ["Nearest Neighbor", "NN + 2-opt", "Brute Force"]


# ----------------------------- routing core -----------------------------
def dist(a, b, metric):
    dx, dy = a[0] - b[0], a[1] - b[1]
    d = abs(dx) + abs(dy) if metric == "Manhattan" else math.hypot(dx, dy)
    return d * KM_PER_PX


def tour_length(order, pts, metric):
    """Length of the closed tour (returns to depot at the end)."""
    n = len(order)
    return sum(dist(pts[order[i]], pts[order[(i + 1) % n]], metric) for i in range(n))


def nearest_neighbor(pts, metric):
    order, left = [0], set(range(1, len(pts)))
    while left:
        last = pts[order[-1]]
        nxt = min(left, key=lambda i: dist(last, pts[i], metric))
        order.append(nxt)
        left.remove(nxt)
    return order


def two_opt(order, pts, metric):
    best, improved = order[:], True
    while improved:
        improved = False
        for i in range(1, len(best) - 1):
            for j in range(i + 1, len(best)):
                cand = best[:i] + best[i:j + 1][::-1] + best[j + 1:]
                if tour_length(cand, pts, metric) < tour_length(best, pts, metric) - 1e-9:
                    best, improved = cand, True
    return best


def brute_force(pts, metric):
    if len(pts) - 1 > MAX_BRUTE:
        raise ValueError(f"Brute Force supports at most {MAX_BRUTE} stops.")
    best = min(itertools.permutations(range(1, len(pts))),
               key=lambda p: tour_length([0, *p], pts, metric))
    return [0, *best]


def solve(algo, pts, metric):
    if algo == "Brute Force":
        return brute_force(pts, metric)
    order = nearest_neighbor(pts, metric)
    return two_opt(order, pts, metric) if algo == "NN + 2-opt" else order


# --------------------------------- GUI ----------------------------------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("DeliveryRouter")
        self.geometry("1050x650")
        self.depot, self.stops, self.route = None, [], []

        side = ttk.Frame(self, padding=10)
        side.pack(side=tk.LEFT, fill=tk.Y)
        self.canvas = tk.Canvas(self, bg="white", highlightthickness=0)
        self.canvas.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.algo = tk.StringVar(value=ALGOS[1])
        self.metric = tk.StringVar(value="Manhattan")
        self.count = tk.IntVar(value=12)

        ttk.Label(side, text="Algorithm").pack(anchor="w")
        ttk.Combobox(side, textvariable=self.algo, values=ALGOS, state="readonly").pack(fill=tk.X, pady=(0, 8))
        ttk.Label(side, text="Distance metric").pack(anchor="w")
        ttk.Combobox(side, textvariable=self.metric, values=["Manhattan", "Euclidean"],
                     state="readonly").pack(fill=tk.X, pady=(0, 8))
        ttk.Label(side, text="Random stops").pack(anchor="w")
        ttk.Spinbox(side, from_=1, to=60, textvariable=self.count).pack(fill=tk.X, pady=(0, 8))

        for text, cmd in [("Add random stops", self.add_random), ("Solve route", self.run_solve),
                          ("Compare all algorithms", self.compare), ("Clear route", self.clear_route),
                          ("Clear all", self.clear_all)]:
            ttk.Button(side, text=text, command=cmd).pack(fill=tk.X, pady=2)

        self.info = ttk.Label(side, text="Stops: 0", font=("TkDefaultFont", 10, "bold"))
        self.info.pack(anchor="w", pady=(12, 4))
        self.log = tk.Text(side, width=34, height=16, state="disabled", font=("Courier", 9))
        self.log.pack(fill=tk.BOTH, expand=True)

        self.canvas.bind("<Button-1>", self.on_add)
        self.canvas.bind("<Button-2>", self.on_remove)  # macOS right click
        self.canvas.bind("<Button-3>", self.on_remove)
        self.canvas.bind("<Configure>", lambda e: self.redraw())

    # ---- helpers ----
    def points(self):
        return [self.depot] + self.stops if self.depot else []

    def write(self, text, clear=False):
        self.log.config(state="normal")
        if clear:
            self.log.delete("1.0", tk.END)
        self.log.insert(tk.END, text + "\n")
        self.log.config(state="disabled")

    def path(self, a, b):
        if self.metric.get() == "Manhattan":
            return [a[0], a[1], b[0], a[1], b[0], b[1]]
        return [*a, *b]

    # ---- events ----
    def on_add(self, e):
        self.route = []
        if self.depot is None:
            self.depot = (e.x, e.y)
        else:
            self.stops.append((e.x, e.y))
        self.update_info()
        self.redraw()

    def on_remove(self, e):
        if not self.stops:
            return
        k = min(range(len(self.stops)), key=lambda i: math.dist(self.stops[i], (e.x, e.y)))
        if math.dist(self.stops[k], (e.x, e.y)) < 20:
            self.stops.pop(k)
            self.route = []
            self.update_info()
            self.redraw()

    def add_random(self):
        w, h = max(self.canvas.winfo_width(), 200), max(self.canvas.winfo_height(), 200)
        if self.depot is None:
            self.depot = (w // 2, h // 2)
        for _ in range(self.count.get()):
            self.stops.append((random.randint(30, w - 30), random.randint(30, h - 30)))
        self.route = []
        self.update_info()
        self.redraw()

    def clear_route(self):
        self.route = []
        self.redraw()

    def clear_all(self):
        self.depot, self.stops, self.route = None, [], []
        self.write("", clear=True)
        self.update_info()
        self.redraw()

    def update_info(self):
        self.info.config(text=f"Stops: {len(self.stops)}")

    # ---- solving ----
    def run_solve(self):
        pts = self.points()
        if len(pts) < 2:
            messagebox.showinfo("DeliveryRouter", "Set a depot and add at least one stop.")
            return
        try:
            t0 = time.perf_counter()
            self.route = solve(self.algo.get(), pts, self.metric.get())
            ms = (time.perf_counter() - t0) * 1000
        except ValueError as err:
            messagebox.showwarning("DeliveryRouter", str(err))
            return
        km = tour_length(self.route, pts, self.metric.get())
        minutes = km / SPEED_KMH * 60 + STOP_MIN * len(self.stops)
        self.write(f"{self.algo.get()}\nDistance: {km:.2f} km\nETA: {minutes:.0f} min\n"
                   f"Solved in {ms:.1f} ms\nOrder: D -> " + " -> ".join(map(str, self.route[1:])) + " -> D",
                   clear=True)
        self.redraw()

    def compare(self):
        pts = self.points()
        if len(pts) < 3:
            messagebox.showinfo("DeliveryRouter", "Add at least two stops to compare.")
            return
        self.write("Algorithm comparison", clear=True)
        for algo in ALGOS:
            try:
                t0 = time.perf_counter()
                order = solve(algo, pts, self.metric.get())
                ms = (time.perf_counter() - t0) * 1000
                km = tour_length(order, pts, self.metric.get())
                self.write(f"{algo:<17}{km:7.2f} km {ms:8.1f} ms")
            except ValueError:
                self.write(f"{algo:<17}skipped (>{MAX_BRUTE} stops)")

    # ---- drawing ----
    def redraw(self):
        c = self.canvas
        c.delete("all")
        w, h = c.winfo_width(), c.winfo_height()
        for x in range(0, w, 50):
            c.create_line(x, 0, x, h, fill="#eceff3")
        for y in range(0, h, 50):
            c.create_line(0, y, w, y, fill="#eceff3")
        pts = self.points()
        if not pts:
            c.create_text(w // 2, h // 2, fill="#9ca3af", font=("TkDefaultFont", 13),
                          text="Click to place the depot, then click to add delivery stops")
        n = len(self.route)
        for k in range(n):
            a, b = pts[self.route[k]], pts[self.route[(k + 1) % n]]
            c.create_line(*self.path(a, b), fill="#2563eb", width=2, arrow=tk.LAST)
        visit = {idx: pos for pos, idx in enumerate(self.route)}
        for i, (x, y) in enumerate(pts):
            if i == 0:
                c.create_rectangle(x - 10, y - 10, x + 10, y + 10, fill="#16a34a", outline="white", width=2)
                c.create_text(x, y, text="D", fill="white", font=("TkDefaultFont", 9, "bold"))
            else:
                c.create_oval(x - 10, y - 10, x + 10, y + 10, fill="#ef4444", outline="white", width=2)
                c.create_text(x, y, text=str(visit.get(i, i)), fill="white", font=("TkDefaultFont", 8, "bold"))


if __name__ == "__main__":
    App().mainloop()
