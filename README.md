# 3D Point Database with SQLite

This project demonstrates how to efficiently generate, store, and query millions of 3D points using **SQLite** and **NumPy**.
It highlights the performance benefits of **batch inserts** and compares two query strategies:

* **Bounding box pre-selection** using SQL range queries.
* **Exact spherical search** based on distance calculation.

## Features

* Create an in-memory SQLite database or save it to disk.
* Insert millions of 3D points efficiently in batches.
* Perform fast bounding box queries.
* Perform exact radius-based (sphere) searches.
* Backup the in-memory database to a persistent file.

## Requirements

* Python 3.10+
* NumPy

## Usage

Run the script directly:

```bash
python fill_database.py
```

## Benchmarks

We ran a sweep with **1M, 5M and 10M points** and radii **5, 10, 20**.
Each run measures generation, batch insert, bounding-box query, and exact sphere query.

### Results

| Points     | Radius | Generate (s) | Insert (s) | BBox Time (s) | BBox Hits | Sphere Time (s) | Sphere Hits |
| ---------- | ------ | ------------ | ---------- | ------------- | --------- | --------------- | ----------- |
| 1,000,000  | 5      | 0.033        | 3.303      | 0.007         | 1,030     | 0.183           | 545         |
| 1,000,000  | 10     | 0.027        | 3.328      | 0.024         | 8,037     | 0.182           | 4,262       |
| 1,000,000  | 20     | 0.025        | 3.282      | 0.078         | 63,791    | 0.195           | 33,536      |
| 5,000,000  | 5      | 0.106        | 17.754     | 0.037         | 4,922     | 0.900           | 2,659       |
| 5,000,000  | 10     | 0.110        | 17.903     | 0.102         | 39,715    | 0.899           | 20,840      |
| 5,000,000  | 20     | 0.125        | 17.870     | 0.347         | 319,466   | 0.994           | 167,283     |
| 10,000,000 | 5      | 0.227        | 37.757     | 0.076         | 9,961     | 1.849           | 5,266       |
| 10,000,000 | 10     | 0.288        | 38.603     | 0.197         | 79,841    | 1.796           | 41,822      |
| 10,000,000 | 20     | 0.208        | 43.637     | 0.741         | 639,778   | 3.536           | 335,155     |

### Observations

* **Insert time** scales \~linearly with number of points (3.3s → 17.8s → 43.6s).
* **BBox query** is very fast (ms level), even with tens of millions of points, thanks to the `(x,y,z)` index.
* **Sphere query** cost grows with radius (hits ∝ r³), but stays under 4s even for 10M points and radius 20.
* Combining **BBox pre-filter → Sphere exact check** is the most efficient approach.
