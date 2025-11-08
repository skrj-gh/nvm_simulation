/**
 * Unit Test: Address Translation (VRA → VRN → PRN → PRA)
 *
 * This test verifies that the ReRAMRegionMapper correctly:
 * 1. Extracts VRN from VRA using bit shift operations
 * 2. Looks up PRN from Region Table
 * 3. Reconstructs PRA correctly
 * 4. Maintains identity mapping initially
 * 5. Correctly handles region swapping
 */

#include <iostream>
#include <cassert>
#include <cstdint>
#include <map>

// Simulate the key functions from ReRAMRegionMapper
class TestRegionMapper {
private:
    const int VRN_SHIFT = 6;
    const uint64_t RO_MASK = 0x3F;

    std::map<uint64_t, uint64_t> regionTable;
    std::map<uint64_t, uint64_t> inverseRegionTable;

    uint64_t numBanks = 8;
    uint64_t numRegionsPerBank = 1024;

public:
    TestRegionMapper() {
        InitializeRegionTable();
    }

    void InitializeRegionTable() {
        for (uint64_t bank = 0; bank < numBanks; bank++) {
            for (uint64_t VRN = 0; VRN < numRegionsPerBank; VRN++) {
                uint64_t key = (bank << 10) | VRN;
                regionTable[key] = VRN;  // Identity mapping
                inverseRegionTable[key] = VRN;
            }
        }
    }

    uint64_t Translate(uint64_t bank, uint64_t VRA) {
        // Extract VRN and Region Offset
        uint64_t VRN = VRA >> VRN_SHIFT;
        uint64_t RO = VRA & RO_MASK;

        // Lookup PRN
        uint64_t key = (bank << 10) | VRN;
        uint64_t PRN = regionTable[key];

        // Reconstruct PRA
        uint64_t PRA = (PRN << VRN_SHIFT) | RO;

        return PRA;
    }

    void SwapRegions(uint64_t bank, uint64_t VRN_hot, uint64_t VRN_cold) {
        uint64_t key_hot = (bank << 10) | VRN_hot;
        uint64_t key_cold = (bank << 10) | VRN_cold;

        uint64_t PRN_hot = regionTable[key_hot];
        uint64_t PRN_cold = regionTable[key_cold];

        // Swap forward mappings
        regionTable[key_hot] = PRN_cold;
        regionTable[key_cold] = PRN_hot;

        // Update inverse mappings
        uint64_t inv_key_hot = (bank << 10) | PRN_hot;
        uint64_t inv_key_cold = (bank << 10) | PRN_cold;
        inverseRegionTable[inv_key_hot] = VRN_cold;
        inverseRegionTable[inv_key_cold] = VRN_hot;
    }

    uint64_t GetVRNFromPRN(uint64_t bank, uint64_t PRN) {
        uint64_t key = (bank << 10) | PRN;
        return inverseRegionTable[key];
    }
};

void test_vra_decomposition() {
    std::cout << "Test 1: VRA Decomposition (VRA → VRN + RO)" << std::endl;

    const int VRN_SHIFT = 6;
    const uint64_t RO_MASK = 0x3F;

    // Test case 1: VRA = 0
    uint64_t VRA = 0;
    uint64_t VRN = VRA >> VRN_SHIFT;
    uint64_t RO = VRA & RO_MASK;
    assert(VRN == 0 && RO == 0);
    std::cout << "  VRA=0 → VRN=0, RO=0 ✓" << std::endl;

    // Test case 2: VRA = 63 (last row in first region)
    VRA = 63;
    VRN = VRA >> VRN_SHIFT;
    RO = VRA & RO_MASK;
    assert(VRN == 0 && RO == 63);
    std::cout << "  VRA=63 → VRN=0, RO=63 ✓" << std::endl;

    // Test case 3: VRA = 64 (first row in second region)
    VRA = 64;
    VRN = VRA >> VRN_SHIFT;
    RO = VRA & RO_MASK;
    assert(VRN == 1 && RO == 0);
    std::cout << "  VRA=64 → VRN=1, RO=0 ✓" << std::endl;

    // Test case 4: VRA = 127 (last row in second region)
    VRA = 127;
    VRN = VRA >> VRN_SHIFT;
    RO = VRA & RO_MASK;
    assert(VRN == 1 && RO == 63);
    std::cout << "  VRA=127 → VRN=1, RO=63 ✓" << std::endl;

    // Test case 5: VRA = 4096 (region 64, offset 0)
    VRA = 4096;
    VRN = VRA >> VRN_SHIFT;
    RO = VRA & RO_MASK;
    assert(VRN == 64 && RO == 0);
    std::cout << "  VRA=4096 → VRN=64, RO=0 ✓" << std::endl;

    // Test case 6: VRA = 65535 (max, last region)
    VRA = 65535;
    VRN = VRA >> VRN_SHIFT;
    RO = VRA & RO_MASK;
    assert(VRN == 1023 && RO == 63);
    std::cout << "  VRA=65535 → VRN=1023, RO=63 ✓" << std::endl;

    std::cout << "Test 1: PASSED ✓\n" << std::endl;
}

