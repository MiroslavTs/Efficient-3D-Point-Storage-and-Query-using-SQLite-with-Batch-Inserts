"""
Efficient 3D Point Storage and Query using SQLite with Batch Inserts

This script demonstrates how to:
1. Generate a large set of random 3D points.
2. Store them efficiently in an in-memory SQLite database using batch inserts.
3. Apply indexing for faster queries.
4. Compare bounding box filtering with exact spherical distance calculations.
5. Backup the in-memory database to disk for persistence.

Author: Miroslav Tsintsarski
Affiliation: Discoverer Petascale Supercomputer (Sofia, Bulgaria)
Email: tsintsarski.work@gmail.com
Date: 27 August 2025
"""

from __future__ import annotations
import argparse
import sqlite3
import time
from pathlib import Path
from typing import Iterable, Tuple
import numpy as np


class PointDB:
    def __init__(self, db_path: str | None = None):
        """
        If db_path is None we use an in-memory database (':memory:').
        Otherwise we use a file-backed database.
        """
        self.db_path = db_path or ":memory:"
        self.conn = sqlite3.connect(self.db_path)
        self.cur = self.conn.cursor()

    def init_schema(self) -> None:
        self.cur.execute(
            """
            CREATE TABLE IF NOT EXISTS points (
                x REAL NOT NULL,
                y REAL NOT NULL,
                z REAL NOT NULL
            );
            """
        )
        self.cur.execute("CREATE INDEX IF NOT EXISTS idx_xyz ON points (x, y, z)")
        self.conn.commit()

    def insert_points_batch(self, array_3d: np.ndarray, batch_size: int = 10_000) -> None:
        """
        Insert points in chunks (batches) for better performance.
        Expects shape: (N, 3) => columns [x, y, z].
        """
        n = array_3d.shape[0]
        for start in range(0, n, batch_size):
            end = min(start + batch_size, n)
            batch = array_3d[start:end]
            self.cur.executemany(
                "INSERT INTO points (x, y, z) VALUES (?, ?, ?)",
                map(tuple, batch)
            )
        self.conn.commit()

    def query_bbox(
        self, xmin: float, xmax: float,
        ymin: float, ymax: float,
        zmin: float, zmax: float
    ) -> Iterable[Tuple[float, float, float]]:
        self.cur.execute(
            """
            SELECT x, y, z FROM points
            WHERE x BETWEEN ? AND ?
              AND y BETWEEN ? AND ?
              AND z BETWEEN ? AND ?
            """,
            (xmin, xmax, ymin, ymax, zmin, zmax)
        )
        return self.cur.fetchall()

    def query_ball(self, center: Tuple[float, float, float], radius: float):
        """
        Exact spherical (radius) search.
        """
        x0, y0, z0 = center  # fixed: y0, z0 (not y1, z2)
        self.cur.execute(
            """
            SELECT x, y, z FROM points
            WHERE (x - ?) * (x - ?) + (y - ?) * (y - ?) + (z - ?) * (z - ?) <= ? * ?
            """,
            (x0, x0, y0, y0, z0, z0, radius, radius)
        )
        return self.cur.fetchall()

    def backup_to(self, out_path: str | Path) -> None:
        """
        Backup the current database to a file.
        """
        with sqlite3.connect(str(out_path)) as dst:
            self.conn.backup(dst)

    def close(self) -> None:
        self.conn.close()


def demo():
    start_time = time.time()
    db = PointDB()  # in-memory
    db.init_schema()

    # Reproducible RNG
    rng = np.random.default_rng(42)
    array_3d = rng.random((1_000_000, 3)) * (100.0, 100.0, 100.0)

    db.insert_points_batch(array_3d, batch_size=10_000)

    radius = 5.0
    point = (50.0, 50.0, 50.0)

    bbox_rows = db.query_bbox(45.0, 55.0, 45.0, 55.0, 45.0, 55.0)
    ball_rows = db.query_ball(point, radius)

    for row in bbox_rows[:10]:
        print("BBox:", row)
    for row in ball_rows[:10]:
        print("Sphere:", row)

    db.backup_to("points_backup.db")
    db.close()

    print(f"Total time: {time.time() - start_time:.2f} seconds")


# ===== Benchmarks =====
def _timer():
    t0 = time.perf_counter()
    def lap() -> float:
        return time.perf_counter() - t0
    return lap

def benchmark(n_points=1_000_000, batch_size=10_000,
              scale=(100.0, 100.0, 100.0),
              center=(50.0, 50.0, 50.0), radius=5.0):
    print(f"\n--- Benchmark start ---")
    print(f"Points: {n_points:,} | Batch size: {batch_size} | Center: {center} | Radius: {radius}")
    print(f"Scale: {scale}")

    # Data generation
    lap = _timer()
    rng = np.random.default_rng(42)
    array_3d = rng.random((n_points, 3)) * scale
    t_gen = lap()
    print(f"[gen] generated {n_points:,} points in {t_gen:.3f}s")

    # DB + schema
    db = PointDB()
    db.init_schema()

    # Insert (batch)
    lap = _timer()
    db.insert_points_batch(array_3d, batch_size=batch_size)
    t_insert = lap()
    print(f"[insert] batch={batch_size:,} -> {t_insert:.3f}s")

    # BBox query
    xmin, xmax = center[0] - radius, center[0] + radius
    ymin, ymax = center[1] - radius, center[1] + radius
    zmin, zmax = center[2] - radius, center[2] + radius

    lap = _timer()
    bbox_rows = db.query_bbox(xmin, xmax, ymin, ymax, zmin, zmax)
    t_bbox = lap()
    print(f"[bbox] rows={len(bbox_rows):,} -> {t_bbox:.3f}s")

    # Sphere query
    lap = _timer()
    sphere_rows = db.query_ball(center, radius)
    t_sphere = lap()
    print(f"[sphere] rows={len(sphere_rows):,} -> {t_sphere:.3f}s")

    db.backup_to("points_backup.db")
    db.close()

    print("\n--- Benchmark summary ---")
    print(f"generate : {t_gen:.3f}s")
    print(f"insert   : {t_insert:.3f}s  (batch={batch_size:,})")
    print(f"bbox     : {t_bbox:.3f}s  (hits={len(bbox_rows):,})")
    print(f"sphere   : {t_sphere:.3f}s (hits={len(sphere_rows):,})")
    print("--- Benchmark end ---\n")

def benchmark_sweep():
    configs = [
        (1_000_000, 5),
        (1_000_000, 10),
        (1_000_000, 20),
        (5_000_000, 5),
        (5_000_000, 10),
        (5_000_000, 20),
        (10_000_000, 5),
        (10_000_000, 10),
        (10_000_000, 20),
    ]
    for n_points, radius in configs:
        benchmark(
            n_points=n_points,
            batch_size=10_000,               
            scale=(100.0, 100.0, 100.0),
            center=(50.0, 50.0, 50.0),
            radius=radius,
        )


def main():
    parser = argparse.ArgumentParser(description="3D point storage and query demo/benchmark.")
    parser.add_argument("-b", "--benchmark", action="store_true",
                        help="Run benchmark instead of the simple demo.")
    parser.add_argument("-s", "--sweep", action="store_true",
                        help="Run a sweep of benchmarks with different parameters.")
    args = parser.parse_args()


    if args.sweep:
        benchmark_sweep()
    elif args.benchmark:
        benchmark()
    else:
        demo()


if __name__ == "__main__":
    main()
