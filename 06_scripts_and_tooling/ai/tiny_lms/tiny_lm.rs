// Tiny LM built from scratch in Rust
// Minimal boilerplate using standard library vectors for a single forward pass layer

#[derive(Debug)]
struct Config {
    vocab_size: usize,
    hidden_dim: usize,
    num_layers: usize,
    num_heads: usize,
    seq_len: usize,
}

struct Weights {
    token_embedding: Vec<f32>, // (vocab_size * hidden_dim)
    wq: Vec<f32>,              // (hidden_dim * hidden_dim)
    wk: Vec<f32>,
    wv: Vec<f32>,
}

struct RunState {
    x: Vec<f32>,
    q: Vec<f32>,
    k: Vec<f32>,
    v: Vec<f32>,
    att: Vec<f32>,
}

fn matmul(out: &mut [f32], x: &[f32], w: &[f32], seq_len: usize, in_dim: usize, out_dim: usize) {
    for s in 0..seq_len {
        for i in 0..out_dim {
            let mut val = 0.0;
            for j in 0..in_dim {
                val += x[s * in_dim + j] * w[j * out_dim + i];
            }
            out[s * out_dim + i] = val;
        }
    }
}

fn softmax(x: &mut [f32]) {
    let mut max_val = x[0];
    for &val in x.iter() {
        if val > max_val {
            max_val = val;
        }
    }
    let mut sum = 0.0;
    for val in x.iter_mut() {
        *val = (*val - max_val).exp();
        sum += *val;
    }
    for val in x.iter_mut() {
        *val /= sum;
    }
}

fn forward(config: &Config, weights: &Weights, state: &mut RunState, tokens: &[usize]) {
    let seq = config.seq_len;
    let dim = config.hidden_dim;

    // 1. Token Embedding
    for s in 0..seq {
        let token = tokens[s];
        for i in 0..dim {
            state.x[s * dim + i] = weights.token_embedding[token * dim + i];
        }
    }

    // 2. Transformer layers (Self-Attention + FFN)
    for l in 0..config.num_layers {
        matmul(&mut state.q, &state.x, &weights.wq, seq, dim, dim);
        matmul(&mut state.k, &state.x, &weights.wk, seq, dim, dim);
        matmul(&mut state.v, &state.x, &weights.wv, seq, dim, dim);

        let scale = (dim as f32).sqrt();
        
        for s in 0..seq {
            for t in 0..=s {
                let mut score = 0.0;
                for i in 0..dim {
                    score += state.q[s * dim + i] * state.k[t * dim + i];
                }
                state.att[s * seq + t] = score / scale;
            }
            for t in (s + 1)..seq {
                state.att[s * seq + t] = -1e9;
            }
            let start = s * seq;
            softmax(&mut state.att[start..(start + seq)]);
        }

        println!("Layer {} forward pass simulated.", l);
    }
}

fn main() {
    println!("Tiny LM in Rust - Minimal implementation initialized.");

    let config = Config {
        vocab_size: 32000,
        hidden_dim: 256,
        num_layers: 2,
        num_heads: 4,
        seq_len: 8,
    };

    let weights = Weights {
        token_embedding: vec![0.01; config.vocab_size * config.hidden_dim],
        wq: vec![0.02; config.hidden_dim * config.hidden_dim],
        wk: vec![0.03; config.hidden_dim * config.hidden_dim],
        wv: vec![0.04; config.hidden_dim * config.hidden_dim],
    };

    let mut state = RunState {
        x: vec![0.0; config.seq_len * config.hidden_dim],
        q: vec![0.0; config.seq_len * config.hidden_dim],
        k: vec![0.0; config.seq_len * config.hidden_dim],
        v: vec![0.0; config.seq_len * config.hidden_dim],
        att: vec![0.0; config.seq_len * config.seq_len],
    };

    let tokens = vec![10, 20, 30, 40, 50, 60, 70, 80];
    forward(&config, &weights, &mut state, &tokens);
}