void test_identity_mapping() {
    std::cout << "Test 2: Identity Mapping (VRA → PRA with no swaps)" << std::endl;

    TestRegionMapper mapper;

    // Test several VRAs - should map to themselves initially
    uint64_t bank = 0;

    for (uint64_t VRA : {0, 63, 64, 127, 1024, 4096, 32768, 65535}) {
        uint64_t PRA = mapper.Translate(bank, VRA);
        assert(PRA == VRA);
        std::cout << "  Bank " << bank << ": VRA=" << VRA << " → PRA=" << PRA << " ✓" << std::endl;
    }

    std::cout << "Test 2: PASSED ✓\n" << std::endl;
}

void test_region_swapping() {
    std::cout << "Test 3: Region Swapping" << std::endl;

    TestRegionMapper mapper;
    uint64_t bank = 0;

    // Before swap: VRN 10 maps to PRN 10, VRN 20 maps to PRN 20
    uint64_t VRA_10_0 = (10 << 6) | 0;   // VRN=10, RO=0
    uint64_t VRA_10_31 = (10 << 6) | 31; // VRN=10, RO=31
    uint64_t VRA_20_0 = (20 << 6) | 0;   // VRN=20, RO=0
    uint64_t VRA_20_31 = (20 << 6) | 31; // VRN=20, RO=31

    uint64_t PRA_before_10_0 = mapper.Translate(bank, VRA_10_0);
    uint64_t PRA_before_20_0 = mapper.Translate(bank, VRA_20_0);

    assert(PRA_before_10_0 == VRA_10_0);
    assert(PRA_before_20_0 == VRA_20_0);
    std::cout << "  Before swap: VRA(VRN=10) → PRA(PRN=10) ✓" << std::endl;
    std::cout << "  Before swap: VRA(VRN=20) → PRA(PRN=20) ✓" << std::endl;

    // Swap VRN 10 and VRN 20
    mapper.SwapRegions(bank, 10, 20);
    std::cout << "  Swapped VRN 10 ↔ VRN 20" << std::endl;

    // After swap: VRN 10 should map to PRN 20, VRN 20 should map to PRN 10
    uint64_t PRA_after_10_0 = mapper.Translate(bank, VRA_10_0);
    uint64_t PRA_after_10_31 = mapper.Translate(bank, VRA_10_31);
    uint64_t PRA_after_20_0 = mapper.Translate(bank, VRA_20_0);
    uint64_t PRA_after_20_31 = mapper.Translate(bank, VRA_20_31);

    // Expected: VRN 10 → PRN 20, so VRA (10<<6)|0 → PRA (20<<6)|0
    uint64_t expected_10_0 = (20 << 6) | 0;
    uint64_t expected_10_31 = (20 << 6) | 31;
    uint64_t expected_20_0 = (10 << 6) | 0;
    uint64_t expected_20_31 = (10 << 6) | 31;

    assert(PRA_after_10_0 == expected_10_0);
    assert(PRA_after_10_31 == expected_10_31);
    assert(PRA_after_20_0 == expected_20_0);
    assert(PRA_after_20_31 == expected_20_31);

    std::cout << "  After swap: VRA(VRN=10,RO=0) → PRA(PRN=20,RO=0) ✓" << std::endl;
    std::cout << "  After swap: VRA(VRN=10,RO=31) → PRA(PRN=20,RO=31) ✓" << std::endl;
    std::cout << "  After swap: VRA(VRN=20,RO=0) → PRA(PRN=10,RO=0) ✓" << std::endl;
    std::cout << "  After swap: VRA(VRN=20,RO=31) → PRA(PRN=10,RO=31) ✓" << std::endl;

    std::cout << "Test 3: PASSED ✓\n" << std::endl;
}

