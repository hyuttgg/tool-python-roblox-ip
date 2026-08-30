# -*- coding: utf-8 -*-
"""
Radar Dashboard — Rich Console UI
Hien thi trang thai tong hop cua tat ca Tag Roblox voi:
  - Bang trang thai live (cap nhat moi 2s)
  - Anomaly sparkline
  - Event log stream
  - Drill-down chi tiet per-tag
  - Keyboard interactive
"""

import time
import threading
from typing import Dict, List, Optional
from config.logging import setup_logger

logger = setup_logger("radar_dashboard")

# Unicode block chars cho sparkline
SPARK_CHARS = " " + chr(9601) + chr(9602) + chr(9603) + chr(9604) + chr(9605) + chr(9606) + chr(9607) + chr(9608)

# State icons
STATE_DISPLAY = {
    "NOT_RUNNING":  ("OFFLINE",       "[dim]"),
    "STARTING":     ("LOADING...",    "[cyan]"),
    "RUNNING":      ("ONLINE",        "[green]"),
    "FROZEN":       ("FROZEN",        "[yellow]"),
    "CRASHED":      ("CRASHED",       "[red]"),
    "DISCONNECTED": ("DISCONNECT",    "[red]"),
    "APP_CHANGED":  ("MODIFIED",      "[magenta]"),
    "SUSPICIOUS":   ("SUSPICIOUS",    "[yellow]"),
    "UNKNOWN":      ("UNKNOWN",       "[dim]"),
}

SEVERITY_COLORS = {
    "NORMAL":     "[green]",
    "WARNING":    "[yellow]",
    "SUSPICIOUS": "[dark_orange]",
    "CRITICAL":   "[bold red]",
}


def _sparkline(values: List[int], width: int = 30) -> str:
    """Tao sparkline tu danh sach anomaly scores."""
    if not values:
        return " " * width

    # Lay N mau cuoi cung
    data = values[-width:]
    if not data:
        return " " * width

    max_val = max(max(data), 1)
    result = []
    for v in data:
        idx = int((v / max_val) * (len(SPARK_CHARS) - 1))
        idx = min(idx, len(SPARK_CHARS) - 1)
        result.append(SPARK_CHARS[idx])

    # Pad neu chua du width
    while len(result) < width:
        result.insert(0, " ")

    return "".join(result)


def _format_uptime(seconds: float) -> str:
    """Chuyen doi so giay thanh HH:MM:SS."""
    if seconds <= 0:
        return "--:--:--"
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def _format_memory(mb: float) -> str:
    """Format memory display."""
    if mb <= 0:
        return "0MB"
    if mb >= 1024:
        return f"{mb/1024:.1f}GB"
    return f"{mb:.0f}MB"


