package mesh

import (
	"log"
	"runtime"
)

type NodeRole string

const (
	RoleWorker NodeRole = "WORKER"
	RoleClient NodeRole = "CLIENT"
)

func ProfileHardware() NodeRole {
	// Simple heuristic: If we have > 16GB of logical RAM and arm64 (Metal) or amd64, we might be a worker.
	// For production, we'd query actual VRAM.
	var memStats runtime.MemStats
	runtime.ReadMemStats(&memStats)

	log.Printf("Hardware Profiler: OS=%s Arch=%s", runtime.GOOS, runtime.GOARCH)

	// Placeholder logic
	if runtime.GOARCH == "arm64" {
		return RoleClient // Just default to client for safety unless explicitly configured
	}
	
	return RoleClient
}
