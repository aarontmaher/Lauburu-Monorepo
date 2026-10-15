package router

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strings"
	"sync"
	"time"

	"github.com/aarontmaher/lauburu-opencode/internal/config"
)

type Destination string

const (
	DestMasterOrchestrator Destination = "QWEN_38_MAX_LOCAL"
	DestMedicalSwarm       Destination = "MEDICAL_SWARM_PARALLEL"
	DestCloudAPI           Destination = "CLOUD_ESCALATION"
)

type MoERouter struct {
	Config     *config.Config
	HTTPClient *http.Client
}

func NewRouter(cfg *config.Config) *MoERouter {
	return &MoERouter{
		Config: cfg,
		HTTPClient: &http.Client{
			Timeout: 60 * time.Second,
		},
	}
}

func (r *MoERouter) DetermineRoute(prompt string) Destination {
	lower := strings.ToLower(prompt)

	// Medical/Biometric triggers
	if strings.Contains(lower, "heart rate") || strings.Contains(lower, "recovery") ||
		strings.Contains(lower, "hrv") || strings.Contains(lower, "ecg") ||
		strings.Contains(lower, "fatigue") {
		return DestMedicalSwarm
	}

	// Hardcoded cloud escalations
	if strings.Contains(lower, "escalate") || strings.Contains(lower, "cloud") {
		return DestCloudAPI
	}

	return DestMasterOrchestrator
}

// ------------------------------------------------------------------------
// Parallel Medical Swarm Logic
// ------------------------------------------------------------------------

type SwarmResult struct {
	Role     string
	Response string
	Error    error
}

// ExecuteMedicalSwarm runs the Tri-Orchestrator Biometric protocol.
func (r *MoERouter) ExecuteMedicalSwarm(userPrompt, telemetryJSON string) (string, error) {
	var wg sync.WaitGroup
	results := make(chan SwarmResult, 2)

	// 1. Qwen-Math: The Quantitative Analyst
	wg.Add(1)
	go func() {
		defer wg.Done()
		sys := "You are the Lauburu Quantitative Analyst (Qwen2.5-Math). Analyze the numerical arrays, standard deviations, and drifts in the provided telemetry JSON. Do not give medical advice; focus strictly on numerical anomalies."
		resp, err := r.QueryModel(fmt.Sprintf("http://127.0.0.1:%s/v1/chat/completions", r.Config.PortDevilAdvocate), "qwen2.5-math-7b", sys, fmt.Sprintf("Telemetry:\n%s\n\nPrompt: %s", telemetryJSON, userPrompt))
		results <- SwarmResult{Role: "Quant Analyst", Response: resp, Error: err}
	}()

	// 2. Meditron: The Clinical Physician
	wg.Add(1)
	go func() {
		defer wg.Done()
		sys := "You are the Lauburu Clinical Physician (Meditron). Ground the provided telemetry in PubMed literature and physiological science (e.g. sympathetic vs parasympathetic fatigue). Be highly clinical."
		resp, err := r.QueryModel(fmt.Sprintf("http://127.0.0.1:%s/v1/chat/completions", r.Config.PortSyntaxWorker), "meditron-7b", sys, fmt.Sprintf("Telemetry:\n%s\n\nPrompt: %s", telemetryJSON, userPrompt))
		results <- SwarmResult{Role: "Clinical Physician", Response: resp, Error: err}
	}()

	wg.Wait()
	close(results)

	var quantAnalysis, clinicalAnalysis string
	for res := range results {
		if res.Error != nil {
			// Log error but continue
			fmt.Printf("[Swarm Error] %s failed: %v\n", res.Role, res.Error)
			continue
		}
		if res.Role == "Quant Analyst" {
			quantAnalysis = res.Response
		} else {
			clinicalAnalysis = res.Response
		}
	}

	// 3. Llama 3.1: The Sovereign Synthesizer
	synthesisSys := "You are the Lauburu Sovereign Synthesizer (Llama-3.1-8B). You are a highly personalized health coach. Synthesize the Math analysis and the Clinical analysis into a definitive, zero-BS actionable directive for the user."
	synthesisPrompt := fmt.Sprintf(
		"User Prompt: %s\n\nRaw Telemetry: %s\n\n--- QUANT ANALYST REPORT ---\n%s\n\n--- CLINICAL PHYSICIAN REPORT ---\n%s\n\nProvide the final synthesis and actionable insight:",
		userPrompt, telemetryJSON, quantAnalysis, clinicalAnalysis,
	)

	return r.QueryModel(fmt.Sprintf("http://127.0.0.1:%s/v1/chat/completions", r.Config.PortMasterOrchestrator), "llama-3.1-8b-instruct", synthesisSys, synthesisPrompt)
}

// ------------------------------------------------------------------------
// Generic OpenAI-Compatible Caller
// ------------------------------------------------------------------------

func (r *MoERouter) QueryModel(endpoint, model, systemPrompt, userPrompt string) (string, error) {
	payload := map[string]interface{}{
		"model": model,
		"messages": []map[string]string{
			{"role": "system", "content": systemPrompt},
			{"role": "user", "content": userPrompt},
		},
		"temperature": 0.2,
	}

	body, _ := json.Marshal(payload)
	req, err := http.NewRequest("POST", endpoint, bytes.NewBuffer(body))
	if err != nil {
		return "", err
	}

	req.Header.Set("Content-Type", "application/json")
	if !r.Config.AllowTraining {
		req.Header.Set("X-OpenRouter-Allow-Training", "false") // Opt-out standard
	}

	resp, err := r.HTTPClient.Do(req)
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()

	if resp.StatusCode != 200 {
		return "", fmt.Errorf("non-200 status: %d", resp.StatusCode)
	}

	var result struct {
		Choices []struct {
			Message struct {
				Content string `json:"content"`
			} `json:"message"`
		} `json:"choices"`
	}

	b, _ := io.ReadAll(resp.Body)
	if err := json.Unmarshal(b, &result); err != nil {
		return "", err
	}

	if len(result.Choices) > 0 {
		return result.Choices[0].Message.Content, nil
	}
	return "", fmt.Errorf("empty response choices")
}

// ExecuteCloudEscalation routes the prompt to Fable/Astra and Free Tier Frontier models via OpenRouter
func (r *MoERouter) ExecuteCloudEscalation(userPrompt string) (string, error) {
	fmt.Println("☁️ Escalating to OpenRouter Frontier Models...")

	// Default to a free tier frontier or high-reasoning model available on OpenRouter
	// "fable" or "astra" hints -> we'll use a mix of available frontier tools
	models := []string{
		"google/gemini-pro",        // Free tier capable
		"anthropic/claude-3-haiku", // Extremely fast, cheap/free tiers available
		"meta-llama/llama-3-70b-instruct",
	}

	var lastErr error
	for _, model := range models {
		fmt.Printf("Attempting Cloud Route: %s\n", model)
		resp, err := CallOpenRouter(r.Config, model, "You are Lauburu Cloud Escalation (Project Astra/Fable Tier). Synthesize this request.", userPrompt)
		if err == nil && resp != "" {
			return fmt.Sprintf("[Cloud: %s]\n%s", model, resp), nil
		}
		lastErr = err
	}
	return "", fmt.Errorf("all cloud escalations failed: %v", lastErr)
}
