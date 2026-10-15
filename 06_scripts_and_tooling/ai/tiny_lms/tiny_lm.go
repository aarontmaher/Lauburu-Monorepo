package main

import (
	"fmt"
	"math"
)

// Tiny LM built from scratch in Go
// Minimal educational matrix-based forward pass without heavy dependencies

type Config struct {
	VocabSize int
	HiddenDim int
	NumLayers int
	NumHeads  int
	SeqLen    int
}

type Weights struct {
	TokenEmbeddingTable [][]float32 // [VocabSize][HiddenDim]
	Wq                  [][]float32 // [HiddenDim][HiddenDim]
	Wk                  [][]float32 // [HiddenDim][HiddenDim]
	Wv                  [][]float32 // [HiddenDim][HiddenDim]
}

type RunState struct {
	X   [][]float32 // [SeqLen][HiddenDim]
	Q   [][]float32 // [SeqLen][HiddenDim]
	K   [][]float32 // [SeqLen][HiddenDim]
	V   [][]float32 // [SeqLen][HiddenDim]
	Att [][]float32 // [SeqLen][SeqLen]
}

func allocMatrix(rows, cols int) [][]float32 {
	m := make([][]float32, rows)
	for i := range m {
		m[i] = make([]float32, cols)
	}
	return m
}

// matmul computes out = x * w
func matmul(out, x, w [][]float32) {
	seqLen := len(x)
	inDim := len(w)
	outDim := len(w[0])
	for s := 0; s < seqLen; s++ {
		for i := 0; i < outDim; i++ {
			var val float32 = 0.0
			for j := 0; j < inDim; j++ {
				val += x[s][j] * w[j][i]
			}
			out[s][i] = val
		}
	}
}

func softmax(x []float32) {
	maxVal := x[0]
	for i := 1; i < len(x); i++ {
		if x[i] > maxVal {
			maxVal = x[i]
		}
	}
	var sum float32 = 0.0
	for i := 0; i < len(x); i++ {
		x[i] = float32(math.Exp(float64(x[i] - maxVal)))
		sum += x[i]
	}
	for i := 0; i < len(x); i++ {
		x[i] /= sum
	}
}

func forward(config *Config, weights *Weights, state *RunState, tokens []int) {
	seqLen := config.SeqLen
	dim := config.HiddenDim

	// 1. Token Embedding
	for s := 0; s < seqLen; s++ {
		token := tokens[s]
		copy(state.X[s], weights.TokenEmbeddingTable[token])
	}

	// 2. Transformer layers (Self-Attention + FFN)
	for l := 0; l < config.NumLayers; l++ {
		// Q, K, V
		matmul(state.Q, state.X, weights.Wq)
		matmul(state.K, state.X, weights.Wk)
		matmul(state.V, state.X, weights.Wv)

		// Attention
		scale := float32(math.Sqrt(float64(dim)))
		for s := 0; s < seqLen; s++ {
			for t := 0; t <= s; t++ {
				var score float32 = 0.0
				for i := 0; i < dim; i++ {
					score += state.Q[s][i] * state.K[t][i]
				}
				state.Att[s][t] = score / scale
			}
			// Mask future
			for t := s + 1; t < seqLen; t++ {
				state.Att[s][t] = -1e9
			}
			softmax(state.Att[s])
		}
		
		fmt.Printf("Layer %d forward pass simulated.\n", l)
	}
}

func main() {
	fmt.Println("Tiny LM in Go - Minimal implementation initialized.")

	config := &Config{
		VocabSize: 32000,
		HiddenDim: 256,
		NumLayers: 2,
		NumHeads:  4,
		SeqLen:    8,
	}

	// Mock weights
	weights := &Weights{
		TokenEmbeddingTable: allocMatrix(config.VocabSize, config.HiddenDim),
		Wq:                  allocMatrix(config.HiddenDim, config.HiddenDim),
		Wk:                  allocMatrix(config.HiddenDim, config.HiddenDim),
		Wv:                  allocMatrix(config.HiddenDim, config.HiddenDim),
	}

	// Mock state
	state := &RunState{
		X:   allocMatrix(config.SeqLen, config.HiddenDim),
		Q:   allocMatrix(config.SeqLen, config.HiddenDim),
		K:   allocMatrix(config.SeqLen, config.HiddenDim),
		V:   allocMatrix(config.SeqLen, config.HiddenDim),
		Att: allocMatrix(config.SeqLen, config.SeqLen),
	}

	tokens := []int{10, 20, 30, 40, 50, 60, 70, 80}
	forward(config, weights, state, tokens)
}
