#include <stdio.h>
#include <stdlib.h>
#include "kd.h"
#include "voronoi.h"

static int passed = 0, failed = 0;

static void check(int ok, const char *name)
{
    if (ok) { printf("  PASS  %s\n", name); passed++; }
    else    { printf("  FAIL  %s\n", name); failed++; }
}

// Test dataset:
//   (1,1) id=0    (4,4) id=1    (7,2) id=2    (2,8) id=3

static point_t pts[] = {
    {1.0, 1.0, 0},
    {4.0, 4.0, 1},
    {7.0, 2.0, 2},
    {2.0, 8.0, 3}
};

static void test_build_and_search(void)
{
    printf("\n[kd_build / kd_nearest / kd_knn]\n");

    kdnode_t *root = kd_build(pts, 4);
    check(root != NULL, "kd_build returns non-NULL");

    point_t q = {3.9, 4.1, -1};

    point_t r = kd_nearest(root, q);
    printf("  nearest to (3.9,4.1) -> id=%d\n", r.id);
    check(r.id == 1, "nearest to (3.9,4.1) is id=1 (4,4)");
    check(kd_nearest(root, (point_t){6.9, 2.1, -1}).id == 2, "nearest to (6.9,2.1) is id=2");
    check(kd_nearest(root, (point_t){0.5, 0.5, -1}).id == 0, "nearest to (0.5,0.5) is id=0");

    int count = 0;
    point_t *knn = kd_knn(root, q, 3, &count);
    printf("  3-NN to (3.9,4.1): ");
    for (int i = 0; i < count; i++) printf("id=%d ", knn[i].id);
    printf("\n");
    check(count == 3,    "kd_knn returns 3 results");
    check(knn[0].id == 1, "knn[0] is nearest (id=1)");
    free(knn);

    int count2 = 0;
    point_t *knn2 = kd_knn(root, q, 10, &count2);
    check(count2 == 4, "kd_knn with k>n returns exactly n results");
    free(knn2);

    kd_free(root);
}

static void test_delete_and_ratio(void)
{
    printf("\n[kd_delete / kd_dead_ratio]\n");

    kdnode_t *root = kd_build(pts, 4);
    point_t q = {3.9, 4.1, -1};

    kd_delete(root, 1);
    point_t r = kd_nearest(root, q);
    printf("  nearest after deleting id=1 -> id=%d\n", r.id);
    check(r.id != 1, "deleted node not returned by kd_nearest");

    kd_delete(root, 999);  // non-existent
    check(1, "deleting non-existent id doesn't crash");

    double ratio = kd_dead_ratio(root);
    printf("  dead_ratio after 1 delete: %.2f\n", ratio);
    check(ratio > 0.24 && ratio < 0.26, "dead_ratio = 0.25 (1 of 4 deleted)");

    kd_delete(root, 0);
    kd_delete(root, 2);
    kd_delete(root, 3);
    check(kd_dead_ratio(root) > 0.99, "dead_ratio = 1.0 when all deleted");
    check(kd_nearest(root, q).id == -1, "kd_nearest on fully-deleted tree returns id=-1");

    kd_free(root);
}

static void test_insert(void)
{
    printf("\n[kd_insert]\n");

    kdnode_t *root = kd_build(pts, 4);
    point_t q = {3.9, 4.1, -1};

    // (3.85, 4.05) is clearly closer to q than id=1 at (4,4)
    kd_insert(&root, (point_t){3.85, 4.05, 10});
    point_t r = kd_nearest(root, q);
    printf("  nearest after inserting (3.85,4.05,id=10) -> id=%d\n", r.id);
    check(r.id == 10, "inserted point becomes new nearest");

    // insert into empty tree
    kdnode_t *empty = NULL;
    kd_insert(&empty, (point_t){5.0, 5.0, 99});
    check(empty != NULL, "kd_insert into NULL creates root");
    check(kd_nearest(empty, q).id == 99, "sole inserted node found by kd_nearest");
    kd_free(empty);

    kd_free(root);
}

static void test_rebalance(void)
{
    printf("\n[kd_rebalance]\n");

    kdnode_t *root = kd_build(pts, 4);

    kd_delete(root, 0);
    kd_delete(root, 2);
    check(kd_dead_ratio(root) > 0.49, "dead_ratio = 0.5 before rebalance");

    kd_rebalance(&root);
    check(root != NULL, "rebalance returns non-NULL tree");
    check(kd_dead_ratio(root) < 0.01, "dead_ratio = 0.0 after rebalance");

    check(kd_nearest(root, (point_t){4.0, 4.0, -1}).id == 1, "id=1 present after rebalance");
    check(kd_nearest(root, (point_t){2.0, 8.0, -1}).id == 3, "id=3 present after rebalance");

    int id = kd_nearest(root, (point_t){1.0, 1.0, -1}).id;
    check(id != 0 && id != 2, "deleted ids 0,2 absent after rebalance");

    // rebalancing a fully-deleted tree should give NULL, not crash
    kdnode_t *all_dead = kd_build(pts, 4);
    kd_delete(all_dead, 0); kd_delete(all_dead, 1);
    kd_delete(all_dead, 2); kd_delete(all_dead, 3);
    kd_rebalance(&all_dead);
    check(all_dead == NULL, "rebalancing all-deleted tree yields NULL");

    // ── Task 4 test: voronoi_build ──
    dcel_t *dcel = voronoi_build(pts, 4);
    printf("voronoi_build output: %d vertices, %d edges, %d faces\n", dcel->nv, dcel->ne, dcel->nf);
    
    int nbr_count = 0;
    face_t** nbrs = dcel_neighbours(dcel, 0, &nbr_count);
    printf("dcel_neighbours for site 0: %d neighbours\n", nbr_count);
    free(nbrs);
    voronoi_free(dcel);

    kd_free(root);
}

int main(void)
{
    printf("=== GeoDispatch KD-Tree Tests ===\n");

    test_build_and_search();
    test_delete_and_ratio();
    test_insert();
    test_rebalance();

    printf("\n%d passed, %d failed\n\n", passed, failed);
    return (failed == 0) ? 0 : 1;
}
