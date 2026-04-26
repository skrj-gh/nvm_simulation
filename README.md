# IMPORTANT
### This is a development branch, do not use this branch.

# How to:

## Clone and Initialize Repository
```bash
git clone https://github.com/skrj-gh/nvm_simulation.git
```

```bash
git submodule init
git submodule update
```

## For Intrabank migrations (LEADER implementation)
```bash
git checkout intra
cd simulator/nvmain
git checkout intra
```
### Now follow the steps mentioned in `README.md` of intra branch 


## For Interbank migration (further work)
```bash
git checkout inter
cd simulator/nvmain
git checkout inter
```
### Now follow the steps mentioned in `README.md` of inter branch


## -------------------------------------------------------------------

# NVM Simulation Toolchain (gem5 + NVMain)

This repository integrates **gem5** with **NVMain** to study non-volatile memory behavior, with a focus on **ReRAM dynamic region mapping**.

## What this project implements

- Dynamic virtual-to-physical region mapping for ReRAM in NVMain
- Region scoring and epoch-based migration in the memory controller
- Fast/slow region latency modeling at bank level
- Same-rank interbank migration support

## Current migration scope

**Supported**
- Intra-bank swaps
- Inter-bank swaps within the same channel and rank

**Not supported**
- Cross-rank migration
- Cross-channel migration

## Address translation model (high-level)

`VA -> PA -> VRA -> (VRN + offset) -> PRN -> PRA -> ReRAM row`

- CPU/MMU translates VA to PA before memory backend sees requests
- ReRAM mapper translates **virtual row regions** to **physical regions**
- Controller tracks heat by virtual ownership and triggers swaps per epoch

## Repository layout

Path: Purpose
`simulator/gem5`: gem5 source (submodule)
`simulator/nvmain`: NVMain source (submodule)
`simulator/nvmain/Config`: NVMain configs (`ReRAM_Baseline.config`, `ReRAM_DynamicMapping.config`)
`results`: Runtime output directories for benchmark runs

## Prerequisites

- Linux-like environment (recommended for scripts/tooling)
- Python 3
- SCons
- C++ toolchain (for tests and simulator build)
- Initialized submodules:

```bash
git submodule init
git submodule update
```

## Build gem5 with NVMain

> `EXTRAS=../nvmain` and `bitflip=1` are required for this project setup.


```bash
export ROOT_DIR=$(pwd)
cd $ROOT_DIR/simulator/gem5
python3 `which scons` bitflip=1 -j 8 EXTRAS=../nvmain ./build/ARM/gem5.fast
cd $ROOT_DIR
```

## Running benchmarks - SPEC CPU 2017

### Mount and install SPEC CPU 2017

**Step 1 : Mount the ISO**
```bash
sudo mkdir -p /mnt/spec2017
sudo mount -o loop,ro cpu2017-1.1.9.iso /mnt/spec2017
```

**Step 2 : Run the installer**
```bash
cd /mnt/spec2017
./install.sh -d $HOME/spec2017 -f
```
-f forces past architecture check, -d sets install destination 

**Step 3 : Confirm the install**
```bash
cd $HOME/spec2017/benchspec/CPU/
ls
```
Should list directories like: 503.bwaves_r  505.mcf_r  519.lbm_r  etc.


**Step 4 : Unmount**
```bash
sudo umount /mnt/spec2017
```

**Step 5 : Install the ARM64 cross-compiler**
```bash
sudo apt-get install -y \
    gcc-aarch64-linux-gnu \
    g++-aarch64-linux-gnu \
    gfortran-aarch64-linux-gnu
    
aarch64-linux-gnu-gcc --version
aarch64-linux-gnu-gfortran --version
```

### Create the SPEC build config

**Step 6 : Source the SPEC environment** (required before any `runcpu` command)
```bash
cd $HOME/spec2017
source shrc
```

