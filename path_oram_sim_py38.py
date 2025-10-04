
# -*- coding: utf-8 -*-
"""
Path ORAM simulation (Python 3.8 compatible version).
Implements read-path eviction Path ORAM per Assignment 2 (Secure Cloud Computing).
"""

import argparse
import math
import random
import sys
from collections import defaultdict
from typing import Optional

#converts (level,index) into an array index in the flat representation of tree
def node_index(level: int, idx: int) -> int:
    return (1 << level) - 1 + idx

#returns a list of nodes from root to leaf_x (not the buckets of those nodes!)
def path_nodes(L: int, leaf_x: int):
    nodes = []
    for l in range(0, L + 1):
        idx = leaf_x >> (L - l) if l > 0 else 0
        nodes.append((l, idx))
    return nodes

#checks if 2 leaves have the same ancestor at requested level 'level'
def same_subtree_at_level(L: int, leaf_a: int, leaf_b: int, level: int) -> bool:
    if level == 0:
        return True
    return (leaf_a >> (L - level)) == (leaf_b >> (L - level))


class PathORAM:
    #initialize all required variables and the tree
    def __init__(self, N: int, Z: int, L: int, seed: Optional[int] = None):
        assert N > 0
        assert Z > 0
        assert L >= 1 and (1 << L) >= N
        self.N = N
        self.Z = Z
        self.L = L
        self.num_nodes = (1 << (L + 1)) - 1
        self.tree = [list() for _ in range(self.num_nodes)]
        if seed is not None:
            random.seed(seed)
        self.leaf_space = 1 << L  #number of leaf nodes (< num_nodes)
        self.position = [random.randrange(self.leaf_space) for _ in range(N)] #position of each block is also randomized
        self.stash = {}
        self._initial_place_blocks()

    #returns the bucket stored at level 'level' and index 'idx'
    def _bucket(self, level: int, idx: int) -> list:
        return self.tree[node_index(level, idx)]

    #initialization of blocks into random buckets but still adhering to position table
    def _initial_place_blocks(self):
        order = list(range(self.N))
        random.shuffle(order) # to sample blocks randomly to be placed (this is randomization on top of position randomization)
        for a in order:
            leaf = self.position[a]
            placed = False
            for l in range(self.L, -1, -1):
                idx = leaf >> (self.L - l) if l > 0 else 0 #this does the bitshift to move up from child node to parent node index
                bucket = self._bucket(l, idx)
                if len(bucket) < self.Z:
                    bucket.append((a, a)) # here (a,a) corresponds to (block_ID, data) initial data is kept the same as block_id cuz we don't care about the data
                    placed = True
                    break
            if not placed:
                self.stash[a] = a


    def access(self, op: str, a: int, new_data=None):
        assert 0 <= a < self.N
        assert op in ("read", "write")
        x = self.position[a]
        self.position[a] = random.randrange(self.leaf_space)

        for (l, idx) in path_nodes(self.L, x):
            bucket = self._bucket(l, idx)
            for (bid, bdata) in bucket:
                self.stash[bid] = bdata
            bucket.clear()

        old_data = self.stash.get(a, a)
        if op == "write":
            self.stash[a] = new_data

        for l in range(self.L, -1, -1):
            idx = x >> (self.L - l) if l > 0 else 0
            bucket = self._bucket(l, idx)
            if len(bucket) >= self.Z:
                continue
            capacity = self.Z - len(bucket)
            chosen = []
            for bid in list(self.stash.keys()):
                if same_subtree_at_level(self.L, self.position[bid], x, l):
                    chosen.append(bid)
                    if len(chosen) == capacity:
                        break
            for bid in chosen:
                bucket.append((bid, self.stash.pop(bid)))
        return old_data

    def simulate(self, total_ops: int, warmup_ops: int, record_file: Optional[str] = None):
        assert total_ops > warmup_ops >= 0
        versions = [0] * self.N
        recorded_stash_sizes = []
        block = 0

        for t in range(total_ops):
            op = "write" if random.getrandbits(1) else "read"
            a = block
            block += 1
            if block == self.N:
                block = 0

            if op == "write":
                versions[a] += 1
                self.access("write", a, (a, versions[a]))
            else:
                _ = self.access("read", a, None)

            if t >= warmup_ops:
                recorded_stash_sizes.append(len(self.stash))

        max_stash = max(recorded_stash_sizes) if recorded_stash_sizes else 0
        tail_counts = {}
        s = len(recorded_stash_sizes)
        hist = [0] * (max_stash + 1)
        for val in recorded_stash_sizes:
            hist[val] += 1
        suffix_ge = [0] * (max_stash + 2)
        running = 0
        for k in range(max_stash, -1, -1):
            running += hist[k]
            suffix_ge[k] = running
        for i in range(0, max_stash + 1):
            tail_counts[i] = suffix_ge[i + 1] if (i + 1) <= max_stash else 0

        if record_file is not None:
            with open(record_file, "w", encoding="utf-8") as f:
                f.write(f"-1,{s}\n")
                for i in range(0, max_stash + 1):
                    f.write(f"{i},{tail_counts[i]}\n")

        return tail_counts, max_stash, len(recorded_stash_sizes)

def main():
    ap = argparse.ArgumentParser(description="Path ORAM simulator")
    ap.add_argument("--N", type=int, required=True)
    ap.add_argument("--Z", type=int, required=True)
    ap.add_argument("--L", type=int, required=True)
    ap.add_argument("--ops", type=int, required=True)
    ap.add_argument("--warmup", type=int, required=True)
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--out", type=str, default=None)
    args = ap.parse_args()

    if args.L < math.ceil(math.log2(args.N)):
        print(f"[WARN] L={args.L} is less than ceil(log2(N))={math.ceil(math.log2(args.N))}.", file=sys.stderr)
        sys.exit(2)

    print(f"[INFO] Initializing Path ORAM: N={args.N}, Z={args.Z}, L={args.L}, seed={args.seed}")
    poram = PathORAM(N=args.N, Z=args.Z, L=args.L, seed=args.seed)
    print(f"[INFO] Simulating: total_ops={args.ops}, warmup={args.warmup}")
    tail_counts, max_stash, recorded = poram.simulate(total_ops=args.ops, warmup_ops=args.warmup, record_file=args.out)
    print(f"[INFO] Recorded accesses: {recorded}")
    print(f"[INFO] Max stash observed: {max_stash}")
    if args.out:
        print(f"[INFO] Wrote file: {args.out}")

if __name__ == "__main__":
    main()
