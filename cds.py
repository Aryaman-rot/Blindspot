import numpy as np
import random
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, recall_score, f1_score
from sklearn.utils.class_weight import compute_sample_weight

class CoverageDirectedTestSelection:
    """
    Implements the Coverage-Directed Test Selection methodology using Random Forest
    or Gradient Boosting Classifier with balanced class handling.
    """
    def __init__(self, dut, simulator, clf_type="rf", seed=42, show_importances=False):
        self.dut = dut
        self.simulator = simulator
        self.classifiers = {}  # One classifier per coverage group
        self.clf_type = clf_type
        self.seed = seed
        self.show_importances = show_importances
        self.feature_names = ["data_mode", "input_interface", "data_size", "output_active", "data_bin"]

    def get_uncovered_groups(self, threshold=100.0):
        """Get list of coverage groups that have not reached the threshold coverage"""
        uncovered_groups = []
        for group in self.dut.coverage_groups.keys():
            coverage = self.dut.get_group_coverage_percentage(group)
            if coverage < threshold:
                uncovered_groups.append(group)
        return uncovered_groups

    def prepare_training_data_for_group(self, group_name):
        """
        Prepare training data for a specific coverage group.
        Returns the FULL unbalanced dataset to maximize training data for balanced models.
        """
        group_points = self.dut.coverage_groups[group_name]

        # Find positive and negative sample test IDs
        positive_examples = []
        for test_id, hit_points in self.simulator.coverage_database.items():
            if any(point in hit_points for point in group_points):
                positive_examples.append(test_id)

        negative_examples = []
        for test_id in range(len(self.simulator.test_database)):
            if test_id in self.simulator.coverage_database:
                hit_points = self.simulator.coverage_database[test_id]
                if not any(point in hit_points for point in group_points):
                    negative_examples.append(test_id)

        if len(positive_examples) == 0 or len(negative_examples) == 0:
            return None, None, None

        # Build feature matrix (X) and label vector (y)
        X = []
        y = []
        used_test_ids = positive_examples + negative_examples

        for test_id in used_test_ids:
            test = self.simulator.test_database[test_id]
            X.append([
                test['data_mode'],
                test['input_interface'],
                test['data_size'],
                test['output_active'],
                test['data_bin']
            ])
            y.append(1 if test_id in positive_examples else 0)

        return np.array(X), np.array(y), used_test_ids

    def train_classifiers_for_uncovered_groups(self):
        """Train classifiers for all uncovered coverage groups"""
        uncovered_groups = self.get_uncovered_groups()
        print(f"Training classifiers for {len(uncovered_groups)} uncovered groups")

        for group in uncovered_groups:
            X, y, used_test_ids = self.prepare_training_data_for_group(group)

            if X is None or len(X) == 0:
                print(f"  No training data available for group {group}")
                continue

            # Ensure we have at least 1 positive sample to train
            if sum(y) == 0:
                print(f"  No positive samples available for group {group}, skipping.")
                continue

            # Instantiate model based on selection
            if self.clf_type == "rf":
                clf = RandomForestClassifier(max_depth=3, random_state=self.seed, class_weight="balanced")
                clf.fit(X, y)
            else:
                clf = GradientBoostingClassifier(max_depth=3, random_state=self.seed)
                # Compute sample weights to balance classes for Boosting
                sample_weights = compute_sample_weight(class_weight="balanced", y=y)
                clf.fit(X, y, sample_weight=sample_weights)

            self.classifiers[group] = clf

            # Display feature importances on every retrain if requested
            if self.show_importances:
                self.print_feature_importances(group)

    def print_feature_importances(self, group_name):
        """Helper to print feature importances for a group's classifier"""
        clf = self.classifiers.get(group_name)
        if clf is not None:
            importances = clf.feature_importances_
            print(f"\nFeature Importances for group {group_name}:")
            for name, imp in zip(self.feature_names, importances):
                print(f"  - {name:15}: {imp * 100:5.1f}%")

    def print_all_feature_importances(self):
        """Prints feature importances for all currently trained classifiers"""
        print("\n=== Final Feature Importances ===")
        for group in self.classifiers.keys():
            self.print_feature_importances(group)

    def select_next_tests(self, candidate_tests, max_tests):
        """Select most promising tests based on classifier predictions"""
        if not self.classifiers:
            print("No classifiers trained yet. Selecting random tests.")
            return random.sample(range(len(candidate_tests)), min(max_tests, len(candidate_tests)))

        uncovered_groups = self.get_uncovered_groups()
        if not uncovered_groups:
            print("All groups have reached coverage target. Selecting random tests.")
            return random.sample(range(len(candidate_tests)), min(max_tests, len(candidate_tests)))

        X_candidates = np.array([[
            test['data_mode'],
            test['input_interface'],
            test['data_size'],
            test['output_active'],
            test['data_bin']
        ] for test in candidate_tests])

        selected_indices = []

        # Try to select one test per uncovered group
        for group in uncovered_groups[:max_tests]:
            if group in self.classifiers:
                clf = self.classifiers[group]
                probabilities = clf.predict_proba(X_candidates)[:, 1]

                for _ in range(len(candidate_tests)):
                    if len(probabilities) == 0:
                        break
                    best_idx = np.argmax(probabilities)
                    if best_idx not in selected_indices:
                        selected_indices.append(best_idx)
                        break
                    else:
                        probabilities[best_idx] = -1

        # Fallback to random sampling if selection quota is not met
        remaining = max_tests - len(selected_indices)
        if remaining > 0:
            available_indices = [i for i in range(len(candidate_tests)) if i not in selected_indices]
            if available_indices:
                additional_indices = random.sample(available_indices, min(remaining, len(available_indices)))
                selected_indices.extend(additional_indices)

        return selected_indices

    def compare_classifiers(self, seed=42):
        """
        Compare RandomForestClassifier (balanced) against GradientBoostingClassifier
        on the initial random test dataset. Prints validation metrics.
        """
        uncovered_groups = self.get_uncovered_groups()
        print("\nClassifier Performance Comparison:")
        print("-" * 85)
        print(f"{'Group':10} | {'Model':18} | {'Accuracy':10} | {'Recall':10} | {'F1-Score':10}")
        print("-" * 85)

        for group in uncovered_groups:
            X, y, _ = self.prepare_training_data_for_group(group)
            if X is None or len(X) < 5:
                print(f"{group:10} | Insufficient data to evaluate.")
                continue

            # Train / Validation split (80/20) with seed preservation
            # Use stratify=y only if we have at least 2 positive samples to stratify
            X_train, X_val, y_train, y_val = train_test_split(
                X, y, test_size=0.2, random_state=seed, stratify=y if sum(y) > 1 else None
            )

            # Edge case handling: check if either split has zero positive class examples
            if sum(y_train) == 0 or sum(y_val) == 0:
                print(f"{group:10} | [Compare] Skipping - insufficient positive examples in train/val split.")
                continue

            models = {
                "Random Forest (Bal)": RandomForestClassifier(max_depth=3, random_state=seed, class_weight="balanced"),
                "Gradient Boosting": GradientBoostingClassifier(max_depth=3, random_state=seed)
            }

            for name, model in models.items():
                if name == "Gradient Boosting":
                    sample_weights = compute_sample_weight(class_weight="balanced", y=y_train)
                    model.fit(X_train, y_train, sample_weight=sample_weights)
                else:
                    model.fit(X_train, y_train)

                preds = model.predict(X_val)
                acc = accuracy_score(y_val, preds)
                rec = recall_score(y_val, preds, zero_division=0)
                f1 = f1_score(y_val, preds, zero_division=0)

                print(f"{group:10} | {name:18} | {acc:10.2%} | {rec:10.2%} | {f1:10.2%}")
            print("-" * 85)
