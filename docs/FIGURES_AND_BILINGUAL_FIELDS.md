# Figure and data conventions

The repository preserves **all 27 distinct figure subjects** in one central directory:
`outputs/figures/all_figures_png/`. Every figure is represented by **one PNG only**.

Vector versions (PDF/SVG) are available in a separate archive; they are not stored here.

The original Chinese names and addresses in CSV files are preserved. Where a CSV includes Chinese, a companion `<column>_en` column has been added. Street names are converted using explicit English labels; other names/addresses are **romanized identifiers**, not verified official English names or independently verified translations. Original raw geospatial and nested ZIP sources remain untouched. Re-running plotting scripts may generate PDF/SVG, which should be moved to the separate figure archive before committing.

This reorganization does not modify any simulation results or experiment parameters.
