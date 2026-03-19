/*
 * voronoi.h — DCEL type definitions and Voronoi function declarations
 *
 * P3 owns voronoi_build(), dcel_neighbours(), voronoi_free(), voronoi_insert_site().
 * P4 appends clip_to_bbox(), cell_area(), compute_all_areas(), flag_underserved().
 *
 * STUB: P3 will replace the function bodies in voronoi.c.
 *       The struct definitions below are the agreed interface contract.
 */
#ifndef VORONOI_H
#define VORONOI_H

#include "kd.h"   /* point_t */

/* ── DCEL structs (Section 10 of the context doc) ────────────── */

typedef struct vertex {
    double x, y;
    struct half_edge *incident_edge;
} vertex_t;

typedef struct half_edge {
    vertex_t          *origin;
    struct half_edge  *twin;
    struct half_edge  *next;
    struct half_edge  *prev;
    struct face       *face;
    int                is_infinite;
} half_edge_t;

typedef struct face {
    int           site_id;
    half_edge_t  *outer_edge;
    double        area;           /* computed by P4's cell_area()        */
    int           is_underserved; /* set by P4's flag_underserved()      */
} face_t;

typedef struct dcel {
    vertex_t    **vertices;  int nv;
    half_edge_t **edges;     int ne;
    face_t      **faces;     int nf;
} dcel_t;

/* ── P3 functions (voronoi.c) ────────────────────────────────── */

dcel_t  *voronoi_build(point_t *sites, int n);
face_t **dcel_neighbours(dcel_t *d, int site_id, int *out_count);
void     voronoi_free(dcel_t *d);
void     voronoi_insert_site(dcel_t *d, point_t new_site);

/* ── P4 functions (geometry.c) ───────────────────────────────── */

void   clip_to_bbox(dcel_t *d, double xmin, double ymin, double xmax, double ymax);
double cell_area(dcel_t *d, int face_id);
void   compute_all_areas(dcel_t *d);
int   *flag_underserved(dcel_t *d, double threshold, int *out_count);

#endif /* VORONOI_H */
