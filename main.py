import argparse
import sys
import time
from dataclasses import dataclass
from typing import Optional, Tuple

import numpy as np
import pyautogui
import pygame
import tkinter as tk


@dataclass(frozen=True)
class MonitorConfig:
    region: Tuple[int, int, int, int]
    interval: float
    pixel_threshold: int
    change_ratio: float
    alarm_file: str
    alarm_cooldown: float


class ScreenRegionSelector:
    """Allow users to drag-select an on-screen rectangle."""

    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.attributes("-fullscreen", True)
        self.root.attributes("-alpha", 0.25)
        self.root.attributes("-topmost", True)
        self.root.configure(bg="black")
        self.root.title("Select capture area")

        self.start_x = 0
        self.start_y = 0
        self.rect_id: Optional[int] = None
        self.selection: Optional[Tuple[int, int, int, int]] = None

        self.canvas = tk.Canvas(self.root, cursor="cross", bg="gray20", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        self.canvas.create_text(
            24,
            24,
            anchor="nw",
            text="Click and drag to select capture area. Press ESC to cancel.",
            fill="white",
            font=("Arial", 14, "bold"),
        )

        self.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        self.root.bind("<Escape>", self._on_cancel)

    def _on_press(self, event: tk.Event) -> None:
        self.start_x, self.start_y = event.x, event.y
        if self.rect_id is not None:
            self.canvas.delete(self.rect_id)
        self.rect_id = self.canvas.create_rectangle(
            self.start_x,
            self.start_y,
            self.start_x,
            self.start_y,
            outline="red",
            width=2,
        )

    def _on_drag(self, event: tk.Event) -> None:
        if self.rect_id is not None:
            self.canvas.coords(self.rect_id, self.start_x, self.start_y, event.x, event.y)

    def _on_release(self, event: tk.Event) -> None:
        x1, y1 = self.start_x, self.start_y
        x2, y2 = event.x, event.y
        left, top = min(x1, x2), min(y1, y2)
        width, height = abs(x2 - x1), abs(y2 - y1)

        if width < 5 or height < 5:
            print("Selection too small, please try again.")
            return

        self.selection = (left, top, width, height)
        self.root.destroy()

    def _on_cancel(self, _: tk.Event) -> None:
        self.selection = None
        self.root.destroy()

    def select(self) -> Optional[Tuple[int, int, int, int]]:
        self.root.mainloop()
        return self.selection


class ScreenChangeMonitor:
    def __init__(self, config: MonitorConfig) -> None:
        self.config = config
        pygame.mixer.init()
        self.sound = pygame.mixer.Sound(config.alarm_file)

    def _capture(self) -> np.ndarray:
        image = pyautogui.screenshot(region=self.config.region)
        return np.array(image)

    def _change_ratio(self, prev: np.ndarray, curr: np.ndarray) -> float:
        diff = np.abs(curr.astype(np.int16) - prev.astype(np.int16))
        per_pixel_max = diff.max(axis=2)
        changed_pixels = np.count_nonzero(per_pixel_max >= self.config.pixel_threshold)
        total_pixels = per_pixel_max.size
        return changed_pixels / total_pixels

    def run(self) -> None:
        print(f"Monitoring region {self.config.region}...")
        previous = self._capture()

        try:
            while True:
                time.sleep(self.config.interval)
                current = self._capture()
                ratio = self._change_ratio(previous, current)

                if ratio >= self.config.change_ratio:
                    print(f"Change detected ({ratio:.2%} pixels changed). Playing alarm.")
                    self.sound.play()
                    time.sleep(self.config.alarm_cooldown)
                else:
                    print(f"No significant change ({ratio:.2%}).")

                previous = current
        except KeyboardInterrupt:
            print("\nStopped monitoring.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Detect changes in a selected screen area.")
    parser.add_argument(
        "--region",
        type=int,
        nargs=4,
        metavar=("LEFT", "TOP", "WIDTH", "HEIGHT"),
        help="Capture region, e.g. --region 0 650 200 150",
    )
    parser.add_argument("--select", action="store_true", help="Interactively select the capture area.")
    parser.add_argument("--interval", type=float, default=3.0, help="Seconds between captures.")
    parser.add_argument(
        "--pixel-threshold",
        type=int,
        default=25,
        help="Per-pixel RGB delta threshold to count as changed (0-255).",
    )
    parser.add_argument(
        "--change-ratio",
        type=float,
        default=0.02,
        help="Required ratio of changed pixels before alarm triggers (0.0-1.0).",
    )
    parser.add_argument("--alarm-file", default="alarm.wav", help="Sound file played on change.")
    parser.add_argument(
        "--alarm-cooldown",
        type=float,
        default=2.0,
        help="Seconds to wait after alarm trigger.",
    )
    return parser.parse_args()


def get_region(args: argparse.Namespace) -> Tuple[int, int, int, int]:
    if args.select:
        region = ScreenRegionSelector().select()
        if not region:
            print("No region selected.")
            sys.exit(1)
        return region

    if args.region:
        return tuple(args.region)

    return 0, 650, 200, 150


def main() -> None:
    args = parse_args()
    region = get_region(args)
    config = MonitorConfig(
        region=region,
        interval=max(args.interval, 0.1),
        pixel_threshold=min(max(args.pixel_threshold, 0), 255),
        change_ratio=min(max(args.change_ratio, 0.0), 1.0),
        alarm_file=args.alarm_file,
        alarm_cooldown=max(args.alarm_cooldown, 0.0),
    )

    monitor = ScreenChangeMonitor(config)
    monitor.run()


if __name__ == "__main__":
    main()
