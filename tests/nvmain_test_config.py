#!/usr/bin/env python3
"""
Minimal gem5 Configuration for NVMain Testing

This is a simple, non-deprecated configuration specifically for testing
the Dynamic ReRAM Region Mapping implementation with NVMain.

Usage:
    gem5.fast tests/nvmain_test_config.py [options]
"""

import argparse
import sys
import os

# Add gem5 to path
gem5_path = os.path.join(os.path.dirname(__file__), '..', 'simulator', 'gem5')
sys.path.insert(0, os.path.join(gem5_path, 'configs'))

import m5
from m5.objects import *
from m5.util import addToPath

# Import common scripts
addToPath('../configs/common')
addToPath('../configs')

def create_simple_system(args):
    """Create a minimal system for NVMain testing"""

    # Create the system
    system = System()

    # Set up clock domain
    system.clk_domain = SrcClockDomain()
    system.clk_domain.clock = '2.4GHz'
    system.clk_domain.voltage_domain = VoltageDomain()

    # Create CPU
    if args.cpu_type == "AtomicSimpleCPU":
        system.cpu = AtomicSimpleCPU()
    elif args.cpu_type == "TimingSimpleCPU":
        system.cpu = TimingSimpleCPU()
    else:
        print(f"Error: Unsupported CPU type {args.cpu_type}")
        sys.exit(1)

    # Set up memory mode
    system.mem_mode = 'timing' if args.cpu_type == "TimingSimpleCPU" else 'atomic'

    # Memory ranges
    system.mem_ranges = [AddrRange('4GB')]

    # Create memory bus
    system.membus = SystemXBar()

    # Set up caches if requested
    if args.caches:
        system.cpu.icache = Cache(size='32kB', assoc=2)
        system.cpu.dcache = Cache(size='8kB', assoc=2)

        system.cpu.icache.cpu_side = system.cpu.icache_port
        system.cpu.dcache.cpu_side = system.cpu.dcache_port

        if args.l2cache:
            system.l2cache = Cache(size='8kB', assoc=4)
            system.l2bus = L2XBar()

            system.cpu.icache.mem_side = system.l2bus.cpu_side_ports
            system.cpu.dcache.mem_side = system.l2bus.cpu_side_ports
            system.l2cache.cpu_side = system.l2bus.mem_side_ports
            system.l2cache.mem_side = system.membus.cpu_side_ports
        else:
            system.cpu.icache.mem_side = system.membus.cpu_side_ports
            system.cpu.dcache.mem_side = system.membus.cpu_side_ports
    else:
        # No caches - direct connection
        system.cpu.icache_port = system.membus.cpu_side_ports
        system.cpu.dcache_port = system.membus.cpu_side_ports

    # Create interrupt controller (required for ARM)
    system.cpu.createInterruptController()

    # Set up memory
    if args.mem_type == "NVMainMemory":
        # NVMain memory with custom config
        system.mem_ctrl = NVMainMemory()
        if args.nvmain_config:
            system.mem_ctrl.config = args.nvmain_config
        else:
            print("Error: --nvmain-config required when using NVMainMemory")
            sys.exit(1)
    else:
        # Default DDR3 memory
        system.mem_ctrl = MemCtrl()
        system.mem_ctrl.dram = DDR3_1600_8x8()

    system.mem_ctrl.range = system.mem_ranges[0]
    system.mem_ctrl.port = system.membus.mem_side_ports

    # Create system port
    system.system_port = system.membus.cpu_side_ports

    return system


def create_process(args):
    """Create a simple process to run"""

    process = Process()

    if args.cmd:
        process.cmd = [args.cmd]
    else:
        # Default: just exit immediately
        process.cmd = ['/bin/true']

    return process


def main():
    parser = argparse.ArgumentParser(
        description="Simple gem5 configuration for NVMain testing"
    )

    parser.add_argument('--cpu-type', type=str, default='TimingSimpleCPU',
                        choices=['AtomicSimpleCPU', 'TimingSimpleCPU'],
                        help='CPU type to use')

    parser.add_argument('--mem-type', type=str, default='DDR3_1600_8x8',
                        help='Memory type (use NVMainMemory for NVMain)')

    parser.add_argument('--nvmain-config', type=str, default=None,
                        help='Path to NVMain configuration file')

    parser.add_argument('--caches', action='store_true',
                        help='Enable L1 caches')

    parser.add_argument('--l2cache', action='store_true',
                        help='Enable L2 cache (requires --caches)')

    parser.add_argument('--cmd', type=str, default=None,
                        help='Command to run (default: /bin/true)')

    args = parser.parse_args()

    # Validate arguments
    if args.l2cache and not args.caches:
        print("Error: --l2cache requires --caches")
        sys.exit(1)

    print("=" * 60)
    print("gem5 NVMain Test Configuration")
    print("=" * 60)
    print(f"CPU Type: {args.cpu_type}")
    print(f"Memory Type: {args.mem_type}")
    if args.nvmain_config:
        print(f"NVMain Config: {args.nvmain_config}")
    print(f"Caches: {'Yes' if args.caches else 'No'}")
    if args.caches:
        print(f"L2 Cache: {'Yes' if args.l2cache else 'No'}")
    print(f"Command: {args.cmd if args.cmd else '/bin/true'}")
    print("=" * 60)
    print()

    # Create system
    system = create_simple_system(args)

    # Create process and assign to CPU
    process = create_process(args)
    system.cpu.workload = process
    system.cpu.createThreads()

    # Instantiate system
    root = Root(full_system=False, system=system)
    m5.instantiate()

    print("Beginning simulation...")
    exit_event = m5.simulate()

    print()
    print("=" * 60)
    print(f"Simulation complete: {exit_event.getCause()}")
    print(f"Simulated time: {m5.curTick() / 1e12:.6f} seconds")
    print("=" * 60)


if __name__ == "__m5_main__":
    main()
