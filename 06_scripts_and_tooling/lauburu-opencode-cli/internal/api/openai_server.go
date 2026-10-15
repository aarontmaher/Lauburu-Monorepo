package api

import (
	"encoding/json"
	"log"
	"net/http"

	"github.com/aarontmaher/lauburu-opencode/internal/router"
)

type Server struct {
	Router *router.MoERouter
}

func NewServer(r *router.MoERouter) *Server {
	return &Server{Router: r}
}

func (s *Server) Start(addr string) error {
	http.HandleFunc("/v1/chat/completions", s.handleChatCompletions)
	log.Printf("Starting OpenAI-compatible server on %s", addr)
	return http.ListenAndServe(addr, nil)
}

func (s *Server) handleChatCompletions(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	dest := s.Router.DetermineRoute("IDE Prompt")
	
	// Mock response
	resp := map[string]interface{}{
		"id": "chatcmpl-123",
		"object": "chat.completion",
		"choices": []map[string]interface{}{
			{
				"index": 0,
				"message": map[string]string{
					"role": "assistant",
					"content": "Routed to: " + string(dest),
				},
				"finish_reason": "stop",
			},
		},
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(resp)
}
