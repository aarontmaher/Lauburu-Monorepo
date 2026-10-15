package process

import (
	"fmt"
	"os/exec"
	"time"
)

func StartMLXSupervisor() {
	cmd := exec.Command("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/02_ai_models_and_inference/antigravity_replacement_trainer_daemon.sh")
	err := cmd.Start()
	if err != nil {
		fmt.Println("Failed to start MLX Trainer:", err)
		return
	}
	for {
		time.Sleep(10 * time.Second)
	}
}
