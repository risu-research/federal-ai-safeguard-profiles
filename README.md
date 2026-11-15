# Federal AI safeguard response profiles

Reproduction materials for *When Governments Report AI Safeguards: Organizational Patterns and the Specificity of Disclosure*, by Moon Hwan Lee (RISU Institute).

The analysis covers 227 deployed, high-impact entries in the 2025 U.S. federal AI use-case inventory. Each entry contains eight reported safeguard responses. The code groups those responses into eight-field profiles and counts pairs of entries with matching profiles.

## Reproduce the analysis

Python 3.11 or newer is sufficient. No third-party packages are required.

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
python3 src/audit_reproduction.py
python3 src/analyze_distinguishability.py
```

The commands above check the preserved row-level classifications and reproduce the tabulated results. For a complete run from the official inventory CSV, use:

```bash
python3 src/download_omb.py data/omb_original.csv
python3 src/audit_reproduction.py --csv data/omb_original.csv
python3 src/replicate_omb_original.py --csv data/omb_original.csv --output results/raw_reproduction.json
```

The download script checks the fixed Git blob hash. The audit checks the original file's SHA-256, the 227 selected row positions, both coding vectors, and the main counts. GitHub Actions runs the source-based checks on every push and pull request.

## Fixed source

- [OMB 2025 federal AI use-case inventory](https://github.com/ombegov/2025-Federal-Agency-AI-Use-Case-Inventory)
- Commit `3c225ba8438e48306ace7698c8c7feb9486cbc69`
- File `Data/2025_individually_reported_AI_use_cases.csv`
- Git blob SHA-1 `01d67daf88003eab8a0e6c2ddaf694e30c4eae7d`
- SHA-256 `a62721202ca4b110ce3c53ffdb688d05ad27a35971a7afda4f1179b2493e31d0`

The source contains 3,611 entries and 36 columns. The downloaded file is kept locally under `data/omb_original.csv` and is excluded from Git. The repository includes the 227 selected rows as coded status vectors, with agency, administrative component, and original CSV row position.

## Main results

| Entries | Strict profiles | Strict matching pairs | Broad profiles | Broad matching pairs |
| --- | ---: | ---: | ---: | ---: |
| All 227 | 27 | 7,903 / 25,651 | 17 | 8,266 / 25,651 |
| Excluding VA and DOJ (60) | 27 | 100 / 1,770 | 17 | 244 / 1,770 |
| DHS (38) | 17 | 54 / 703 | 10 | 141 / 703 |

Strict coding preserves distinctions between responses to each safeguard question. Broad coding combines categories to assess sensitivity to coding choices. Both classify **published answers**. The paper separately compares three named systems with dated public records.

## Contents

- `src/` contains data retrieval, field coding, counting, and verification scripts.
- `codebook/STRICT_BROAD_CROSSWALK.json` describes every field mapping and the order of broad coding rules.
- `codebook/OBSERVED_STRICT_TO_BROAD_CHANGES.csv` lists all 33 field-level code changes with their original row positions.
- `data/omb_227_strict_status_matrix.csv` preserves the selected rows and their strict and broad codes.
- `results/` contains the profile, agency, and pair comparisons used in the manuscript.
- `references/source_register.csv` identifies the official and published materials used for the three document comparisons.
- `verification/source_integrity_manifest.json` records the file hashes and row-level verification fingerprints.
- `tests/` contains offline tests. `.github/workflows/reproduce.yml` repeats the checks in GitHub Actions.

The scripts use deterministic rules and fixed source bytes. Any adaptation of the coding rules should be reported separately from the results reproduced here.

## Citation

The repository includes `CITATION.cff` for citing this research artifact. Please cite the official OMB inventory when using the source data.
