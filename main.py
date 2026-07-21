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
    # Plot output options
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
    # Experiment size parameters
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
    # Classifier options
    parser.add_argument(
        "--classifier",
        type=str,
        choices=["rf", "gb"],
        default="rf",
        help="Classifier to use for CDS: 'rf' (Random Forest) or 'gb' (Gradient Boosting) (default: rf).",
    )
    parser.add_argument(
        "--compare",
        action="store_true",
        help="Run classifier comparison on initial training data and exit.",
    )
    parser.add_argument(
        "--show-importances",
        action="store_true",
        help="Show feature importances on every retrain iteration.",
    )
    args = parser.parse_args()

    # Reproducibility
    seed_val = args.seed if args.seed is not None else 42
    if args.seed is not None:
        random.seed(args.seed)
        np.random.seed(args.seed)
        print(f"[Seed] Global random seed set to {args.seed}")

    # Create experiment
    experiment = Experiment(
        clf_type=args.classifier,
        seed=seed_val,
        show_importances=args.show_importances
    )
    
    # Check if we should only run the comparison evaluation
    if args.compare:
        print("\n=== Running Classifier Comparison Evaluation ===")
        # Run initial test simulation to gather training data
        experiment.run_initial_phase(args.initial_tests)
        experiment.cds.compare_classifiers(seed=seed_val)
        return

    # Run CDS method
    experiment.run_cds_iteration(
        args.initial_tests, args.iterations, args.tests_per_iter
    )
    
    # Run random selection with equivalent number of tests
    total_cds_tests = experiment.tests_simulated_cds
    experiment.run_random_selection(total_cds_tests)

    # Print per-group coverage summary
    print("\n--- Coverage Point Detail ---")
    dut = experiment.dut_cds
    for group, points in dut.coverage_groups.items():
        hit = sum(1 for p in points if dut.coverage_points.get(p, False))
        total = len(points)
        pct = (hit / total * 100) if total else 0
        bar = ("#" * hit) + ("." * (total - hit))
        print(f"  {group}: {hit:2}/{total:2} [{bar}] {pct:5.1f}%")

    # Plot and analyze results
    fig = experiment.plot_results()
    # Save plot; optionally open GUI window
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
    coverage_levels = args.coverage_milestones
    
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