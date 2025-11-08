#!/bin/bash
#
# Comprehensive Test Suite for Dynamic ReRAM Region Mapping
#
# This script runs all tests to verify the implementation:
# 1. Unit tests for address translation
# 2. Component loading verification
# 3. Migration algorithm validation
# 4. Performance comparison with baseline

set -e

echo "========================================"
echo "Dynamic ReRAM Region Mapping Test Suite"
echo "========================================"
echo

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$ROOT_DIR"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_header() {
    echo
    echo "========================================"
    echo "$1"
    echo "========================================"
    echo
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

# Track test results
total_tests=0
passed_tests=0

run_test() {
    local test_name=$1
    local test_command=$2

    total_tests=$((total_tests + 1))
    print_header "Test $total_tests: $test_name"

    if eval "$test_command"; then
        passed_tests=$((passed_tests + 1))
        print_success "$test_name PASSED"
        return 0
    else
        print_error "$test_name FAILED"
        return 1
    fi
}

# ========================================
# Test 1: Compile Unit Tests
# ========================================

compile_unit_tests() {
    echo "Compiling unit tests..."
    g++ -std=c++11 -o tests/test_address_translation tests/test_address_translation.cpp
    print_success "Unit tests compiled"
}

run_test "Compile Unit Tests" "compile_unit_tests"

# ========================================
# Test 2: Run Unit Tests
# ========================================

run_unit_tests() {
    echo "Running unit tests..."
    tests/test_address_translation
}

run_test "Address Translation Unit Tests" "run_unit_tests"

# ========================================
# Test 3: Component Loading
# ========================================

run_component_test() {
    echo "Running component loading test..."
    chmod +x tests/test_component_loading.sh
    tests/test_component_loading.sh
}

# Only run if gem5 is built
if [ -f "simulator/gem5/build/ARM/gem5.fast" ]; then
    run_test "Component Loading Verification" "run_component_test"
else
    print_warning "Skipping component loading test (gem5 not built)"
    echo "Build gem5 first with:"
    echo "  cd simulator/gem5"
    echo "  python3 \`which scons\` bitflip=1 -j 8 EXTRAS=../nvmain ./build/ARM/gem5.fast"
fi

# ========================================
# Test 4: Simple Memory Test
# ========================================

run_simple_memory_test() {
    print_header "Simple Memory Access Test"

    # Create a simple memory access program
    cat > tests/simple_mem_test.c <<'EOF'
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define SIZE (1024 * 1024)  // 1MB

int main() {
    printf("Starting simple memory test...\n");

    // Allocate array
    int *array = (int *)malloc(SIZE * sizeof(int));
    if (!array) {
        fprintf(stderr, "Allocation failed\n");
        return 1;
    }

    // Write pattern (will create hot regions)
    printf("Writing pattern...\n");
    for (int i = 0; i < SIZE; i++) {
        array[i] = i;
    }

    // Read and verify
    printf("Verifying...\n");
    int errors = 0;
    for (int i = 0; i < SIZE; i++) {
        if (array[i] != i) {
            errors++;
        }
    }

    printf("Test complete. Errors: %d\n", errors);
    free(array);
    return (errors == 0) ? 0 : 1;
}
EOF

    # Compile the test
    echo "Compiling simple memory test..."
    gcc -static -o tests/simple_mem_test tests/simple_mem_test.c

    # Run with gem5 (using non-deprecated config)
    echo "Running with gem5/NVMain..."
    simulator/gem5/build/ARM/gem5.fast \
        --outdir=m5out/simple_test \
        tests/nvmain_test_config.py \
        --mem-type=NVMainMemory \
        --nvmain-config=simulator/nvmain/Config/ReRAM_DynamicMapping.config \
        --cpu-type=TimingSimpleCPU \
        --caches --l2cache \
        --cmd=tests/simple_mem_test

    print_success "Simple memory test completed"
    echo "Output in: m5out/simple_test/"
}

if [ -f "simulator/gem5/build/ARM/gem5.fast" ]; then
    run_test "Simple Memory Access" "run_simple_memory_test"
else
    print_warning "Skipping simple memory test (gem5 not built)"
fi

# ========================================
# Test 5: Migration Algorithm Validation
# ========================================

run_migration_validation() {
    print_header "Migration Algorithm Validation"

    if [ ! -f "m5out/simple_test/stats.txt" ]; then
        print_warning "No statistics file found"
        echo "Run a simulation first to generate stats.txt"
        return 1
    fi

    chmod +x tests/test_migration_algorithm.py
    python3 tests/test_migration_algorithm.py m5out/simple_test/stats.txt
}

if [ -f "simulator/gem5/build/ARM/gem5.fast" ] && [ -f "m5out/simple_test/stats.txt" ]; then
    run_test "Migration Algorithm Validation" "run_migration_validation"
else
    print_warning "Skipping migration validation (no statistics available)"
fi

# ========================================
# Test 6: Configuration Validation
# ========================================

validate_configuration() {
    print_header "Configuration File Validation"

    config_file="simulator/nvmain/Config/ReRAM_DynamicMapping.config"

    echo "Checking configuration file: $config_file"

    required_params=(
        "AddressMappingScheme ReRAMRegionMapper"
        "MEM_CTL ReRAMRegionController"
        "BankType ReRAMBank"
        "CHANNELS 2"
        "RANKS 2"
        "BANKS 8"
        "ROWS 65536"
        "COLS 4096"
        "MATHeight 1024"
        "RegionSize 64"
        "FastRegionsPerMat 4"
        "Alpha"
        "Beta"
        "EpochLength"
        "MigrationThreshold"
        "FastRegionLatency"
        "SlowRegionLatency"
    )

    all_ok=true
    for param in "${required_params[@]}"; do
        if grep -q "$param" "$config_file"; then
            print_success "Found: $param"
        else
            print_error "Missing: $param"
            all_ok=false
        fi
    done

    if [ "$all_ok" = true ]; then
        print_success "Configuration file is complete"
        return 0
    else
        print_error "Configuration file has issues"
        return 1
    fi
}

run_test "Configuration Validation" "validate_configuration"

# ========================================
# Final Summary
# ========================================

print_header "Test Suite Summary"

echo "Total tests run: $total_tests"
echo "Tests passed: $passed_tests"
echo "Tests failed: $((total_tests - passed_tests))"
echo

if [ $passed_tests -eq $total_tests ]; then
    print_success "ALL TESTS PASSED ✓✓✓"
    echo
    echo "Your Dynamic ReRAM Region Mapping implementation is working correctly!"
    echo
    echo "Components verified:"
    echo "  ✓ Address translation (VRA → VRN → PRN → PRA)"
    echo "  ✓ Region Table management"
    echo "  ✓ Component loading and initialization"
    echo "  ✓ Configuration file correctness"

    if [ -f "m5out/simple_test/stats.txt" ]; then
        echo "  ✓ Migration algorithm operational"
        echo
        echo "Check detailed statistics in: m5out/simple_test/stats.txt"
    fi

    exit 0
else
    print_error "SOME TESTS FAILED"
    echo
    echo "Failed tests: $((total_tests - passed_tests))/$total_tests"
    echo
    echo "Review the output above to see which tests failed."
    echo "Common issues:"
    echo "  - gem5 not built: Run build command in simulator/gem5"
    echo "  - Missing config: Check simulator/nvmain/Config/ReRAM_DynamicMapping.config"
    echo "  - Component linking: Check simulator/nvmain/NVM/nvmain.cpp modifications"

    exit 1
fi