**Step 7 : Create the cross-compile config file**
```bash
cat > $HOME/spec2017/config/gem5_aarch64_static.cfg << 'EOF'
#----------------------------------------------------------------------
# Cross-compile SPEC CPU 2017 to static AArch64 for gem5 SE mode
#----------------------------------------------------------------------
label        = gem5_aarch64_static
teeout       = yes
makeflags    = --jobs=8

CC           = aarch64-linux-gnu-gcc
CXX          = aarch64-linux-gnu-g++
FC           = aarch64-linux-gnu-gfortran

CC_VERSION_OPTION = --version 
CXX_VERSION_OPTION = --version 
FC_VERSION_OPTION = --version

# Static linking is MANDATORY for gem5 SE mode.
# SE mode has no dynamic linker, so any shared library dependency
# will cause an immediate crash at startup.
EXTRA_LDFLAGS = -static -static-libgcc -static-libstdc++

OPTIMIZE     = -O3 -march=armv8-a

CFLAGS       = $(OPTIMIZE)
CXXFLAGS     = $(OPTIMIZE)
FFLAGS       = $(OPTIMIZE)


default=base:
    PORTABILITY = -DSPEC_LP64
EOF
```

### Prepare the benchmark

**Step 8 : Building a benchmark**
```bash
cd $HOME/spec2017
source shrc      

runcpu --config=gem5_aarch64_static \
       --action=build \
       --iterations=1 \
       519.lbm_r
```

**Step 9 : Setting up a benchmark**
```bash
cd $HOME/spec2017
source shrc

runcpu --config=gem5_aarch64_static \
       --action=setup \
       --size=ref \
       519.lbm_r
```

**Step 10 — Check the exact command line SPEC expects**
```bash
BENCH=519.lbm_r
RUN_DIR=$HOME/spec2017/benchspec/CPU/$BENCH/run/run_base_refrate_gem5_aarch64_static.0000
cat $RUN_DIR/speccmds.cmd
```

This shows the exact binary name, arguments, and stdin redirection that SPEC's own harness would use — copy these exactly

For `519.lbm_r` with `ref` input this is typically:

```bash
../run_base_refrate_gem5_aarch64_static.0000/lbm_r 3000 reference.dat 0 0 100_100_130_ldc.of
```
meaning the arguments are `3000 reference.dat 0 0 100_100_130_ldc.of` and stdin is not used.


### Run the benchmark

```bash
APP=519.lbm_r
ROOT_DIR=$HOME/nvm_simulation
RUN_DIR=$HOME/spec2017/benchspec/CPU/$APP/run/run_base_refrate_gem5_aarch64_static.0000

mkdir -p $ROOT_DIR/results/$APP.d
cp $ROOT_DIR/simulator/nvmain/Config/ReRAM_DynamicMapping.config \
   $ROOT_DIR/results/$APP.d/
```

```bash
cd $RUN_DIR

nohup $ROOT_DIR/simulator/gem5/build/ARM/gem5.fast \
$ROOT_DIR/simulator/gem5/configs/deprecated/example/se.py \
--mem-type=NVMainMemory \
--nvmain-config=$ROOT_DIR/results/$APP.d/ReRAM_DynamicMapping.config \
--cpu-type=DerivO3CPU --caches --l2cache \
--l1i_size='32kB' --l1d_size='8kB' --l2_size='8kB' \
--mem-size=4GB \
-c $RUN_DIR/lbm_r_base.gem5_aarch64_static \
-o "3000 reference.dat 0 0 100_100_130_ldc.of" \
--output=$ROOT_DIR/results/$APP.d/lbm_stdout.txt \
--errout=$ROOT_DIR/results/$APP.d/lbm_stderr.txt \
> $ROOT_DIR/results/$APP.d/gem5.terminal 2>&1 &
```

- **Similarly other benchmarks can be run.**
- **Baseline results can be obtained by using `ReRAM_Baseline.config` instead of `ReRAM_DynamicMapping.config`**

## Key NVMain configs

- `simulator/nvmain/Config/ReRAM_DynamicMapping.config`
  - Dynamic mapping + migration policy knobs
- `simulator/nvmain/Config/ReRAM_Baseline.config`
  - ReRAM architecture with no migration

## Typical stats to inspect

From `gem5.terminal` after simulation:

- `regionSwaps`
- `averageLatency`
- `migrationsPerBank`
- `totalEnergy`
- `worstCaseEndurance`
- (interbank-enabled runs) migration counters for intra/inter activity

## Notes
- `results/` is runtime-generated and not part of tracked source artifacts.