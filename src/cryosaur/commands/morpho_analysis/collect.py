'''
CRYOSAUR: file collection, prefixing and pairing for morpho-analysis
'''

# -- Import external dependencies
import re
from pathlib import Path

# -- Define globs and prefix-segment patterns
TOMOGRAM_GLOB = 'processed/raw*/relion_murfey/Tomograms/job*/tomograms/*.mrc'
SEGMENTATION_GLOB = 'processed/raw*/relion_murfey/Segmentation/job*/tomograms/*.mrc'
RAW_DIR_RE = re.compile(r'^raw\d*$')  # matches e.g. "raw", "raw2", "raw12"
JOB_DIR_RE = re.compile(r'^job\d+$')

# -- find_files: returns all .mrc files under root matching the given glob pattern
def find_files(root: Path, glob_pattern: str) -> list[Path]:
    return sorted(root.glob(glob_pattern))

# -- _dir_parts: returns the raw<N> and job<NNN> segment names found in file_path's parents (up to root), or (None, None) if absent
def _dir_parts(root: Path, file_path: Path) -> tuple[str | None, str | None]:
    raw_part = None
    job_part = None
    for parent in file_path.parents:
        if RAW_DIR_RE.match(parent.name):
            raw_part = parent.name
        if JOB_DIR_RE.match(parent.name):
            job_part = parent.name
        if parent == root:
            break
    return raw_part, job_part

# -- build_prefix: builds a collision-avoiding prefix from the root name, raw<N> segment, and job<NNN> segment found in file_path's parents
def build_prefix(root: Path, file_path: Path) -> str:
    raw_part, job_part = _dir_parts(root, file_path)
    return f'{root.name}_{raw_part or "raw"}_{job_part or "jobUNK"}'

# -- collect: returns (tomograms, segmentations), each a list of (file_path, prefixed_stem)
def collect(roots: list[Path]) -> tuple[list[tuple[Path, str]], list[tuple[Path, str]]]:
    tomograms = []
    segmentations = []
    for root in roots:
        for f in find_files(root, TOMOGRAM_GLOB):
            prefix = build_prefix(root, f)
            tomograms.append((f, f'{prefix}_{f.stem}'))
        for f in find_files(root, SEGMENTATION_GLOB):
            prefix = build_prefix(root, f)
            segmentations.append((f, f'{prefix}_{f.stem}'))
    return tomograms, segmentations

# -- summarise_counts: returns per (root, raw<N>) tomogram/segmentation counts, for display before symlinking
def summarise_counts(roots: list[Path]) -> list[tuple[str, str, int, int]]:
    counts: dict[tuple[str, str], list[int]] = {}
    for root in roots:
        for f in find_files(root, TOMOGRAM_GLOB):
            raw_part, _ = _dir_parts(root, f)
            key = (root.name, raw_part or 'raw')
            counts.setdefault(key, [0, 0])[0] += 1
        for f in find_files(root, SEGMENTATION_GLOB):
            raw_part, _ = _dir_parts(root, f)
            key = (root.name, raw_part or 'raw')
            counts.setdefault(key, [0, 0])[1] += 1
    return [(root_name, raw_part, n_tomo, n_seg) for (root_name, raw_part), (n_tomo, n_seg) in sorted(counts.items())]

# -- strip_segmentation_suffix: removes the _denoised_segmented suffix (if present) for pairing comparison
def strip_segmentation_suffix(stem: str) -> str:
    return re.sub(r'_denoised_segmented$', '', stem)

# -- pair_files: matches each tomogram to its segmentation by original stem, returning their (prefixed) symlink stems
def pair_files(tomograms: list[tuple[Path, str]], segmentations: list[tuple[Path, str]]) -> list[tuple[str, str]]:
    seg_by_stem = {strip_segmentation_suffix(orig.stem): prefixed_stem for orig, prefixed_stem in segmentations}
    return [
        (prefixed_stem, seg_by_stem[orig.stem])
        for orig, prefixed_stem in tomograms
        if orig.stem in seg_by_stem
    ]

# -- make_symlinks: symlinks each (orig, prefixed_stem) pair into target_dir, replacing any existing link
def make_symlinks(files: list[tuple[Path, str]], target_dir: Path) -> None:
    target_dir.mkdir(parents=True, exist_ok=True)
    for orig, prefixed_stem in files:
        link_path = target_dir / f'{prefixed_stem}{orig.suffix}'
        if link_path.exists() or link_path.is_symlink():
            link_path.unlink()
        link_path.symlink_to(orig.resolve())
