package inference

import (
	"log"
	"os"
	"os/exec"
	"strings"
)

type PrimaManager struct {
	BinaryPath string
	ModelPath  string
	Cmd        *exec.Cmd
}

func NewPrimaManager(binaryPath, modelPath string) *PrimaManager {
	return &PrimaManager{
		BinaryPath: binaryPath,
		ModelPath:  modelPath,
	}
}

func (pm *PrimaManager) Start() error {
	if _, err := os.Stat(pm.BinaryPath); os.IsNotExist(err) {
		log.Printf("prima.cpp not found at %s, will skip local inference startup", pm.BinaryPath)
		return nil
	}

	pm.Cmd = exec.Command(pm.BinaryPath, "-m", pm.ModelPath, "--port", "8080")
	pm.Cmd.Stdout = os.Stdout
	pm.Cmd.Stderr = os.Stderr

	log.Printf("Starting prima.cpp with model %s", pm.ModelPath)
	return pm.Cmd.Start()
}

func (pm *PrimaManager) Stop() {
	if pm.Cmd != nil && pm.Cmd.Process != nil {
		pm.Cmd.Process.Kill()
	}
}

func (pm *PrimaManager) StartWithSharding(rpcEndpoints []string) error {
	args := []string{"-m", pm.ModelPath, "--port", "8080"}
	if len(rpcEndpoints) > 0 {
		args = append(args, "--rpc")
		args = append(args, strings.Join(rpcEndpoints, ","))
		log.Printf("🔥 Initializing Long-Distance PRP Sharding across: %v", rpcEndpoints)
	}
	pm.Cmd = exec.Command(pm.BinaryPath, args...)
	pm.Cmd.Stdout = os.Stdout
	pm.Cmd.Stderr = os.Stderr
	return pm.Cmd.Start()
}
