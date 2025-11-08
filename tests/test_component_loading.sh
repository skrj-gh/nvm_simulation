#!/bin/bash
#
# Component Loading Test
#
# This test verifies that the Dynamic ReRAM Region Mapping components
# are correctly loaded and initialized during gem5/NVMain simulation.
#
# Expected output:
# - ReRAMRegionMapper initialization messages
# - ReRAMRegionController initialization messages
# - ReRAMBank configuration messages
# - Controller-Mapper linking confirmation

set -e  # Exit on error

echo "========================================"
echo "Component Loading Test"
echo "========================================"
echo

# Configuration
GEM5_DIR="simulator/gem5"
NVMAIN_CONFIG="simulator/nvmain/Config/ReRAM_DynamicMapping.config"
TEST_OUTPUT="tests/component_loading_test.out"

# Check if gem5 binary exists
if [ ! -f "$GEM5_DIR/build/ARM/gem5.fast" ]; then
    echo "ERROR: gem5.fast not found!"
    echo "Please build gem5 first:"
    echo "  cd $GEM5_DIR"
    echo "  python3 \`which scons\` bitflip=1 -j 8 EXTRAS=../nvmain ./build/ARM/gem5.fast"
    exit 1
fi

# Check if config file exists
if [ ! -f "$NVMAIN_CONFIG" ]; then
    echo "ERROR: Configuration file not found: $NVMAIN_CONFIG"
    exit 1
fi

echo "Test 1: Verify Configuration File"
echo "----------------------------------"
echo "Checking for required configuration parameters..."

required_params=(
    "AddressMappingScheme ReRAMRegionMapper"
    "MEM_CTL ReRAMRegionController"
    "BankType ReRAMBank"
    "RegionSize 64"
    "FastRegionsPerMat 4"
    "Alpha 0.5"
    "Beta 0.5"
    "EpochLength"
    "MigrationThreshold"
    "FastRegionLatency"
    "SlowRegionLatency"
)

all_found=true
for param in "${required_params[@]}"; do
    if grep -q "$param" "$NVMAIN_CONFIG"; then
        echo "  ✓ Found: $param"
    else
        echo "  ✗ Missing: $param"
        all_found=false
    fi
done

if [ "$all_found" = true ]; then
    echo "Configuration file OK ✓"
else
    echo "Configuration file has missing parameters ✗"
    exit 1
fi
echo

echo "Test 2: Dry-Run Simulation (Component Loading)"
echo "----------------------------------------------"
echo "Running gem5 with ReRAM configuration..."
echo "This will verify components load correctly."
echo

# Create a minimal test - just run /bin/true or similar
# We'll capture the output to check for initialization messages
$GEM5_DIR/build/ARM/gem5.fast \
    $GEM5_DIR/configs/example/se.py \
    --mem-type=NVMainMemory \
    --nvmain-config=$NVMAIN_CONFIG \
    --cpu-type=TimingSimpleCPU \
    --caches --l2cache \
    --cmd=/bin/true \
    2>&1 | tee $TEST_OUTPUT

echo
echo "Test 3: Verify Component Initialization"
echo "----------------------------------------"

# Check for expected initialization messages
echo "Checking for component initialization messages..."

check_message() {
    local message=$1
    local description=$2
    if grep -q "$message" "$TEST_OUTPUT"; then
        echo "  ✓ $description"
        return 0
    else
        echo "  ✗ $description (NOT FOUND)"
        return 1
    fi
}

success=true

# ReRAMRegionMapper initialization
check_message "ReRAMRegionMapper Configuration" "ReRAMRegionMapper initialized" || success=false
check_message "Region table size.*entries" "Region table created" || success=false
check_message "Initialized.*region mappings" "Region mappings initialized" || success=false

# Controller-Mapper linking
check_message "Detected ReRAMRegionMapper" "Controller detected mapper" || success=false
check_message "Linked ReRAMRegionController to ReRAMRegionMapper" "Controller linked to mapper" || success=false

# ReRAMRegionController initialization
check_message "ReRAMRegionController Configuration" "ReRAMRegionController initialized" || success=false
check_message "Alpha.*write weight" "Alpha parameter set" || success=false
check_message "Epoch length" "Epoch length configured" || success=false

# ReRAMBank initialization
check_message "ReRAMBank Configuration" "ReRAMBank initialized" || success=false
check_message "Fast region latency" "Fast region latency set" || success=false
check_message "Slow region latency" "Slow region latency set" || success=false

echo

if [ "$success" = true ]; then
    echo "========================================"
    echo "Component Loading Test: PASSED ✓✓✓"
    echo "========================================"
    echo
    echo "All components loaded correctly:"
    echo "  ✓ ReRAMRegionMapper (Address Translator)"
    echo "  ✓ ReRAMRegionController (Memory Controller)"
    echo "  ✓ ReRAMBank (Variable Latency Bank)"
    echo "  ✓ Controller-Mapper linking successful"
    echo
else
    echo "========================================"
    echo "Component Loading Test: FAILED ✗"
    echo "========================================"
    echo
    echo "Some components did not load correctly."
    echo "Check the output in: $TEST_OUTPUT"
    echo
    exit 1
fi

echo "Output saved to: $TEST_OUTPUT"
echo
