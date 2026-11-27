# Canon full-frame photography lenses

The collection includes 18 native `os-optics` Projects from 10 Canon patent publications. Each
record names its direct publication, numerical example and configuration. The batch manifest lists
which of the 31 considered inputs became records. [Series issue #9](https://github.com/JunLin615/os-optics-lens/issues/9)

Six records represent a single end of a zoom. The remaining twelve are fixed-focal-length designs.
Each Project uses the infinite-conjugate spacings. Paraxial EFL and BFL use the native Project's
stored vacuum wavelength of 587.56 nm, which retains the numerical value of the published d-line in
air.

## Materials and apertures

The Projects use Sellmeier models fitted to a Cauchy curve through the printed d-line index and
Abbe number. The intake scaled the model index by 1.0002772 to account for the Engine's air
convention. The fit interval is a modeling condition. Continuous spectral coverage is unconfirmed.

The stop opening is solved against the printed f-number. Clear semi-diameters come from a
paraxial meridional ray envelope and the allowance documented in each record. Stop-dependent
constraints remain unconfirmed.

## Field traces

Each record retains the image height and chief-ray angle for seven real meridional chief rays
through the committed Project, at 30%, 50%, 70%, 85%, 90%, 95% and 100% of the patent's stated
half field. The trace records the wavelength and conjugate. The source half field sets the
sampling limit, and the full-frame facet describes the intended patent-example format. The
trace measures chief-ray landing positions on the modeled image plane. Usable image-circle
coverage and image quality remain unconfirmed.

Run `python scripts/check_intake.py --base origin/main` with `os-optics==0.14.0` to verify the
native Project and its EFL and BFL. The Canon collection tests also check record and Project
hashes, manifest membership and the search projection of the retained field data.