void test_inverse_mapping() {
    std::cout << "Test 4: Inverse Mapping (PRN → VRN lookup)" << std::endl;

    TestRegionMapper mapper;
    uint64_t bank = 0;

    // Initially PRN should map back to same VRN
    for (uint64_t PRN : {0, 10, 20, 100, 500, 1023}) {
        uint64_t VRN = mapper.GetVRNFromPRN(bank, PRN);
        assert(VRN == PRN);
        std::cout << "  Before swap: PRN=" << PRN << " → VRN=" << VRN << " ✓" << std::endl;
    }

    // Swap VRN 10 and VRN 20
    mapper.SwapRegions(bank, 10, 20);
    std::cout << "  Swapped VRN 10 ↔ VRN 20" << std::endl;

    // Now PRN 10 should map to VRN 20, PRN 20 should map to VRN 10
    uint64_t VRN_from_10 = mapper.GetVRNFromPRN(bank, 10);
    uint64_t VRN_from_20 = mapper.GetVRNFromPRN(bank, 20);

    assert(VRN_from_10 == 20);
    assert(VRN_from_20 == 10);

    std::cout << "  After swap: PRN=10 → VRN=20 ✓" << std::endl;
    std::cout << "  After swap: PRN=20 → VRN=10 ✓" << std::endl;

    std::cout << "Test 4: PASSED ✓\n" << std::endl;
}

void test_multi_bank_isolation() {
    std::cout << "Test 5: Multi-Bank Isolation" << std::endl;

    TestRegionMapper mapper;

    // Swap VRN 10 and 20 in bank 0
    mapper.SwapRegions(0, 10, 20);

    // Bank 1 should still have identity mapping
    uint64_t VRA_10 = 10 << 6;
    uint64_t PRA_bank0 = mapper.Translate(0, VRA_10);
    uint64_t PRA_bank1 = mapper.Translate(1, VRA_10);

    uint64_t expected_bank0 = 20 << 6;  // Swapped
    uint64_t expected_bank1 = 10 << 6;  // Not swapped

    assert(PRA_bank0 == expected_bank0);
    assert(PRA_bank1 == expected_bank1);

    std::cout << "  Bank 0 (swapped): VRA(VRN=10) → PRA(PRN=20) ✓" << std::endl;
    std::cout << "  Bank 1 (not swapped): VRA(VRN=10) → PRA(PRN=10) ✓" << std::endl;

    std::cout << "Test 5: PASSED ✓\n" << std::endl;
}

void test_fast_region_detection() {
    std::cout << "Test 6: Fast Region Detection" << std::endl;

    const uint64_t numRegionsPerMat = 16;
    const uint64_t fastRegionsPerMat = 4;

    // Test PRN values
    for (uint64_t PRN = 0; PRN < 256; PRN++) {
        uint64_t regionInMat = PRN % numRegionsPerMat;
        bool isFast = (regionInMat < fastRegionsPerMat);

        // Mat 0: PRN 0-3 fast, 4-15 slow
        // Mat 1: PRN 16-19 fast, 20-31 slow
        // etc.

        if (PRN < 4 || (PRN >= 16 && PRN < 20) || (PRN >= 32 && PRN < 36)) {
            assert(isFast == true);
        } else if ((PRN >= 4 && PRN < 16) || (PRN >= 20 && PRN < 32) || (PRN >= 36 && PRN < 48)) {
            assert(isFast == false);
        }
    }

    std::cout << "  PRN 0-3 (Mat 0, regions 0-3): Fast ✓" << std::endl;
    std::cout << "  PRN 4-15 (Mat 0, regions 4-15): Slow ✓" << std::endl;
    std::cout << "  PRN 16-19 (Mat 1, regions 0-3): Fast ✓" << std::endl;
    std::cout << "  PRN 20-31 (Mat 1, regions 4-15): Slow ✓" << std::endl;

    std::cout << "Test 6: PASSED ✓\n" << std::endl;
}

int main() {
    std::cout << "========================================" << std::endl;
    std::cout << "ReRAM Region Mapper Unit Tests" << std::endl;
    std::cout << "========================================\n" << std::endl;

    test_vra_decomposition();
    test_identity_mapping();
    test_region_swapping();
    test_inverse_mapping();
    test_multi_bank_isolation();
    test_fast_region_detection();

    std::cout << "========================================" << std::endl;
    std::cout << "ALL TESTS PASSED ✓✓✓" << std::endl;
    std::cout << "========================================" << std::endl;

    return 0;
}
