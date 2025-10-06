# -*- coding: utf-8 -*-
"""
Task 2 – Plot Path ORAM stash size distribution
Generates P[size(S) > R] vs R for Z=2 and Z=4 using simulation output files.
"""

import matplotlib.pyplot as plt

def read_simulation_file(path):
    """Read the simulationX.txt file and return (S, tail_counts dict)."""
    tail_counts = {}
    total_accesses = None
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split(',')
            if parts[0].startswith('-1'):
                total_accesses = int(parts[1])
            else:
                i = int(parts[0])
                s_i = int(parts[1])
                tail_counts[i] = s_i
    if total_accesses is None:
        raise ValueError(f"No total line (-1, S) found in {path}")
    return total_accesses, tail_counts


def compute_probabilities(total_accesses, tail_counts):
    """Return lists of (R, P[size(S)>R]) excluding R=0."""
    R_vals = sorted(k for k in tail_counts.keys() if k > 0)
    probs = [tail_counts[r] / total_accesses for r in R_vals]
    return R_vals, probs


def main():
    # Input files (adjust names if you used different ones)
    files = {
        "Z = 2": "simulation1.txt",
        "Z = 4": "simulation2.txt"
    }

    plt.figure(figsize=(7,5))
    for label, fname in files.items():
        total, tails = read_simulation_file(fname)
        R, Pvals = compute_probabilities(total, tails)
        plt.plot(R, Pvals, marker='o', label=label)

    plt.xlabel("Required stash size R (excluding R=0)")
    plt.ylabel("Pr[size(S) > R]")
    plt.title("Path ORAM Stash Size Probability")
    plt.yscale('log')       # optional: log scale makes tail visible
    plt.grid(True, which='both', linestyle='--', linewidth=0.5)
    plt.legend()
    plt.tight_layout()
    plt.savefig("stash_probability_plot.png", dpi=300)
    print("Saved plot to stash_probability_plot.png")

if __name__ == "__main__":
    main()
