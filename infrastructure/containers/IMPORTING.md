# Shared Container Imports

Branches that reuse existing ML containers can now import images from the shared repos (`spaceport/sfm`, `spaceport/3dgs`, `spaceport/compressor`) instead of rebuilding. The GitHub Actions workflow copies manifests and layer blobs directly between ECR repositories, so importing a container simply requires that the target branch suffix repo is empty. Any change inside `infrastructure/containers/**` will still trigger a rebuild for the touched container.

The build workflow automatically decides whether to import or rebuild. No manual steps are required, but the import path assumes that the shared repositories already have a `latest` tag.
