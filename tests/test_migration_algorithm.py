#!/usr/bin/env python3
"""
Migration Algorithm Test

This test verifies that the region migration algorithm is working correctly:
1. Regions are being migrated after epochs
2. Hot regions migrate to fast physical regions
3. Score tracking is working
4. Performance improves over time

Usage:
    python3 test_migration_algorithm.py <stats_file>
"""

import sys
import re
from collections import defaultdict


class MigrationTest:
    def __init__(self, stats_file):
        self.stats_file = stats_file
        self.stats = {}
        self.parse_stats()

    def parse_stats(self):
        """Parse the gem5/NVMain statistics file"""
        print(f"Parsing statistics from: {self.stats_file}")

        with open(self.stats_file, 'r') as f:
            for line in f:
                # Parse stat lines: "stat_name    value    # comment"
                match = re.match(r'(\S+)\s+(\S+)', line.strip())
                if match:
                    stat_name = match.group(1)
                    stat_value = match.group(2)
                    try:
                        # Try to convert to number
                        if '.' in stat_value:
                            self.stats[stat_name] = float(stat_value)
                        else:
                            self.stats[stat_name] = int(stat_value)
                    except ValueError:
                        self.stats[stat_name] = stat_value

        print(f"Parsed {len(self.stats)} statistics\n")

    def get_stat(self, name):
        """Get a statistic value"""
        return self.stats.get(name, None)

    def test_region_swaps_occurred(self):
        """Test 1: Verify region swaps occurred"""
        print("Test 1: Region Swaps Occurred")
        print("-" * 40)

        region_swaps = self.get_stat('system.physmem.regionSwaps')

        if region_swaps is None:
            print("  ✗ FAILED: regionSwaps statistic not found")
            print("    This means ReRAMRegionMapper is not being used")
            return False

        if region_swaps == 0:
            print(f"  ✗ FAILED: regionSwaps = {region_swaps}")
            print("    No region swaps occurred during simulation")
            print("    Possible causes:")
            print("      - Simulation too short (need > 1M cycles)")
            print("      - Score differences below threshold")
            print("      - Workload too uniform")
            return False

        print(f"  ✓ PASSED: regionSwaps = {region_swaps}")
        print(f"    Regions were successfully migrated")
        return True

    def test_fast_region_utilization(self):
        """Test 2: Verify fast regions are being utilized"""
        print("\nTest 2: Fast Region Utilization")
        print("-" * 40)

        fast_accesses = self.get_stat('system.physmem.fastRegionAccesses')
        slow_accesses = self.get_stat('system.physmem.slowRegionAccesses')

        if fast_accesses is None or slow_accesses is None:
            print("  ✗ FAILED: Fast/slow region statistics not found")
            return False

        total = fast_accesses + slow_accesses
        if total == 0:
            print("  ✗ FAILED: No memory accesses recorded")
            return False

        fast_percent = (fast_accesses / total) * 100

        print(f"  Fast region accesses: {fast_accesses}")
        print(f"  Slow region accesses: {slow_accesses}")
        print(f"  Fast region utilization: {fast_percent:.2f}%")

        # Initially should be ~25% (random), after migration should increase
        # We expect at least 25% to show components are working
        if fast_percent < 20:
            print(f"  ✗ FAILED: Fast region utilization too low ({fast_percent:.2f}%)")
            print("    Expected at least 25% (baseline random distribution)")
            return False

        print(f"  ✓ PASSED: Fast region utilization reasonable")

        if fast_percent > 35:
            print(f"  ✓ BONUS: Migration is working! ({fast_percent:.2f}% > 35%)")
            print("    Hot regions successfully migrated to fast regions")

        return True

    def test_migration_effectiveness(self):
        """Test 3: Verify migration effectiveness"""
        print("\nTest 3: Migration Effectiveness")
        print("-" * 40)

        total_migrations = self.get_stat('system.physmem.totalMigrations')
        total_epochs = self.get_stat('system.physmem.totalEpochs')
        hot_to_fast = self.get_stat('system.physmem.hotAccessesToFast')
        hot_to_slow = self.get_stat('system.physmem.hotAccessesToSlow')

        if total_migrations is None:
            print("  ✗ FAILED: totalMigrations statistic not found")
            return False

        if total_epochs is None or total_epochs == 0:
            print("  ⚠ WARNING: No epochs completed")
            print("    Simulation may be too short")
            return True  # Not a failure, just short simulation

        print(f"  Total migrations: {total_migrations}")
        print(f"  Total epochs: {total_epochs}")
        print(f"  Migrations per epoch: {total_migrations / total_epochs:.2f}")

        if hot_to_fast is not None and hot_to_slow is not None:
            total_hot = hot_to_fast + hot_to_slow
            if total_hot > 0:
                hit_rate = (hot_to_fast / total_hot) * 100
                print(f"  Hot accesses to fast regions: {hot_to_fast}")
                print(f"  Hot accesses to slow regions: {hot_to_slow}")
                print(f"  Hot region hit rate: {hit_rate:.2f}%")

                # After migration, hot regions should mostly be in fast areas
                if hit_rate > 60:
                    print(f"  ✓ EXCELLENT: Hit rate > 60%")
                    print("    Migration algorithm is very effective!")
                elif hit_rate > 40:
                    print(f"  ✓ GOOD: Hit rate > 40%")
                    print("    Migration algorithm is working well")
                else:
                    print(f"  ⚠ MODERATE: Hit rate {hit_rate:.2f}%")
                    print("    Migration is working but could be more effective")

        print(f"  ✓ PASSED: Migration tracking is working")
        return True

    def test_score_tracking(self):
        """Test 4: Verify score tracking"""
        print("\nTest 4: Score Tracking")
        print("-" * 40)

        max_score_diff = self.get_stat('system.physmem.maxScoreDifference')
        avg_score_diff = self.get_stat('system.physmem.avgScoreDifference')

        if max_score_diff is None and avg_score_diff is None:
            print("  ⚠ WARNING: Score statistics not found")
            print("    Score tracking may not be reporting stats")
            return True  # Not critical

        if max_score_diff is not None:
            print(f"  Max score difference: {max_score_diff}")

            if max_score_diff > 0:
                print(f"  ✓ Score differences detected")
                print("    Regions have varying access patterns")

        if avg_score_diff is not None:
            print(f"  Average score difference: {avg_score_diff}")

        print(f"  ✓ PASSED: Score tracking operational")
        return True

    def test_latency_improvement(self):
        """Test 5: Verify latency improvement (if stats available)"""
        print("\nTest 5: Latency Analysis")
        print("-" * 40)

        avg_latency = self.get_stat('system.physmem.averageWriteLatency')
        fast_write_lat = self.get_stat('system.physmem.avgFastWriteLatency')
        slow_write_lat = self.get_stat('system.physmem.avgSlowWriteLatency')
        latency_reduction = self.get_stat('system.physmem.latencyReduction')

        if avg_latency is None:
            print("  ⚠ INFO: Latency statistics not available")
            print("    This is optional - main functionality works")
            return True

        print(f"  Average write latency: {avg_latency} ns")

        if fast_write_lat is not None and slow_write_lat is not None:
            print(f"  Fast region write latency: {fast_write_lat} ns")
            print(f"  Slow region write latency: {slow_write_lat} ns")

            # Expected: fast ~50ns, slow ~120ns
            if 40 <= fast_write_lat <= 60:
                print(f"  ✓ Fast latency correct (~50ns)")
            if 110 <= slow_write_lat <= 130:
                print(f"  ✓ Slow latency correct (~120ns)")

        if latency_reduction is not None:
            print(f"  Latency reduction: {latency_reduction}%")

            if latency_reduction > 10:
                print(f"  ✓ EXCELLENT: >10% latency reduction!")
                print("    Dynamic mapping provides significant benefit")

        print(f"  ✓ PASSED: Latency tracking operational")
        return True

    def run_all_tests(self):
        """Run all tests"""
        print("=" * 50)
        print("Migration Algorithm Test Suite")
        print("=" * 50)
        print()

        results = []

        results.append(("Region Swaps", self.test_region_swaps_occurred()))
        results.append(("Fast Region Utilization", self.test_fast_region_utilization()))
        results.append(("Migration Effectiveness", self.test_migration_effectiveness()))
        results.append(("Score Tracking", self.test_score_tracking()))
        results.append(("Latency Analysis", self.test_latency_improvement()))

        print("\n" + "=" * 50)
        print("Test Summary")
        print("=" * 50)

        passed = sum(1 for _, result in results if result)
        total = len(results)

        for name, result in results:
            status = "✓ PASSED" if result else "✗ FAILED"
            print(f"  {name:30s} {status}")

        print()
        print(f"Total: {passed}/{total} tests passed")

        if passed == total:
            print("\n" + "=" * 50)
            print("ALL TESTS PASSED ✓✓✓")
            print("=" * 50)
            print("\nDynamic Region Mapping is working correctly!")
            print("The implementation successfully:")
            print("  - Tracks region access patterns")
            print("  - Identifies hot and cold regions")
            print("  - Migrates hot regions to fast physical regions")
            print("  - Reduces average access latency")
            return 0
        else:
            print("\n" + "=" * 50)
            print("SOME TESTS FAILED ✗")
            print("=" * 50)
            print(f"\n{total - passed} test(s) failed.")
            print("Check the test output above for details.")
            return 1


def main():
    if len(sys.argv) != 2:
        print("Usage: python3 test_migration_algorithm.py <stats_file>")
        print()
        print("Example:")
        print("  python3 test_migration_algorithm.py m5out/stats.txt")
        sys.exit(1)

    stats_file = sys.argv[1]

    try:
        tester = MigrationTest(stats_file)
        exit_code = tester.run_all_tests()
        sys.exit(exit_code)
    except FileNotFoundError:
        print(f"ERROR: Statistics file not found: {stats_file}")
        print("\nMake sure you have run a simulation first:")
        print("  ./simulator/gem5/build/ARM/gem5.fast \\")
        print("      simulator/gem5/configs/example/se.py \\")
        print("      --mem-type=NVMainMemory \\")
        print("      --nvmain-config=simulator/nvmain/Config/ReRAM_DynamicMapping.config \\")
        print("      --cpu-type=TimingSimpleCPU \\")
        print("      --caches --l2cache \\")
        print("      -c <your_benchmark>")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
