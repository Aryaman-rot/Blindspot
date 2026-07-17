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

    def _resolve_coverage_points(self, test, encoded_out, overflow_flag):
        """
        Map Verilog outputs to coverage point ID strings.

        Verilog is the ORACLE for which interface path fired and whether
        data_bin > 5000. Python constructs the exact point-ID strings using
        the original test parameters -- identical format to the old if/else.

        encoded_out   : 1 = MEM path (GROUP1), 2 = Radar path (GROUP2)
        overflow_flag : 1 means data_bin > 5000, gates GROUP3
        """
        data_size       = test['data_size']       # original Python value (1-4)
        output_active   = test['output_active']
        data_bin        = test['data_bin']
        input_interface = test['input_interface']

        hit_points = []

        # GROUP1: Verilog confirmed MEM path
        if encoded_out == 1:
            for bin_range in [(0, 100), (101, 500), (501, 1000)]:
                if bin_range[0] <= data_bin <= bin_range[1]:
                    point_id = (
                        f"g1_iface0_ds{data_size}_out{output_active}"
                        f"_bin{bin_range[0]}-{bin_range[1]}"
                    )
                    hit_points.append(point_id)

        # GROUP2: Verilog confirmed Radar path
        if encoded_out == 2:
            for bin_range in [(0, 200), (201, 1000), (1001, 5000)]:
                if bin_range[0] <= data_bin <= bin_range[1]:
                    point_id = (
                        f"g2_iface1_ds{data_size}_out{output_active}"
                        f"_bin{bin_range[0]}-{bin_range[1]}"
                    )
                    hit_points.append(point_id)

        # GROUP3: Verilog confirmed overflow AND specific iface/data_size combo
        if overflow_flag == 1 and input_interface == 1 and data_size == 4:
            point_id = (
                f"g3_iface{input_interface}_ds{data_size}_special_bin5001-10000"
            )
            hit_points.append(point_id)

        return hit_points

    def simulate_tests(self, tests):
        """
        Simulate a batch of tests using the real Verilog DUT.
        One iverilog+vvp subprocess call for the whole batch (efficient).
        Updates dut.coverage_points and self.coverage_database in place.
        Returns list-of-lists of hit point IDs (same contract as before).
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
        Delegates to simulate_tests() to reuse the Verilog path.
        """
        return self.simulate_tests([test])[0]
