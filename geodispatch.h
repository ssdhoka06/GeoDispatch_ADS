#ifndef GEODISPATCH_H
#define GEODISPATCH_H

#include "kd.h"
#include "voronoi.h"

/* P5 — algo.c algorithms */

typedef struct {
    int site_id;
    point_t from;
    point_t to;
} facility_move_t;

typedef struct {
    int iterations_run;
    facility_move_t *moves; /* For all iterations, sequentially. Or array per iter? Spec says it returns moves per iteration. */
    /* Let's simplify: the spec says "returns per-iteration facility movements". 
       A flat array is good, Python can group by iteration. Or array of arrays. */
    int nmoves;
} lloyds_result_t;

void voronoi_incremental_update(dcel_t *d, kdnode_t *kd_root, int changed_site_id);

lloyds_result_t *run_lloyds(dcel_t **d_ptr, kdnode_t **kd_root_ptr, 
                            point_t *sites, int n, 
                            int max_iterations, double threshold);

void free_lloyds_result(lloyds_result_t *res);

/* P5 — Python Bridge Helpers */
typedef struct {
    int site_id;
    double area;
    int is_underserved;
    double *polygon_coords; /* Flat [x1, y1, x2, y2, ...] */
    int num_points;
} coverage_cell_t;

typedef struct {
    coverage_cell_t *cells;
    int ncells;
} coverage_map_t;

coverage_map_t *get_coverage_map(dcel_t *d);
void free_coverage_map(coverage_map_t *map);

#endif /* GEODISPATCH_H */
