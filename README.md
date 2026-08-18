# cryosaur

🦖 Resources and scripts for investigating ultrastructure using *in situ* cryoEM

> [!WARNING]
> `cryosaur` is primarily designed for automating analyses as part of my DPhil research, and may not be portable to other systems for various reasons (e.g. directory paths, filenaming patterns).


## Installation

```bash
uv tool install githttps://github.com/holsam/cryosaur
```

## Cluster configuration
Commands that submit work to a scheduler (`destripe-lamella`, and `trim-vol --cluster ...`) read a config file for SLURM partition, resource and module settings. If this file hasn't been created, these commands will raise an error.
```bash
# create a starter config, seeded with built-in CPU defaults for SLURM
cryosaur config init --seed slurm_cpu

# create a starter config, seeded with built-in GPU defaults for SLURM
cryosaur config init --seed slurm_gpu

# open it in $EDITOR to fill in your partition, modules, and any extra resource profiles
cryosaur config edit

# open it in specified editor to fill in your partition, modules, and any extra resource profiles
cryosaur config edit --editor <editor>

# print the current config
cryosaur config show
```

At present, the config file has one `[cluster]` table:
```toml
[cluster]
scheduler = "slurm"
default_resources = "default"      # used unless --cluster-resources overrides it

[cluster.modules]
cuda = "cuda/12.2"
relion5 = "EM/relion/5.0/2024-12-09"

[cluster.resources.default]
partition = "my-partition"
cpus_per_task = 4
mem = "16G"
time = "04:00:00"
modules = []

[cluster.resources.gpu_heavy]
partition = "my-partition"
gpus = 4
cpus_per_task = 40
mem_per_gpu = "32000M"
time = "72:00:00"
modules = ["cuda", "relion5"]
```

Any command run on a cluster uses `[cluster].default_resources` unless you pass `--cluster-resources <id>` to pick a different `[cluster.resources.<id>]` profile for that run.

## Commands

### `destripe-lamella`

Destripes per-tilt micrographs with PyLisC, then reconstructs, denoises and segments from the
cleaned images, reusing an existing RELION5 alignment.

```bash
cryosaur destripe-lamella /path/to/relion/project
cryosaur destripe-lamella /path/to/relion/project --dry-run
cryosaur destripe-lamella /path/to/relion/project --cluster-resources gpu_heavy
cryosaur destripe-lamella /path/to/relion/project --from reconstruct   # resume a partial run
```

Requires `[cluster.resources]` to be configured (see above).

### `trim-vol`

Trims reconstructed tomogram volumes using IMOD.

```bash
cryosaur trim-vol tomogram.mrc
cryosaur trim-vol tomograms_dir/ --preview          # local run, writes a comparison image
cryosaur trim-vol tomograms_dir/ --cluster slurm    # submit each volume as a SLURM job
cryosaur trim-vol tomograms_dir/ --cluster slurm --cluster-resources gpu_heavy
```

### `cryosaur utils check-tools`

Checks `PATH` for the external tools each command needs (`pylisc`, `pipeliner`, IMOD binaries, ...).

```bash
cryosaur utils check-tools
cryosaur utils check-tools destripe-lamella
```

### `cryosaur utils flatten`

Flattens a nested directory of files into one directory of symlinks (useful for tools that expect
a flat input directory).

```bash
cryosaur utils flatten nested_dir/ flat_dir/ --extension .mrc
```

## Logging

Every command accepts `-v`/`--verbose` and `-q`/`--quiet` (both stackable) to raise or lower log verbosity, and `-d`/`--directory` plus `-m`/`--mode` to control where the log file is written.