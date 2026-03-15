# DX Terminal Reap ROI

Real-time transparent floating window for tracking [DX Terminal](https://www.terminal.markets/tokens) token reap returns.

![Python](https://img.shields.io/badge/Python-3.8+-blue) ![Platform](https://img.shields.io/badge/Platform-Windows-green) ![License](https://img.shields.io/badge/License-MIT-yellow)

## Features

- **Multi-token columns** — SLOP, HOTDOGZ, HOLE side by side
- **Live POOPCOIN Mcap** header with price
- **Editable Hold %** and **Reap %** per token column
- **Cost / Value / ROI** calculated in real-time
- **On-chain user holdings** — auto-excludes system addresses
- Draggable, always-on-top, semi-transparent window
- Right-click to close

## Quick Start

### Option 1: Download Portable EXE (Recommended)

Download `DX-Terminal-Reap-ROI.exe` from [Releases](https://github.com/Sanqingrx/DX-Terminal-Reap-ROI/releases), double-click to run. No installation needed.

### Option 2: Run from Source

Requirements: Python 3.8+ (only standard library, no extra dependencies)

```bash
git clone https://github.com/Sanqingrx/DX-Terminal-Reap-ROI.git
cd DX-Terminal-Reap-ROI
python terminal_monitor.py
```

### Option 3: Build EXE Yourself

```bash
pip install pyinstaller
python -m PyInstaller --onefile --noconsole --name "DX-Terminal-Reap-ROI" terminal_monitor.py
# Output: dist/DX-Terminal-Reap-ROI.exe
```

## How It Works

Each reap token (SLOP / HOTDOGZ / HOLE) column calculates:

| Field | Formula |
|-------|---------|
| **User Holdings** | `1 - (excluded addresses balance / total supply)` |
| **My Share** | `(Hold% / 100) / User Holdings` |
| **Cost** | `Hold% / 100 * Token Mcap` |
| **Value** | `My Share * (Reap% / 100) * POOPCOIN Mcap` |
| **ROI** | `(Value - Cost) / Cost * 100%` |

Data sources:
- **Price / Mcap** — [DexScreener API](https://dexscreener.com)
- **Token balances** — [Base RPC](https://mainnet.base.org) (on-chain `balanceOf`)

## Controls

| Action | How |
|--------|-----|
| Move window | Left-click drag |
| Edit values | Click the Hold% / Reap% input fields |
| Close | Right-click anywhere or click X |

## Author

[Sanqing](https://x.com/sanqing_rx) | Built with Claude
