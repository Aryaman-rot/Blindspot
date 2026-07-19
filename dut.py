import csv
import os
import subprocess

class SimpleDUT:
    """
    A simplified Device Under Test (DUT) representing a basic signal processor
    with configuration fields similar to those mentioned in the paper.
    """
    def __init__(self):
        # Define possible values for each configuration field
        self.data_mode_values = [0, 1]  # 0: Bypass, 1: Process
        self.input_interface_values = [0, 1]  # 0: MEM, 1: Radar
        self.data_size_values = [1, 2, 3, 4]
        self.output_active_values = [0, 1]
        self.data_bin_max = 10000  # Simplified range for data_bin

        # Initialize coverage model
        self.initialize_coverage_model()

    def initialize_coverage_model(self):
        """Initialize the coverage model with coverage points and groups"""
        self.coverage_points = {}
        self.coverage_groups = {}

        # Group 1: Input Interface = 0 (Memory) related functionality
        group1_points = []
        for ds in self.data_size_values:
            for out_act in self.output_active_values:
                for bin_range in [(0, 100), (101, 500), (501, 1000)]:
                    point_id = f"g1_iface0_ds{ds}_out{out_act}_bin{bin_range[0]}-{bin_range[1]}"
                    self.coverage_points[point_id] = False
                    group1_points.append(point_id)
        self.coverage_groups["GROUP1"] = group1_points

        # Group 2: Input Interface = 1 (Radar) related functionality
        group2_points = []
        for ds in self.data_size_values:
            for out_act in self.output_active_values:
                for bin_range in [(0, 200), (201, 1000), (1001, 5000)]:
                    point_id = f"g2_iface1_ds{ds}_out{out_act}_bin{bin_range[0]}-{bin_range[1]}"
                    self.coverage_points[point_id] = False
                    group2_points.append(point_id)
        self.coverage_groups["GROUP2"] = group2_points

        # Group 3: Cross-product functionality (complex interactions)
        group3_points = []
        for iface in self.input_interface_values:
            for ds in [3, 4]:  # Only larger data sizes
                if iface == 1 and ds == 4:  # Special radar high-data case
                    for bin_range in [(5001, 10000)]:
                        point_id = f"g3_iface{iface}_ds{ds}_special_bin{bin_range[0]}-{bin_range[1]}"
                        self.coverage_points[point_id] = False
                        group3_points.append(point_id)
        self.coverage_groups["GROUP3"] = group3_points

        # Group 4: Bypass Mode Functionality (data_mode == 0)
        group4_points = []
        for iface in self.input_interface_values:
            for out_act in self.output_active_values:
                for bin_range in [(0, 5000), (5001, 10000)]:
                    point_id = f"g4_bypass_iface{iface}_out{out_act}_bin{bin_range[0]}-{bin_range[1]}"
                    self.coverage_points[point_id] = False
                    group4_points.append(point_id)
        self.coverage_groups["GROUP4"] = group4_points

        # Metadata about coverage model
        self.total_coverage_points = len(self.coverage_points)
        self.coverage_per_group = {group: len(points) for group, points in self.coverage_groups.items()}

    def get_coverage_percentage(self):
        """Calculate the current coverage percentage"""
        covered = sum(1 for p in self.coverage_points.values() if p)
        return (covered / self.total_coverage_points) * 100

    def get_group_coverage_percentage(self, group_name):
        """Calculate coverage percentage for a specific group"""
        group_points = self.coverage_groups[group_name]
        covered = sum(1 for p in group_points if self.coverage_points[p])
        return (covered / len(group_points)) * 100

    def reset_coverage(self):
        """Reset all coverage points to not covered"""
        for point in self.coverage_points:
            self.coverage_points[point] = False

    def run_verilog_simulation(self, tests):
        """
        Write stimulus, compile (once) + run the Verilog testbench via Icarus
        Verilog, and return a list of (encoded_out: int, overflow_flag: int)
        tuples -- one per test, in the same order as `tests`.
        """
        project_root = os.path.dirname(os.path.abspath(__file__))
        rtl_dir   = os.path.join(project_root, "rtl")
        stim_path = os.path.join(rtl_dir, "stimulus.csv")
        out_path  = os.path.join(rtl_dir, "sim_output.csv")
        vvp_path  = os.path.join(rtl_dir, "sim.vvp")
        tb_path   = os.path.join(rtl_dir, "signal_proc_tb.v")
        mod_path  = os.path.join(rtl_dir, "signal_proc.v")

        iverilog_cmd = "iverilog"
        vvp_cmd = "vvp"

        import shutil
        if not shutil.which(iverilog_cmd):
            fallback_iverilog = r"C:\iverilog\bin\iverilog.exe"
            if os.path.exists(fallback_iverilog):
                iverilog_cmd = fallback_iverilog

        if not shutil.which(vvp_cmd):
            fallback_vvp = r"C:\iverilog\bin\vvp.exe"
            if os.path.exists(fallback_vvp):
                vvp_cmd = fallback_vvp

        # -- Step 1: Write stimulus (no header; data_size offset by -1) -------
        with open(stim_path, "w", newline="") as f:
            for t in tests:
                f.write(
                    f"{t['data_mode']},"
                    f"{t['input_interface']},"
                    f"{t['data_size'] - 1},"   # Python 1-4 -> Verilog [1:0] 0-3
                    f"{t['output_active']},"
                    f"{t['data_bin']}\n"
                )

        # -- Step 2: Compile only when sim.vvp is absent or stale -------------
        sources = [tb_path, mod_path]
        needs_compile = (
            not os.path.exists(vvp_path)
            or os.path.getmtime(vvp_path) < max(os.path.getmtime(s) for s in sources)
        )
        if needs_compile:
            print("[Verilog] Compiling signal_proc (first run or source changed)...")
            rel_tb = os.path.relpath(tb_path, project_root).replace(os.sep, "/")
            rel_mod = os.path.relpath(mod_path, project_root).replace(os.sep, "/")
            rel_vvp = os.path.relpath(vvp_path, project_root).replace(os.sep, "/")
            
            result = subprocess.run(
                [iverilog_cmd, "-s", "signal_proc_tb", "-o", rel_vvp, rel_tb, rel_mod],
                capture_output=True, text=True,
                cwd=project_root
            )
            if result.returncode != 0:
                raise RuntimeError(f"iverilog compile failed:\n{result.stderr}")

        # -- Step 3: Simulate (always -- stimulus changes every iteration) ----
        rel_vvp = os.path.relpath(vvp_path, project_root).replace(os.sep, "/")
        result = subprocess.run(
            [vvp_cmd, rel_vvp],
            capture_output=True, text=True,
            cwd=project_root,  # so $fopen("rtl/...") in testbench resolves
        )
        if result.returncode != 0:
            raise RuntimeError(f"vvp simulation failed:\n{result.stderr}")

        # -- Step 4: Read outputs ---------------------------------------------
        sim_results = []
        with open(out_path, newline="") as f:
            reader = csv.DictReader(f)   # header: encoded_out,overflow_flag
            for row in reader:
                sim_results.append(
                    (int(row["encoded_out"]), int(row["overflow_flag"]))
                )

        if len(sim_results) != len(tests):
            raise RuntimeError(
                f"Simulation output row count ({len(sim_results)}) "
                f"!= stimulus count ({len(tests)})"
            )

        return sim_results
