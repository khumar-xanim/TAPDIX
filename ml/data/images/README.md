# Photos

One folder per problem type: `images/<category>/<problem_type>/<file>.jpg` (create the skeleton with
`python -m tapdix_ml.data.index_photos --init`). Folder names are the labels - put a photo in the folder that
describes what is wrong, then run `python -m tapdix_ml.data.index_photos` to build `ml/data/photos_index.csv`
(path, label, sha256) - those paths are the links used in the tabular data.

Rules before a photo may be used for training:
1. Consent from whoever took/owns it (customers: the `ml_training_consent` flag; masters: portfolio terms).
2. Remove EXIF (it can contain GPS) and blur faces, documents, number plates, addresses.
3. No duplicates (the indexer rejects identical files).
Photos are git-ignored on purpose (size + privacy); keep them in object storage / DVC.
