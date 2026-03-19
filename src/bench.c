// Benchmark: KD-tree vs brute force, fresh vs degraded vs rebalanced
// Build: make bench  |  Run: ./bench

#include <stdio.h>
#include <stdlib.h>
#include <float.h>
#include <time.h>
#include "kd.h"

#define N_POINTS     10000
#define N_QUERIES    100000   // large enough to get measurable time on Windows
#define N_CORRECT    1000     // brute-force is slow, only check this many
#define COORD_RANGE  15000.0  // +-15 km, roughly Pune city radius
#define DELETE_COUNT ((int)(N_POINTS * 0.4))

static double ms(clock_t a, clock_t b)
{
    return (double)(b - a) / CLOCKS_PER_SEC * 1000.0;
}

static double rand_coord(void)
{
    return -COORD_RANGE + ((double)rand() / RAND_MAX) * 2.0 * COORD_RANGE;
}

static point_t rand_point(int id)
{
    return (point_t){ rand_coord(), rand_coord(), id };
}

static point_t brute_nearest(point_t *pts, int n, point_t q)
{
    double best_d   = DBL_MAX;
    point_t best_pt = {0, 0, -1};
    for (int i = 0; i < n; i++) {
        double dx = pts[i].x - q.x;
        double dy = pts[i].y - q.y;
        double d  = dx*dx + dy*dy;
        if (d < best_d) { best_d = d; best_pt = pts[i]; }
    }
    return best_pt;
}

int main(void)
{
    srand((unsigned)time(NULL));

    point_t *pts     = malloc(sizeof(point_t) * N_POINTS);
    point_t *queries = malloc(sizeof(point_t) * N_QUERIES);

    for (int i = 0; i < N_POINTS;  i++) pts[i]     = rand_point(i);
    for (int i = 0; i < N_QUERIES; i++) queries[i]  = rand_point(-1);

    clock_t t0, t1;

    printf("\n--- Phase 1: Build ---\n");
    t0 = clock();
    kdnode_t *root = kd_build(pts, N_POINTS);
    t1 = clock();
    printf("kd_build(%d pts): %.1f ms\n", N_POINTS, ms(t0, t1));

    printf("\n--- Phase 2: NN search (fresh tree) ---\n");

    t0 = clock();
    for (int i = 0; i < N_QUERIES; i++) {
        volatile point_t r = kd_nearest(root, queries[i]);
        (void)r;
    }
    t1 = clock();
    double kd_fresh_ms = ms(t0, t1);
    double kd_us = kd_fresh_ms * 1000.0 / N_QUERIES;

    t0 = clock();
    for (int i = 0; i < N_CORRECT; i++) {
        volatile point_t r = brute_nearest(pts, N_POINTS, queries[i]);
        (void)r;
    }
    t1 = clock();
    double bf_us = ms(t0, t1) * 1000.0 / N_CORRECT;

    int mismatches = 0;
    for (int i = 0; i < N_CORRECT; i++) {
        if (kd_nearest(root, queries[i]).id != brute_nearest(pts, N_POINTS, queries[i]).id)
            mismatches++;
    }

    printf("KD-tree:     %.3f us/query  (%d queries)\n", kd_us, N_QUERIES);
    printf("Brute force: %.3f us/query  (%d queries)\n", bf_us, N_CORRECT);
    printf("Speedup:     %.1fx\n", bf_us / kd_us);
    printf("Correctness: %d/%d [%s]\n", N_CORRECT - mismatches, N_CORRECT,
           mismatches == 0 ? "PASS" : "FAIL");

    printf("\n--- Phase 3: Degraded tree (40%% deleted) ---\n");

    t0 = clock();
    for (int i = 0; i < DELETE_COUNT; i++) kd_delete(root, i);
    t1 = clock();
    printf("kd_delete x%d: %.1f ms\n", DELETE_COUNT, ms(t0, t1));
    printf("dead_ratio: %.2f\n", kd_dead_ratio(root));

    t0 = clock();
    for (int i = 0; i < N_QUERIES; i++) {
        volatile point_t r = kd_nearest(root, queries[i]);
        (void)r;
    }
    t1 = clock();
    double kd_deg_us = ms(t0, t1) * 1000.0 / N_QUERIES;
    printf("KD-tree (degraded): %.3f us/query  (%.2fx slower)\n",
           kd_deg_us, kd_deg_us / kd_us);

    printf("\n--- Phase 4: Rebalance ---\n");
    t0 = clock();
    kd_rebalance(&root);
    t1 = clock();
    printf("kd_rebalance: %.1f ms  (live nodes: %d, dead_ratio: %.2f)\n",
           ms(t0, t1), N_POINTS - DELETE_COUNT, kd_dead_ratio(root));

    printf("\n--- Phase 5: NN search (post-rebalance) ---\n");
    t0 = clock();
    for (int i = 0; i < N_QUERIES; i++) {
        volatile point_t r = kd_nearest(root, queries[i]);
        (void)r;
    }
    t1 = clock();
    double kd_reb_us = ms(t0, t1) * 1000.0 / N_QUERIES;
    printf("KD-tree (rebalanced): %.3f us/query  (%.2fx vs fresh)\n",
           kd_reb_us, kd_reb_us / kd_us);

    printf("\n--- Summary ---\n");
    printf("Speedup vs brute force: %.1fx\n", bf_us / kd_us);
    printf("Degradation (40%% dead): %.2fx slower\n", kd_deg_us / kd_us);
    printf("Post-rebalance vs fresh: %.2fx\n\n", kd_reb_us / kd_us);

    kd_free(root);
    free(pts);
    free(queries);
    return 0;
}
