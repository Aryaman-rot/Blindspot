import argparse
import numpy as np
import random

from exp import Experiment

def main():
    parser = argparse.ArgumentParser(description="Coverage-Directed Test Selection experiment")
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        metavar="INT",
        help="Fix the global random seed (random + numpy) for a fully reproducible run.",
    )
    # --- Change 2: Non-blocking plot args ---
    parser.add_argument(
        "--output",
        type=str,
        default="results.png",
        metavar="FILE",
        help="Filename to save the results plot to (default: results.png).",
    )
    parser.add_argument(
        "--show",
        action="store_true",
        help="Open the plot in a GUI window after saving (blocks until closed).",
    )
    # --- Change 3: Configurable experiment parameters ---
    parser.add_argument(
        "--initial-tests",
        type=int,
        default=500,
        metavar="N",
        help="Number of initial random tests before CDS begins (default: 500).",
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=100,
        metavar="N",
        help="Number of CDS iterations to run (default: 100).",
    )
    parser.add_argument(
        "--tests-per-iter",
        type=int,
        default=50,
        metavar="N",
        help="Number of tests selected per CDS iteration (default: 50).",
    )
    parser.add_argument(
        "--coverage-milestones",
        type=int,
        nargs="+",
        default=[90, 95, 98],
        metavar="PCT",
        help="Coverage %% levels to report savings for (default: 90 95 98).",
    )
    args = parser.parse_args()

    # --- Change 1: Reproducibility seed ---
    if args.seed is not None:
        random.seed(args.seed)
        np.random.seed(args.seed)
        print(f"[Seed] Global random seed set to {args.seed}")

    # Create experiment
    experiment = Experiment()
    
    # Run CDS method
    experiment.run_cds_iteration(
        args.initial_tests, args.iterations, args.tests_per_iter
    )
    
    # Run random selection with equivalent number of tests
    total_cds_tests = experiment.tests_simulated_cds
    experiment.run_random_selection(total_cds_tests)

    print(experiment.dut_cds.coverage_points)

    # Plot and analyze results
    fig = experiment.plot_results()
    # --- Change 2: Save plot; optionally open GUI window ---
    fig.savefig(args.output, dpi=150, bbox_inches="tight")
    print(f"[Plot] Saved to {args.output}")
    if args.show:
        fig.show()
    
    # Print detailed results
    print("\n--- Experiment Results ---")
    print(f"Total tests with CDS: {experiment.tests_simulated_cds}")
    print(f"Final coverage with CDS: {experiment.coverage_progress_cds[-1][1]:.2f}%")
    print(f"Total tests with Random: {experiment.tests_simulated_random}")
    print(f"Final coverage with Random: {experiment.coverage_progress_random[-1][1]:.2f}%")
    
    # Calculate tests needed to reach specific coverage levels
    coverage_levels = args.coverage_milestones  # --- Change 3: was hardcoded [90, 95, 98]
    
    print("\nTests required to reach coverage levels:")
    print("Coverage | CDS Tests | Random Tests | Savings")
    print("---------|-----------|-------------|--------")
    
    for level in coverage_levels:
        # Find tests needed for CDS
        cds_tests = None
        for tests, coverage in experiment.coverage_progress_cds:
            if coverage >= level:
                cds_tests = tests
                break
        
        # Find tests needed for Random
        random_tests = None
        for tests, coverage in experiment.coverage_progress_random:
            if coverage >= level:
                random_tests = tests
                break
        
        if cds_tests is not None and random_tests is not None:
            savings = ((random_tests - cds_tests) / random_tests) * 100
            print(f"{level:7}% | {cds_tests:9} | {random_tests:11} | {savings:6.2f}%")
        else:
            print(f"{level:7}% | {'N/A':9} | {'N/A':11} | {'N/A':6}")

if __name__ == "__main__":
    main()