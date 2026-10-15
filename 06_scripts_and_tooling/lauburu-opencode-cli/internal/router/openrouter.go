package router

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"time"

	"github.com/aarontmaher/lauburu-opencode/internal/config"
)

func CallOpenRouter(cfg *config.Config, model, systemPrompt, userPrompt string) (string, error) {
	if cfg.OpenRouterKey == "" {
		return "", fmt.Errorf("openrouter_key not set in config.yaml")
	}

	endpoint := "https://openrouter.ai/api/v1/chat/completions"
	if cfg.CloudflareGateway != "" {
		endpoint = cfg.CloudflareGateway
	}

	payload := map[string]interface{}{
		"model": model,
		"messages": []map[string]string{
			{"role": "system", "content": systemPrompt},
			{"role": "user", "content": userPrompt},
		},
	}
	body, _ := json.Marshal(payload)

	req, _ := http.NewRequest("POST", endpoint, bytes.NewBuffer(body))
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Authorization", "Bearer "+cfg.OpenRouterKey)
	req.Header.Set("HTTP-Referer", "https://github.com/aarontmaher/lauburu")
	req.Header.Set("X-Title", "Lauburu OpenCode")

	client := &http.Client{Timeout: 60 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()

	var result struct {
		Choices []struct {
			Message struct {
				Content string `json:"content"`
			} `json:"message"`
		} `json:"choices"`
	}

	b, _ := io.ReadAll(resp.Body)
	json.Unmarshal(b, &result)

	if len(result.Choices) > 0 {
		return result.Choices[0].Message.Content, nil
	}
	return "", fmt.Errorf("no response from openrouter")
}
