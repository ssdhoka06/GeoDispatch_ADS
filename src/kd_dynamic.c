#include <stdlib.h>
#include "kd.h"

// Tree is sorted by coordinates, not by ID, so we have to walk everything
void kd_delete(kdnode_t *root, int point_id)
{
    if (root == NULL) return;
    if (root->point.id == point_id) {
        root->deleted = 1;
        return;
    }
    kd_delete(root->left,  point_id);
    kd_delete(root->right, point_id);
}

static void count_nodes(kdnode_t *node, int *total, int *dead)
{
    if (node == NULL) return;
    (*total)++;
    if (node->deleted) (*dead)++;
    count_nodes(node->left,  total, dead);
    count_nodes(node->right, total, dead);
}

double kd_dead_ratio(kdnode_t *root)
{
    if (root == NULL) return 0.0;
    int total = 0, dead = 0;
    count_nodes(root, &total, &dead);
    return (double)dead / total;
}

// Walk down using the same axis logic as search, new leaf alternates axis from parent
void kd_insert(kdnode_t **root, point_t p)
{
    kdnode_t **curr = root;
    int next_axis = 0;

    while (*curr != NULL) {
        int axis       = (*curr)->axis;
        double node_val = (axis == 0) ? (*curr)->point.x : (*curr)->point.y;
        double new_val  = (axis == 0) ? p.x : p.y;
        next_axis = axis ^ 1;
        curr = (new_val < node_val) ? &(*curr)->left : &(*curr)->right;
    }

    kdnode_t *node = (kdnode_t *)malloc(sizeof(kdnode_t));
    node->point   = p;
    node->axis    = next_axis;
    node->deleted = 0;
    node->left    = NULL;
    node->right   = NULL;
    *curr = node;
}

static int count_total(kdnode_t *node)
{
    if (node == NULL) return 0;
    return 1 + count_total(node->left) + count_total(node->right);
}

static void collect_live(kdnode_t *node, point_t *buf, int *n)
{
    if (node == NULL) return;
    if (!node->deleted) buf[(*n)++] = node->point;
    collect_live(node->left,  buf, n);
    collect_live(node->right, buf, n);
}

void kd_rebalance(kdnode_t **root)
{
    if (root == NULL || *root == NULL) return;

    int total    = count_total(*root);
    point_t *buf = (point_t *)malloc(sizeof(point_t) * total);
    int n        = 0;

    collect_live(*root, buf, &n);
    kd_free(*root);
    *root = (n > 0) ? kd_build(buf, n) : NULL;

    free(buf);
}
