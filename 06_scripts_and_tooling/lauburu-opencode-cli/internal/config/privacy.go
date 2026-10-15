package config

import (
	"os"
	"path/filepath"
	"gopkg.in/yaml.v3"
)

type Config struct {
	AllowTraining            bool   `yaml:"allow_training"`
	AuthKey                  string `yaml:"tailscale_auth_key"`
	ModelDir                 string `yaml:"model_dir"`
	OpenRouterKey            string `yaml:"openrouter_key"`
	CloudflareGateway        string `yaml:"cloudflare_gateway"`
	PortMasterOrchestrator   string `yaml:"port_master_orchestrator"`
	PortDevilAdvocate        string `yaml:"port_devil_advocate"`
	PortSyntaxWorker         string `yaml:"port_syntax_worker"`
}

func LoadConfig() (*Config, error) {
	home, err := os.UserHomeDir()
	if err != nil {
		return nil, err
	}
	
	path := filepath.Join(home, ".lauburu", "config.yaml")
	
	// Defaults aligned with Rule 8 Sovereign Mesh Hierarchy
	cfg := &Config{
		AllowTraining:            true,
		ModelDir:                 filepath.Join(home, "DFS_UNIFIED", "Lauburu-Monorepo", "02_ai_models_and_inference", "gguf_vault"),
		PortMasterOrchestrator:   "8082", // Qwen 3.8 Max (Sovereign Local Orchestrator)
		PortDevilAdvocate:        "8083", // Qwen 3.8 Max 27B Abliterated (Adversarial Red Team)
		PortSyntaxWorker:         "8081", // Qwen 2.5 Coder 7B (Subordinate Worker ONLY)
		CloudflareGateway:        "https://gateway.ai.cloudflare.com/v1/lauburu/openrouter", // Default gateway format
	}
	
	data, err := os.ReadFile(path)
	if err == nil {
		_ = yaml.Unmarshal(data, cfg)
	} else {
		// Create the directory and file if it doesn't exist
		os.MkdirAll(filepath.Dir(path), 0755)
		out, _ := yaml.Marshal(cfg)
		os.WriteFile(path, out, 0644)
	}
	return cfg, nil
}
