"""
DX Terminal Reap ROI
Transparent floating window - POOPCOIN + SLOP / HOTDOGZ / HOLE columns
Each reap token has its own editable holding % and reap gain %.
"""
import tkinter as tk
from urllib.request import urlopen, Request
from concurrent.futures import ThreadPoolExecutor
import json
import threading
import time
import webbrowser

# === Config ===
DEFAULT_HOLDING_PCT = 1.0
DEFAULT_REAP_PCT = 3.5
REFRESH_INTERVAL = 15
TOTAL_SUPPLY = 1_000_000_000

POOPCOIN_CONTRACT = "0xbDa4FC392f761787f7F16D3C554ED8b9a15e91B1"

REAP_TOKENS = [
    ("SLOP",    "0xb7bD411cd4851AF0291EE3998cF0C3aCb9eF8fe4", "#00d2ff"),
    ("HOTDOGZ", "0x781BAe1c8E0DbB4950845A6d776d94C33b326D8a", "#ff6b9d"),
    ("HOLE",    "0xFcc897aaC0073A94ca3D91E567f0129822558C1d", "#b388ff"),
]

EXCLUDE_ADDRESSES = [
    "0x498581fF718922c3f8e6A244956aF099B2652b2b",
    "0xF9283Ae11B7315911fd8E762a7C8B496d5B2F366",
    "0x6189a688C90dae64D7b4a7Bd3a74cEd15d6857C8",
]

BASE_RPC = "https://mainnet.base.org"
DEXSCREENER_API = "https://api.dexscreener.com/latest/dex/tokens/{}"


def fetch_json(url, data=None):
    headers = {"Content-Type": "application/json", "Accept": "application/json",
                "User-Agent": "Mozilla/5.0"}
    if data:
        req = Request(url, data=json.dumps(data).encode(), headers=headers)
    else:
        req = Request(url, headers=headers)
    with urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode())


def get_mcap(contract):
    url = DEXSCREENER_API.format(contract)
    data = fetch_json(url)
    pairs = data.get("pairs") or []
    if pairs:
        raw_mcap = pairs[0].get("marketCap") or pairs[0].get("fdv") or 0
        mcap = float(raw_mcap)
        price = float(pairs[0].get("priceUsd") or 0)
        return mcap, price
    return 0.0, 0.0


def get_token_balance(contract, holder):
    addr_padded = holder.lower().replace("0x", "").zfill(64)
    call_data = "0x70a08231" + addr_padded
    payload = {
        "jsonrpc": "2.0", "method": "eth_call",
        "params": [{"to": contract, "data": call_data}, "latest"], "id": 1,
    }
    result = fetch_json(BASE_RPC, payload)
    return int(result.get("result", "0x0"), 16)


def get_decimals(contract):
    payload = {
        "jsonrpc": "2.0", "method": "eth_call",
        "params": [{"to": contract, "data": "0x313ce567"}, "latest"], "id": 1,
    }
    result = fetch_json(BASE_RPC, payload)
    return int(result.get("result", "0x12"), 16)


# Cache: {(contract, addr): last_known_balance}
_balance_cache = {}


def get_balance_with_retry(contract, addr, retries=2):
    """Fetch balance with retry; fall back to cached value on failure."""
    key = (contract.lower(), addr.lower())
    for attempt in range(retries + 1):
        try:
            bal = get_token_balance(contract, addr)
            _balance_cache[key] = bal
            return bal
        except Exception:
            if attempt < retries:
                time.sleep(0.5)
    # All retries failed — use cached value
    return _balance_cache.get(key, 0)


def get_excluded_pct(contract, decimals):
    total = 0
    for addr in EXCLUDE_ADDRESSES:
        total += get_balance_with_retry(contract, addr)
    return (total / (10 ** decimals)) / TOTAL_SUPPLY


def _make_entry(parent, var, bg="#0f3460"):
    e = tk.Entry(parent, textvariable=var, font=("Consolas", 9), width=7,
                 bg=bg, fg="#fff", insertbackground="#fff", bd=1, relief="solid",
                 justify="center")

    def _on_click(ev):
        ev.widget.focus_set()
        return "break"

    e.bind("<Button-1>", _on_click)
    e.bind("<B1-Motion>", lambda ev: "break")
    return e


def _fetch_token_data(name, contract, decimals):
    """Fetch mcap + excluded pct for a single token (used in thread pool)."""
    mcap, price = get_mcap(contract)
    excl = get_excluded_pct(contract, decimals)
    return name, {"mcap": mcap, "price": price,
                  "user_holdings": 1.0 - excl, "excluded_pct": excl}


class MonitorApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("DX Terminal Reap ROI")
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", 0.85)
        self.root.overrideredirect(True)
        self.root.configure(bg="#1a1a2e")

        n = len(REAP_TOKENS)
        win_w = 150 * n + 20
        self.root.geometry(f"{win_w}x370+100+100")

        self._last_data = None
        self._drag_data = {"x": 0, "y": 0}
        self.root.bind("<Button-1>", self._on_drag_start)
        self.root.bind("<B1-Motion>", self._on_drag_motion)
        self.root.bind("<Button-3>", self._on_right_click)

        self._build_ui()

        self.running = True
        self.thread = threading.Thread(target=self._update_loop, daemon=True)
        self.thread.start()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self):
        bg = "#1a1a2e"
        fg = "#e0e0e0"
        green = "#00ff88"
        yellow = "#ffcc00"
        header_bg = "#16213e"

        # Title bar
        title_frame = tk.Frame(self.root, bg=header_bg)
        title_frame.pack(fill="x")
        tk.Label(title_frame, text=" DX Terminal Reap ROI", font=("Consolas", 10, "bold"),
                 bg=header_bg, fg="#00d2ff", anchor="w").pack(side="left", padx=5)
        tk.Button(title_frame, text="X", font=("Consolas", 8, "bold"),
                  bg=header_bg, fg="#ff4444", bd=0, command=self._on_close).pack(side="right", padx=5)

        # POOPCOIN header
        poop_frame = tk.Frame(self.root, bg=bg, padx=10, pady=4)
        poop_frame.pack(fill="x")
        tk.Label(poop_frame, text="POOPCOIN", font=("Consolas", 11, "bold"),
                 bg=bg, fg=yellow, anchor="w").pack(side="left")
        self.poop_mcap_label = tk.Label(poop_frame, text="loading...",
                                         font=("Consolas", 10), bg=bg, fg=fg)
        self.poop_mcap_label.pack(side="right")

        tk.Frame(self.root, bg="#333", height=1).pack(fill="x")

        # Columns container
        cols_frame = tk.Frame(self.root, bg=bg, padx=5, pady=5)
        cols_frame.pack(fill="x")

        self.columns = {}
        for i, (name, contract, color) in enumerate(REAP_TOKENS):
            col = tk.Frame(cols_frame, bg=bg, padx=5)
            col.pack(side="left", fill="y", expand=True)

            # Separator between columns
            if i > 0:
                sep = tk.Frame(cols_frame, bg="#333", width=1)
                sep.pack(side="left", fill="y", before=col)

            # Token name
            tk.Label(col, text=name, font=("Consolas", 11, "bold"),
                     bg=bg, fg=color).pack(anchor="center")

            # Mcap
            mcap_lbl = tk.Label(col, text="$--", font=("Consolas", 9, "bold"),
                                bg=bg, fg=fg)
            mcap_lbl.pack(anchor="center")

            # Price
            price_lbl = tk.Label(col, text="$--", font=("Consolas", 8),
                                 bg=bg, fg="#888")
            price_lbl.pack(anchor="center")

            # User holdings
            user_lbl = tk.Label(col, text="Users: --%", font=("Consolas", 8),
                                bg=bg, fg="#777")
            user_lbl.pack(anchor="center", pady=(3, 0))

            tk.Frame(col, bg="#333", height=1).pack(fill="x", pady=4)

            # Holding %
            tk.Label(col, text="Hold %", font=("Consolas", 8), bg=bg, fg="#aaa").pack()
            hold_var = tk.StringVar(value=str(DEFAULT_HOLDING_PCT))
            hold_entry = _make_entry(col, hold_var)
            hold_entry.pack(pady=1)
            hold_entry.bind("<Return>", lambda e: self._update_ui())
            hold_entry.bind("<FocusOut>", lambda e: self._update_ui())

            # Reap gain %
            tk.Label(col, text="Reap %", font=("Consolas", 8), bg=bg, fg="#aaa").pack()
            reap_var = tk.StringVar(value=str(DEFAULT_REAP_PCT))
            reap_entry = _make_entry(col, reap_var)
            reap_entry.pack(pady=1)
            reap_entry.bind("<Return>", lambda e: self._update_ui())
            reap_entry.bind("<FocusOut>", lambda e: self._update_ui())

            tk.Frame(col, bg="#333", height=1).pack(fill="x", pady=4)

            # Cost
            cost_lbl = tk.Label(col, text="Cost: $--", font=("Consolas", 8),
                                bg=bg, fg="#aaa")
            cost_lbl.pack(anchor="center")

            # Value
            val_lbl = tk.Label(col, text="$--", font=("Consolas", 11, "bold"),
                               bg=bg, fg=green)
            val_lbl.pack(anchor="center")

            # ROI
            roi_lbl = tk.Label(col, text="ROI: --%", font=("Consolas", 9, "bold"),
                               bg=bg, fg=yellow)
            roi_lbl.pack(anchor="center")

            self.columns[name] = {
                "mcap_lbl": mcap_lbl, "price_lbl": price_lbl,
                "user_lbl": user_lbl, "cost_lbl": cost_lbl,
                "val_lbl": val_lbl, "roi_lbl": roi_lbl,
                "hold_var": hold_var, "reap_var": reap_var,
            }

        # Status bar
        status_frame = tk.Frame(self.root, bg=header_bg)
        status_frame.pack(fill="x")
        self.status_label = tk.Label(status_frame, text="Right-click to close | Drag to move",
                                      font=("Consolas", 7), bg=header_bg, fg="#666")
        self.status_label.pack(side="left", padx=5)

        # Author credit
        author_lbl = tk.Label(status_frame, text="Sanqing", font=("Consolas", 7, "underline"),
                               bg=header_bg, fg="#00d2ff", cursor="hand2")
        author_lbl.pack(side="right", padx=(0, 2))
        author_lbl.bind("<Button-1>", lambda e: webbrowser.open("https://x.com/sanqing_rx"))
        tk.Label(status_frame, text="by Claude |", font=("Consolas", 7),
                 bg=header_bg, fg="#666").pack(side="right")

    def _update_loop(self):
        self.token_decimals = {}
        for name, contract, _ in REAP_TOKENS:
            try:
                self.token_decimals[name] = get_decimals(contract)
            except Exception:
                self.token_decimals[name] = 18

        while self.running:
            try:
                self._fetch_and_update()
            except Exception as e:
                if self.running:
                    try:
                        self.root.after(0, lambda e=e: self.status_label.config(
                            text=f"Error: {str(e)[:50]}"))
                    except Exception:
                        pass
            time.sleep(REFRESH_INTERVAL)

    def _fetch_and_update(self):
        if not self.running:
            return

        # Fetch POOPCOIN + all reap tokens in parallel
        with ThreadPoolExecutor(max_workers=4) as pool:
            poop_future = pool.submit(get_mcap, POOPCOIN_CONTRACT)
            token_futures = [
                pool.submit(_fetch_token_data, name, contract,
                            self.token_decimals.get(name, 18))
                for name, contract, _ in REAP_TOKENS
            ]

            poop_mcap, poop_price = poop_future.result()
            tokens_data = {}
            for f in token_futures:
                name, data = f.result()
                tokens_data[name] = data

        self._last_data = {
            "poop_mcap": poop_mcap, "poop_price": poop_price,
            "tokens": tokens_data,
        }

        if self.running:
            try:
                self.root.after(0, self._update_ui)
            except Exception:
                pass

    def _update_ui(self):
        if not self._last_data:
            return
        d = self._last_data
        poop_mcap = d["poop_mcap"]

        self.poop_mcap_label.config(
            text=f"${poop_mcap:,.0f}  |  ${d['poop_price']:.6f}")

        for name, td in d["tokens"].items():
            c = self.columns[name]
            c["mcap_lbl"].config(text=f"${td['mcap']:,.0f}")
            c["price_lbl"].config(text=f"${td['price']:.8f}")
            uh = td["user_holdings"]
            c["user_lbl"].config(text=f"Users: {uh*100:.1f}%")

            try:
                hold = float(c["hold_var"].get())
            except ValueError:
                hold = 0
            try:
                reap = float(c["reap_var"].get())
            except ValueError:
                reap = 0

            my_pct = max(hold, 0) / 100.0
            my_share = my_pct / uh if uh > 0 else 0
            cost = my_pct * td["mcap"]
            value = my_share * (max(reap, 0) / 100.0) * poop_mcap
            roi = ((value - cost) / cost * 100) if cost > 0 else 0

            c["cost_lbl"].config(text=f"Cost: ${cost:,.2f}")
            c["val_lbl"].config(text=f"${value:,.2f}")
            c["roi_lbl"].config(text=f"ROI: {roi:+,.1f}%",
                                fg="#00ff88" if roi >= 0 else "#ff4444")

        self.status_label.config(
            text=f"Updated {time.strftime('%H:%M:%S')} | Refresh: {REFRESH_INTERVAL}s")

    def _on_drag_start(self, event):
        self._drag_data["x"] = event.x
        self._drag_data["y"] = event.y

    def _on_drag_motion(self, event):
        x = self.root.winfo_x() + event.x - self._drag_data["x"]
        y = self.root.winfo_y() + event.y - self._drag_data["y"]
        self.root.geometry(f"+{x}+{y}")

    def _on_right_click(self, event):
        self._on_close()

    def _on_close(self):
        self.running = False
        self.root.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = MonitorApp()
    app.run()
