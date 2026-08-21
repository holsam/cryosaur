# cryosaur

🦖 Resources and scripts for investigating ultrastructure using *in situ* cryoEM

> [!WARNING]
> `cryosaur` is primarily designed for automating analyses as part of my DPhil research, and may not be portable to other systems for various reasons (e.g. directory paths, filenaming patterns).

## Table of contents

- [Installation](#installation)
- [Cluster configuration](#cluster-configuration)
- [Commands](#commands)
  - [`destripe-lamella`](#destripe-lamella)
  - [`trim-vol`](#trim-vol)
  - [`cryosaur utils check-tools`](#cryosaur-utils-check-tools)
  - [`cryosaur utils flatten`](#cryosaur-utils-flatten)
- [Project (lamella annotation store)](#project-lamella-annotation-store)
  - [`cryosaur session create` / `list` / `show` / `delete`](#cryosaur-session-create--list--show--delete)
  - [`cryosaur project view`](#cryosaur-project-view)
  - [`cryosaur project annotate`](#cryosaur-project-annotate)
  - [`cryosaur project render`](#cryosaur-project-render)
  - [`cryosaur project import-toml`](#cryosaur-project-import-toml)
- [Logging](#logging)

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

Destripes per-tilt micrographs with PyLisC, then reconstructs, denoises and segments from the cleaned images, reusing an existing RELION5 alignment.

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

Flattens a nested directory of files into one directory of symlinks (useful for tools that expect a flat input directory).

```bash
cryosaur utils flatten nested_dir/ flat_dir/ --extension .mrc
```

## Project (lamella annotation store)

`cryosaur project` and `cryosaur session` manage a SQLite annotation store of sessions, lamellae, notes, points, and segmentation overlays. Requires the `project` extra:

```bash
uv tool install "cryosaur[project] @ git+https://github.com/holsam/cryosaur"
```

Every command below takes `--db-path` (default: the config's `[project] db_path`, or `project.db` next to `config.toml`).

### `cryosaur session create` / `list` / `show` / `delete`

Manage sessions without the dashboard.

```bash
cryosaur session create --name "my-session" --path raw=/data/raw --path segmentations=/data/seg
cryosaur session list
cryosaur session show <session_id>
cryosaur session delete <session_id> --yes
```

### `cryosaur project view`

Launches the local-only Streamlit dashboard for browsing sessions/lamellae, importing folders and TOML exports, filtering by name/status, and viewing overlay thumbnails.

```bash
cryosaur project view --db-path project.db
```

### `cryosaur project annotate`

Launches the PySide6/PyVista GUI for annotating lamellae (notes, points) in one session.

```bash
cryosaur project annotate --session-id <session_id>
```

### `cryosaur project render`

Extracts a surface mesh + thumbnail from segmentation output for one lamella (or every lamella in a session), caching it as an overlay.

```bash
cryosaur project render --session-id <session_id> --seg-type membrain-seg --lamella-name lam01
cryosaur project render --session-id <session_id> --seg-type membrain-seg --all
```

### `cryosaur project import-toml`

Imports a TOML export, diffing conflicting sessions/lamellae and confirming skip/replace before writing anything.

```bash
cryosaur project import-toml export.toml
cryosaur project import-toml export.toml --on-conflict replace
```

## Logging

Every command accepts `-v`/`--verbose` and `-q`/`--quiet` (both stackable) to raise or lower log verbosity, and `-d`/`--directory` plus `-m`/`--mode` to control where the log file is written.
