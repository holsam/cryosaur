'''
CRYOSAUR: binned MRC volume loading for the tomogram viewer
'''

# -- Import external dependencies
import mrcfile, numpy as np, pyvista as pv
from pathlib import Path

# -- _bin_volume: downsamples a 3D array by averaging bin_factor x bin_factor x bin_factor blocks, trimming any remainder
def _bin_volume(data: np.ndarray, bin_factor: int) -> np.ndarray:
    if bin_factor <= 1:
        return data
    trimmed_shape = tuple(dim - dim % bin_factor for dim in data.shape)
    trimmed = data[:trimmed_shape[0], :trimmed_shape[1], :trimmed_shape[2]]
    reshaped = trimmed.reshape(
        trimmed_shape[0] // bin_factor, bin_factor,
        trimmed_shape[1] // bin_factor, bin_factor,
        trimmed_shape[2] // bin_factor, bin_factor,
    )
    return reshaped.mean(axis=(1, 3, 5))

# -- load_volume: loads an MRC tomogram, downsampled by bin_factor, as a PyVista ImageData ready for volume rendering
def load_volume(path: Path, bin_factor: int = 2) -> pv.ImageData:
    '''
    Sets voxel spacing to bin_factor so rendered/picked coordinates map back to full-resolution voxel space regardless of the render-time binning
    '''
    try:
        with mrcfile.open(path, permissive=True) as mrc:
            data = mrc.data.astype(np.float32)  # shape (nz, ny, nx)
    except ValueError, RuntimeWarning as e:
        log.error(f'Could not load MRC from <cyan>{path}</cyan>: {e}')
        raise CryosaurError(f'Could not load MRC from <cyan>{path}</cyan>: {e}')

    binned = _bin_volume(data, bin_factor)
    grid = pv.ImageData(dimensions=(binned.shape[2], binned.shape[1], binned.shape[0]))
    grid.spacing = (bin_factor, bin_factor, bin_factor)
    grid.point_data['density'] = np.transpose(binned, (2, 1, 0)).flatten(order='F')
    return grid
