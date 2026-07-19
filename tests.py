import random

class TestSimulator:
    """
    Handles test generation and simulation for the DUT
    """
    def __init__(self, dut):
        self.dut = dut
        self.test_database = []  # Store generated tests
        self.coverage_database = {}  # Store coverage results for each test

    def generate_test_stimuli(self, num_tests):
        """Generate a collection of test stimuli"""
        tests = []
        for _ in range(num_tests):
            # Create test with random values for each field
            test = {
                'data_mode': random.choice(self.dut.data_mode_values),
                'input_interface': random.choice(self.dut.input_interface_values),
                'data_size': random.choice(self.dut.data_size_values),
                'output_active': random.choice(self.dut.output_active_values),
                'data_bin': random.randint(0, self.dut.data_bin_max)
            }
            tests.append(test)

        # Add tests to test database
        for test in tests:
            self.test_database.append(test)

        return tests

    # ── private helper ────────────────────────────────────────────────────────

    def _resolve_coverage_points(self, test, encoded_out, overflow_flag):
        """
        Map Verilog outputs to coverage point ID strings.
        """
        data_mode       = test['data_mode']
        data_size       = test['data_size']       # original Python value (1-4)
        output_active   = test['output_active']
        data_bin        = test['data_bin']
        input_interface = test['input_interface']

        hit_points = []

        # GROUP1: Verilog confirmed MEM path (in both Process and Bypass modes)
        if encoded_out == 1:
            for bin_range in [(0, 100), (101, 500), (501, 1000)]:
                if bin_range[0] <= data_bin <= bin_range[1]:
                    point_id = (
                        f"g1_iface0_ds{data_size}_out{output_active}"
                        f"_bin{bin_range[0]}-{bin_range[1]}"
                    )
                    hit_points.append(point_id)

        # GROUP2: Verilog confirmed Radar path (in both Process and Bypass modes)
        if encoded_out == 2:
            for bin_range in [(0, 200), (201, 1000), (1001, 5000)]:
                if bin_range[0] <= data_bin <= bin_range[1]:
                    point_id = (
                        f"g2_iface1_ds{data_size}_out{output_active}"
                        f"_bin{bin_range[0]}-{bin_range[1]}"
                    )
                    hit_points.append(point_id)

        # GROUP3: Verilog confirmed overflow AND specific iface/data_size combo (Process Mode only)
        if data_mode == 1 and overflow_flag == 1 and input_interface == 1 and data_size == 4:
            point_id = (
                f"g3_iface{input_interface}_ds{data_size}_special_bin5001-10000"
            )
            hit_points.append(point_id)

        # GROUP4: Bypass Mode Coverage points (data_mode == 0)
        if data_mode == 0:
            for bin_range in [(0, 5000), (5001, 10000)]:
                if bin_range[0] <= data_bin <= bin_range[1]:
                    point_id = (
                        f"g4_bypass_iface{input_interface}_out{output_active}"
                        f"_bin{bin_range[0]}-{bin_range[1]}"
                    )
                    hit_points.append(point_id)

        return hit_points

    # ── public API (same signatures as before) ────────────────────────────────

    def simulate_tests(self, tests):
        """
        Simulate a batch of tests using the real Verilog DUT.
        One iverilog+vvp subprocess call for the whole batch (efficient).
        """
        sim_outputs = self.dut.run_verilog_simulation(tests)

        results = []
        for test, (encoded_out, overflow_flag) in zip(tests, sim_outputs):
            hit_points = self._resolve_coverage_points(test, encoded_out, overflow_flag)

            # Update DUT coverage model
            for point in hit_points:
                if point in self.dut.coverage_points:
                    self.dut.coverage_points[point] = True

            # Store in coverage database (key mirrors test_database index)
            test_id = len(self.coverage_database)
            self.coverage_database[test_id] = hit_points

            results.append(hit_points)

        return results

    def simulate_test(self, test):
        """
        Simulate a single test.
        """
        return self.simulate_tests([test])[0]
