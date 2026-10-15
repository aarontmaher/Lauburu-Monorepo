# Mesh Binaries

This folder is synced across all Lauburu mesh devices via Syncthing.
When `DEPLOY_MESH.sh` is run on a node, it will copy the appropriate binaries from here into the node's `~/.local/bin/` folder before launching the services.

Drop the `prima-worker` executable for your architecture (compiled from the custom `prima.cpp` ring sharding fork) into this folder. It will then automatically deploy across the mesh!
