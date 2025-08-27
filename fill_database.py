"""
Efficient 3D Point Storage and Query using SQLite with Batch Inserts

This script demonstrates how to:
1. Generate a large set of random 3D points.
2. Store them efficiently in an in-memory SQLite database using batch inserts.
3. Apply indexing for faster queries.
4. Compare bounding box filtering with exact spherical distance calculations.
5. Backup the in-memory database to disk for persistence.

Author: Miroslav Tsintsarski
Affiliation: Discoverer Supercomputer
Email: tsintsarski.work@gmail.com
Date: 27 August 2025
"""




from __future__ import annotations
import sqlite3
import time
from pathlib import Path
from typing import Iterable, Tuple
import numpy as np


class PointDB:
    def __init__(self, db_path: str | None = None):
        """"
        If db_path is None we work in the memory. Otherwise we work with a file.
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

        self.cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_xyz ON points (x, y, z)"""
        )

        self.conn.commit()

    def insert_points_batch(self, array_3d: np.ndarray, batch_size: int = 10000) -> None:
        """
        Return point on chucnks for better performance
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
    
    def query_bbox(self, xmin: float, xmax: float,
                         ymin: float, ymax: float,
                         zmin: float, zmax: float) -> Iterable[Tuple[float, float, float]]:
        
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
        Sphere search 
        """

        x0, y1, z2 = center
        self.cur.execute(
            """
            SELECT x, y, z FROM points
            WHERE (x - ?) * (x - ?) + (y - ?) * (y - ?) + (z - ?) * (z - ?) <= ? * ?
            """,
            (x0, x0, y1, y1, z2, z2, radius, radius)
        )
        return self.cur.fetchall()
    
    def backup_to(self, out_path: str | Path) -> None:
        """
        Back up the database to a file
        """
        with sqlite3.connect(str(out_path)) as db_backup:
            self.conn.backup(db_backup)
    
    def close(self) -> None:
        self.conn.close()


if __name__ == "__main__":
    start_time = time.time()

    # Creating a in-memory database
    db = PointDB()
    db.init_schema()

    # Generating random 3D points
    array_3d = np.random.rand(1_000_000, 3) * (100.0, 100.0, 100.0)

    # Inserting points into the database in batches
    db.insert_points_batch(array_3d, batch_size=10_000)

    radius  = 5.0
    point = (50.0, 50.0, 50.0)

    bbox_rows = db.query_bbox(45.0, 55.0, 45.0, 55.0, 45.0, 55.0)
    ball_rows = db.query_ball(point, radius)

    for row in bbox_rows[:10]:
        print("BBox:", row)

    # Backup the in-memory database to a file
    db.backup_to("points_backup.db")

    db.close()

    total_time = time.time() - start_time
    print(f"Total time: {total_time:.2f} seconds")