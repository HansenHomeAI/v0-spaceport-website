# Shared Container Imports

Branches that reuse existing ML containers can now import images from the shared repos (`spaceport/sfm`, `spaceport/3dgs`, `spaceport/compressor`) instead of rebuilding. The GitHub Actions workflow copies manifests and layer blobs directly between ECR repositories, so importing a container simply requires that the target branch suffix repo is empty. Any change inside `infrastructure/containers/**` will still trigger a rebuild for the touched container.

The build workflow automatically decides whether to import or rebuild. No manual steps are required, but the import path assumes that the shared repositories already have a `latest` tag.

## Single-container build expectation

The GitHub Actions workflow only builds containers whose own folders changed. If you touch multiple container folders in the same commit, it will build each touched container. To keep runs cheap and fast, scope a given commit/PR to a single container; otherwise explicitly trigger a single-container build via the `container` input on the workflow dispatch. Avoid ever editing multiple container directories in one change set unless you truly intend multiple builds.
