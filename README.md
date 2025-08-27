# 3D Point Database with SQLite

This project demonstrates how to efficiently generate, store, and query millions of 3D points using **SQLite** and **NumPy**.  
It highlights the performance benefits of **batch inserts** and compares two query strategies:
- **Bounding box pre-selection** using SQL range queries.
- **Exact spherical search** based on distance calculation.

## Features
- Create an in-memory SQLite database or save it to disk.
- Insert millions of 3D points efficiently in batches.
- Perform fast bounding box queries.
- Perform exact radius-based (sphere) searches.
- Backup the in-memory database to a persistent file.

## Requirements
- Python 3.10+
- NumPy

## Usage
Run the script directly:

```bash
python fill_database.py