class RadarDashboard:
    """
    Rich Console Dashboard cho Radar Monitor.
    Hien thi bang trang thai, sparkline, event log va tuong tac ban phim.
    """

    def __init__(self, engine=None):
        self._engine = engine
        self._running = False
        self._score_history: Dict[str, List[int]] = {}
        self._max_history = 60

    def _get_engine(self):
        """Lazy-load radar engine."""
        if self._engine is None:
            try:
                from monitoring.radar.engine import radar_engine
                self._engine = radar_engine
            except Exception:
                pass
        return self._engine

    def run_live(self, refresh_interval: float = 2.0) -> None:
        """
        Chay dashboard live voi Rich Live display.
        Nhan phim: [Q] Quit, [R] Refresh, [D] Detail, [H] History, [I] Integrity
        """
        try:
            from rich.console import Console
            from rich.live import Live
            from rich.table import Table
            from rich.panel import Panel
            from rich.layout import Layout
            from rich.text import Text
            from rich import box
        except ImportError:
            logger.error("Thu vien 'rich' chua duoc cai dat. Chay: pip install rich")
            self._run_fallback()
            return

        console = Console()
        self._running = True

        # Thread bat phim
        stop_event = threading.Event()
        detail_tag = [None]

        def _key_listener():
            while not stop_event.is_set():
                try:
                    import msvcrt
                    if msvcrt.kbhit():
                        key = msvcrt.getch().decode("utf-8", errors="ignore").lower()
                        if key == "q":
                            stop_event.set()
                            self._running = False
                        elif key == "i":
                            self._show_integrity(console)
                except Exception:
                    # Non-Windows fallback
                    time.sleep(0.5)

        key_thread = threading.Thread(target=_key_listener, daemon=True)
        key_thread.start()

        try:
            with Live(console=console, refresh_per_second=1, screen=False) as live:
                while self._running and not stop_event.is_set():
                    panel = self._build_panel()
                    live.update(panel)
                    time.sleep(refresh_interval)
        except KeyboardInterrupt:
            pass
        finally:
            stop_event.set()
            self._running = False

    def _build_panel(self):
        """Xay dung panel hien thi chinh."""
        from rich.table import Table
        from rich.panel import Panel
        from rich.text import Text
        from rich import box

        engine = self._get_engine()
        if not engine:
            return Panel("[red]Radar Engine chua duoc khoi tao[/red]", title="RADAR MONITOR")

        reports = engine.get_all_reports()
        uptime_str = _format_uptime(engine.uptime_sec)

        # --- Header ---
        header = Text()
        header.append("ROBLOX RADAR MONITOR v1.0\n", style="bold cyan")
        header.append(f"  Scan: {engine.scan_interval}s | Tags: {engine.tag_count} | "
                      f"Cycles: {engine.cycle_count} | Uptime: {uptime_str}\n", style="dim")

        # --- Tag Table ---
        table = Table(box=box.SIMPLE_HEAVY, show_header=True, header_style="bold white",
                      expand=True, pad_edge=False)
        table.add_column("TAG", style="bold", width=18)
        table.add_column("STATE", width=14)
        table.add_column("SCORE", justify="right", width=6)
        table.add_column("CPU", justify="right", width=8)
        table.add_column("RAM", justify="right", width=8)
        table.add_column("PING", justify="right", width=8)
        table.add_column("FPS", justify="right", width=5)
        table.add_column("UPTIME", justify="right", width=10)

        if not reports:
            table.add_row("[dim]No tags registered[/dim]", "", "", "", "", "", "", "")
        else:
            for tag_id, report in sorted(reports.items()):
                # State display
                state_label, state_color = STATE_DISPLAY.get(report.state, ("?", "[dim]"))
                state_text = f"{state_color}{state_label}[/]"

                # Score display
                sev_color = SEVERITY_COLORS.get(report.severity, "[white]")
                score_text = f"{sev_color}{report.anomaly_score}[/]"

                # Metrics
                cpu_text = f"{report.filtered_cpu:.1f}%" if report.process_alive else "-"
                ram_text = _format_memory(report.filtered_ram) if report.process_alive else "-"
                ping_text = f"{report.filtered_ping:.0f}ms" if report.filtered_ping > 0 else "-"
                fps_text = str(int(report.filtered_fps)) if report.filtered_fps > 0 else "-"
                uptime_text = _format_uptime(report.uptime_sec)

                table.add_row(
                    tag_id, state_text, score_text,
                    cpu_text, ram_text, ping_text, fps_text, uptime_text
                )

                # Luu score history cho sparkline
                history = self._score_history.setdefault(tag_id, [])
                history.append(report.anomaly_score)
                if len(history) > self._max_history:
                    self._score_history[tag_id] = history[-self._max_history:]

        # --- Sparkline ---
        sparkline_section = Text()
        sparkline_section.append("\n  Anomaly Timeline ", style="bold dim")
        for tag_id, scores in self._score_history.items():
            spark = _sparkline(scores, width=40)
            sev = "green"
            if scores and scores[-1] >= 70:
                sev = "red"
            elif scores and scores[-1] >= 40:
                sev = "yellow"
            elif scores and scores[-1] >= 20:
                sev = "dark_orange"
            sparkline_section.append(f"\n  {tag_id:18s} ", style="dim")
            sparkline_section.append(spark, style=sev)

        # --- Events ---
        events_section = Text()
        events_section.append("\n\n  Recent Events ", style="bold dim")

        all_transitions = []
        for tag_id, report in reports.items():
            for entry in report.state_history[-5:]:
                all_transitions.append((entry.get("time", 0), tag_id, entry))

        all_transitions.sort(key=lambda x: x[0], reverse=True)

        if not all_transitions:
            events_section.append("\n  [dim]No events yet[/dim]")
        else:
            for ts, tid, entry in all_transitions[:8]:
                t_str = time.strftime("%H:%M:%S", time.localtime(ts))
                from_s = entry.get("from", "?")
                to_s = entry.get("to", "?")
                score = entry.get("score", 0)
                events_section.append(f"\n  [{t_str}] ", style="dim")
                events_section.append(f"{tid} ", style="bold")
                events_section.append(f"{from_s} -> {to_s} ", style="cyan")
                events_section.append(f"(score={score})", style="dim")

        # --- Footer ---
        footer = Text()
        footer.append("\n\n  [Q] Quit  [I] Integrity Check", style="dim")

        # Combine
        content = Text()
        content.append_text(header)
        content.append_text(Text.from_ansi(""))

        return Panel(
            Text.assemble(header, "\n", table, sparkline_section, events_section, footer),
            title="[bold cyan]ROBLOX RADAR MONITOR[/bold cyan]",
            border_style="cyan",
            padding=(1, 2),
        )

    def _show_integrity(self, console) -> None:
        """Hien thi ket qua kiem tra integrity."""
        try:
            from monitoring.radar.integrity import IntegrityMonitor
            from rich.panel import Panel

            monitor = IntegrityMonitor()
            result = monitor.check_integrity()

            lines = [
                f"EXE Found: {result.exe_found}",
                f"Path: {result.exe_path}",
                f"Version: {result.version}",
                f"Current Hash: {result.current_hash[:32]}..." if result.current_hash else "Hash: N/A",
                f"Baseline Hash: {result.baseline_hash[:32]}..." if result.baseline_hash else "Baseline: N/A",
                f"Match: {result.match}",
                f"Details: {result.details}",
            ]
            console.print(Panel("\n".join(lines), title="[bold]Integrity Check[/bold]", border_style="magenta"))
        except Exception as e:
            console.print(f"[red]Integrity check error: {e}[/red]")

    def _run_fallback(self) -> None:
        """Fallback dashboard khi khong co Rich."""
        engine = self._get_engine()
        if not engine:
            print("Radar Engine chua khoi tao.")
            return

        print("=" * 60)
        print("  ROBLOX RADAR MONITOR (Text Fallback)")
        print("=" * 60)

        self._running = True
        try:
            while self._running:
                reports = engine.get_all_reports()
                print(f"\n--- Cycle {engine.cycle_count} | Tags: {engine.tag_count} ---")
                for tag_id, report in sorted(reports.items()):
                    print(
                        f"  {tag_id:18s} | {report.state:14s} | "
                        f"Score={report.anomaly_score:3d} [{report.severity:10s}] | "
                        f"CPU={report.filtered_cpu:5.1f}% | "
                        f"RAM={_format_memory(report.filtered_ram):6s} | "
                        f"Ping={report.filtered_ping:5.0f}ms | "
                        f"FPS={report.filtered_fps:3.0f}"
                    )
                time.sleep(2.0)
        except KeyboardInterrupt:
            self._running = False
            print("\nRadar Dashboard stopped.")

    def get_summary_text(self) -> str:
        """Tra ve van ban tom tat trang thai (cho controller menu)."""
        engine = self._get_engine()
        if not engine:
            return "Radar Engine: NOT INITIALIZED"

        reports = engine.get_all_reports()
        if not reports:
            return f"Radar Engine: ACTIVE | Tags: 0 | Cycles: {engine.cycle_count}"

        states = {}
        for report in reports.values():
            states[report.state] = states.get(report.state, 0) + 1

        parts = [f"Tags: {len(reports)}"]
        for state, count in sorted(states.items()):
            parts.append(f"{state}: {count}")
        parts.append(f"Cycles: {engine.cycle_count}")

        return "Radar: " + " | ".join(parts)


# Singleton
radar_dashboard = RadarDashboard()
