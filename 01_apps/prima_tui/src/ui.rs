// ui.rs — Full TUI rendering: Ring topology, Halda monitor, benchmark, chat

use ratatui::{prelude::*, widgets::*};
use crate::{AppState, AppTab, NodeStatus, BenchmarkResult};

const TITLE_STYLE: Style = Style::new().fg(Color::Cyan).add_modifier(Modifier::BOLD);
const ACCENT: Style = Style::new().fg(Color::Magenta);
const ONLINE: Style = Style::new().fg(Color::Green);
const OFFLINE: Style = Style::new().fg(Color::Red);
const DIM: Style = Style::new().fg(Color::DarkGray);

// ─── Root Render ──────────────────────────────────────────────────────────────

pub fn render(f: &mut Frame, state: &AppState) {
    let area = f.area();
    if area.width < 10 || area.height < 5 {
        f.render_widget(
            Paragraph::new("Terminal too small. Resize to ≥ 80×24.").style(OFFLINE),
            area,
        );
        return;
    }

    // Outer vertical split: header | body | footer
    let chunks = Layout::vertical([
        Constraint::Length(3), // header tabs
        Constraint::Min(0),    // body
        Constraint::Length(3), // footer / log tail
    ]).split(area);

    render_header(f, state, chunks[0]);
    match state.tab {
        AppTab::Ring      => render_ring(f, state, chunks[1]),
        AppTab::Halda     => render_halda(f, state, chunks[1]),
        AppTab::Benchmark => render_benchmark(f, state, chunks[1]),
        AppTab::Chat      => render_chat(f, state, chunks[1]),
    }
    render_footer(f, state, chunks[2]);
}

// ─── Header / Tab Bar ─────────────────────────────────────────────────────────

fn render_header(f: &mut Frame, state: &AppState, area: Rect) {
    let online = state.nodes.iter().filter(|n| n.status == NodeStatus::Online).count();
    let total = state.nodes.len();

    let tabs = Tabs::new(vec![
        Line::from(vec![Span::raw(" ① Ring "), Span::styled("●", ONLINE)]),
        Line::from(" ② Halda "),
        Line::from(" ③ Bench "),
        Line::from(" ④ Chat  "),
    ])
    .select(match state.tab {
        AppTab::Ring => 0,
        AppTab::Halda => 1,
        AppTab::Benchmark => 2,
        AppTab::Chat => 3,
    })
    .block(Block::bordered()
        .title(Span::styled(
            format!(" prima-tui | Lauburu Mesh | {}/{} nodes online ", online, total),
            TITLE_STYLE
        ))
        .border_style(Style::default().fg(Color::Cyan)))
    .highlight_style(Style::default().fg(Color::Black).bg(Color::Cyan).bold())
    .divider("|");

    f.render_widget(tabs, area);
}

// ─── Ring Topology ────────────────────────────────────────────────────────────

fn render_ring(f: &mut Frame, state: &AppState, area: Rect) {
    let chunks = Layout::horizontal([
        Constraint::Percentage(55), // ring diagram
        Constraint::Percentage(45), // node details
    ]).split(area);

    render_ring_diagram(f, state, chunks[0]);
    render_node_details(f, state, chunks[1]);
}

fn render_ring_diagram(f: &mut Frame, state: &AppState, area: Rect) {
    let n = state.nodes.len();
    let cx = area.width as i32 / 2;
    let cy = area.height as i32 / 2;

    // Build ring ASCII art using Block + canvas-style approach via paragraph
    let mut lines: Vec<Line> = vec![];
    let header = Line::from(vec![
        Span::styled("  prima.cpp PRP Ring  ", TITLE_STYLE),
        Span::styled(format!(" world={} ", n), ACCENT),
    ]);
    lines.push(header);
    lines.push(Line::from(""));

    // Ring visualization: place nodes in a circle (text-based)
    // For 5 nodes: top, top-right, bottom-right, bottom-left, top-left
    let positions = ["    ↑   TOP   ↑   ", " → RIGHT →       ", " ↓ BOTTOM ↓      ", " ← LEFT ←       ", "  ↑ TOP-L ↑     "];

    for (i, node) in state.nodes.iter().enumerate() {
        let arrow = if i + 1 < n { "→" } else { "↺" }; // last loops back
        let next_name = &state.nodes[(i + 1) % n].spec.name;

        let status_span = Span::styled(
            format!("[{}]", node.status_symbol()),
            node.status_style(),
        );
        let rank_span = Span::styled(format!("R{}", node.spec.rank), ACCENT);
        let name_span = Span::raw(format!(" {} ", node.spec.name));
        let transport_span = Span::styled(format!("({})", node.spec.transport), DIM);
        let arrow_span = Span::styled(
            format!(" {} {} ", arrow, next_name.split(' ').next().unwrap_or("")),
            Style::default().fg(Color::Yellow),
        );

        lines.push(Line::from(vec![
            Span::raw("  "),
            status_span,
            rank_span,
            name_span,
            transport_span,
            arrow_span,
        ]));

        // Show metrics if online
        if node.status == NodeStatus::Online {
            let ttft = node.ttft_ms.map_or("--".to_string(), |t| format!("{:.0}ms", t));
            let tps  = node.tps.map_or("--".to_string(), |t| format!("{:.1}t/s", t));
            let ram  = node.ram_pct.map_or("--".to_string(), |r| format!("{:.0}%RAM", r));
            lines.push(Line::from(Span::styled(
                format!("     TTFT:{} TPS:{} {}", ttft, tps, ram),
                Style::default().fg(Color::Cyan),
            )));
        }
        if i + 1 < n {
            lines.push(Line::from(Span::styled("       │", DIM)));
        }
    }

    lines.push(Line::from(""));
    lines.push(Line::from(vec![
        Span::styled("  Model: ", DIM),
        Span::styled(state.nodes[0].spec.model_path
            .split('/').last().unwrap_or("unknown"), ACCENT),
    ]));

    let para = Paragraph::new(lines)
        .block(Block::bordered()
            .title(" Ring Topology ")
            .border_style(Style::default().fg(Color::Cyan)))
        .wrap(Wrap { trim: false });
    f.render_widget(para, area);
}

fn render_node_details(f: &mut Frame, state: &AppState, area: Rect) {
    let sel = state.selected_node.min(state.nodes.len().saturating_sub(1));

    let rows: Vec<Row> = state.nodes.iter().map(|n| {
        let status = Span::styled(
            format!(" {} ", n.status_symbol()),
            n.status_style(),
        );
        let ttft = n.ttft_ms.map_or("--".to_string(), |t| format!("{:.0}", t));
        let tps  = n.tps.map_or("--".to_string(), |t| format!("{:.1}", t));
        let lw   = n.layer_window.clone().unwrap_or_else(|| "--".to_string());
        let gpu  = n.gpu_layers.map_or("--".to_string(), |g| g.to_string());

        Row::new(vec![
            Cell::from(status),
            Cell::from(format!("R{}", n.spec.rank)),
            Cell::from(n.spec.name.split(' ').take(2).collect::<Vec<_>>().join(" ")),
            Cell::from(ttft),
            Cell::from(tps),
            Cell::from(lw),
            Cell::from(gpu),
        ])
    }).collect();

    let table = Table::new(rows, [
        Constraint::Length(3),  // status
        Constraint::Length(3),  // rank
        Constraint::Min(14),    // name
        Constraint::Length(6),  // ttft
        Constraint::Length(7),  // tps
        Constraint::Length(8),  // lw
        Constraint::Length(4),  // ngl
    ])
    .header(Row::new(vec!["", "Rk", "Node", "TTFT", "TPS", "Layers", "GPU"])
        .style(TITLE_STYLE))
    .highlight_style(Style::default().bg(Color::DarkGray))
    .block(Block::bordered()
        .title(" Node Details (← →) ")
        .border_style(Style::default().fg(Color::Cyan)));

    let mut table_state = TableState::default().with_selected(Some(sel));
    f.render_stateful_widget(table, area, &mut table_state);
}

// ─── Halda Layer Monitor ──────────────────────────────────────────────────────

fn render_halda(f: &mut Frame, state: &AppState, area: Rect) {
    let chunks = Layout::vertical([
        Constraint::Percentage(60),
        Constraint::Percentage(40),
    ]).split(area);

    // Layer bar chart (Halda assignments)
    let bars: Vec<Bar> = state.nodes.iter().map(|n| {
        let lw_val = n.layer_window.as_deref()
            .and_then(|s| s.parse::<u64>().ok())
            .unwrap_or(0);
        Bar::default()
            .value(lw_val)
            .label(Line::from(n.spec.name.split(' ').next().unwrap_or("")))
            .style(if n.status == NodeStatus::Online {
                Style::default().fg(Color::Cyan)
            } else {
                Style::default().fg(Color::DarkGray)
            })
    }).collect();

    let bar_chart = BarChart::default()
        .data(BarGroup::default().bars(&bars))
        .block(Block::bordered()
            .title(" Halda Layer Window Assignments (-lw) ")
            .border_style(Style::default().fg(Color::Cyan)))
        .bar_width(12)
        .bar_gap(2)
        .value_style(Style::default().fg(Color::Yellow).bold())
        .label_style(Style::default().fg(Color::White));

    f.render_widget(bar_chart, chunks[0]);

    // Halda detail table
    let rows: Vec<Row> = state.nodes.iter().map(|n| {
        Row::new(vec![
            Cell::from(Span::styled(format!("R{}", n.spec.rank), ACCENT)),
            Cell::from(n.spec.name.split(' ').take(2).collect::<Vec<_>>().join(" ")),
            Cell::from(n.layer_window.clone().unwrap_or_else(|| "auto".to_string())),
            Cell::from(n.gpu_layers.map_or("0".to_string(), |g| g.to_string())),
            Cell::from(n.spec.gpu_mem_gb.map_or("--".to_string(), |g| format!("{:.0}GB", g))),
            Cell::from(n.spec.transport.as_str()),
            Cell::from(n.ram_pct.map_or("--".to_string(), |r| format!("{:.0}%", r))),
            Cell::from(n.spec.role.as_str()),
        ])
    }).collect();

    let table = Table::new(rows, [
        Constraint::Length(3),
        Constraint::Min(16),
        Constraint::Length(7),
        Constraint::Length(4),
        Constraint::Length(7),
        Constraint::Min(14),
        Constraint::Length(6),
        Constraint::Length(8),
    ])
    .header(Row::new(vec!["Rk", "Node", "-lw", "-ngl", "VRAM", "Transport", "RAM%", "Role"])
        .style(TITLE_STYLE))
    .block(Block::bordered()
        .title(" Halda Workload Distribution | prima.cpp Auto-Scheduler ")
        .border_style(Style::default().fg(Color::Cyan)));

    f.render_widget(table, chunks[1]);
}

// ─── 5-Framework Benchmark ────────────────────────────────────────────────────

fn render_benchmark(f: &mut Frame, state: &AppState, area: Rect) {
    let chunks = Layout::vertical([
        Constraint::Percentage(65),
        Constraint::Percentage(35),
    ]).split(area);

    // Results table
    let rows: Vec<Row> = if state.benchmark_results.is_empty() {
        vec![Row::new(vec![
            Cell::from("--"),
            Cell::from("No results yet — press [b] to benchmark"),
            Cell::from("--"),
            Cell::from("--"),
        ])]
    } else {
        // Show latest result per framework
        let mut latest: std::collections::HashMap<String, &BenchmarkResult> = std::collections::HashMap::new();
        for r in &state.benchmark_results {
            latest.insert(r.framework.clone(), r);
        }

        // Sort by TTFT ascending
        let mut sorted: Vec<&BenchmarkResult> = latest.values().cloned().collect();
        sorted.sort_by(|a, b| a.ttft_ms.partial_cmp(&b.ttft_ms).unwrap_or(std::cmp::Ordering::Equal));

        sorted.iter().enumerate().map(|(i, r)| {
            let medal = match i { 0 => "🥇", 1 => "🥈", 2 => "🥉", _ => "  " };
            let ttft_style = if i == 0 { ONLINE } else { Style::default() };
            let tps_style  = if r.tps > 20.0 { ONLINE } else if r.tps > 5.0 { Style::default().fg(Color::Yellow) } else { OFFLINE };

            Row::new(vec![
                Cell::from(format!("{} {}", medal, r.framework)).style(if i == 0 { ONLINE } else { Style::default() }),
                Cell::from(format!("{:.0}ms", r.ttft_ms)).style(ttft_style),
                Cell::from(format!("{:.1}", r.tps)).style(tps_style),
                Cell::from(r.transport.as_str()),
                Cell::from(r.timestamp.format("%H:%M:%S").to_string()),
            ])
        }).collect()
    };

    let table = Table::new(rows, [
        Constraint::Min(20),    // framework
        Constraint::Length(9),  // ttft
        Constraint::Length(7),  // tps
        Constraint::Min(20),    // transport
        Constraint::Length(9),  // time
    ])
    .header(Row::new(vec!["Framework", "TTFT", "TPS", "Transport", "Time"])
        .style(TITLE_STYLE))
    .block(Block::bordered()
        .title(" 5-Framework AgentWorld Benchmark | [b] re-run ")
        .border_style(Style::default().fg(Color::Cyan)));

    f.render_widget(table, chunks[0]);

    // Framework feature comparison matrix
    let feature_lines = vec![
        Line::from(vec![
            Span::styled("  prima.cpp   ", Style::default().fg(Color::Cyan).bold()),
            Span::raw("PRP ring, Halda auto-scheduler, <10% memory pressure, phones+Mac+Linux+Android"),
        ]),
        Line::from(vec![
            Span::styled("  llama.cpp   ", Style::default().fg(Color::Green)),
            Span::raw("TB4 DMA 0.52ms, RPC sharding, Metal/CUDA, best single-node speed"),
        ]),
        Line::from(vec![
            Span::styled("  Accelerate  ", Style::default().fg(Color::Yellow)),
            Span::raw("HuggingFace FSDP, training-first, bf16, PyTorch native, best for LoRA"),
        ]),
        Line::from(vec![
            Span::styled("  Exo P2P     ", Style::default().fg(Color::Magenta)),
            Span::raw("Decentralized, no coordinator, ring/pipeline, Tailscale-native"),
        ]),
        Line::from(vec![
            Span::styled("  Petals DHT  ", Style::default().fg(Color::Blue)),
            Span::raw("BitTorrent-style DHT, very large model support, public + private nodes"),
        ]),
    ];

    let para = Paragraph::new(feature_lines)
        .block(Block::bordered()
            .title(" Framework Feature Matrix ")
            .border_style(Style::default().fg(Color::Cyan)))
        .wrap(Wrap { trim: false });

    f.render_widget(para, chunks[1]);
}

// ─── Chat Panel ───────────────────────────────────────────────────────────────

fn render_chat(f: &mut Frame, state: &AppState, area: Rect) {
    let chunks = Layout::vertical([
        Constraint::Min(0),    // history
        Constraint::Length(3), // input box
    ]).split(area);

    // Chat history
    let mut lines: Vec<Line> = vec![];
    for (role, content) in &state.chat_history {
        let (prefix, style) = if role == "user" {
            ("YOU  │ ", Style::default().fg(Color::Cyan).bold())
        } else {
            ("AGNT │ ", Style::default().fg(Color::Green))
        };
        for (i, chunk) in content.chars().collect::<Vec<_>>().chunks(area.width as usize - 10).enumerate() {
            let text: String = chunk.iter().collect();
            if i == 0 {
                lines.push(Line::from(vec![
                    Span::styled(prefix, style),
                    Span::styled(text, style),
                ]));
            } else {
                lines.push(Line::from(vec![
                    Span::raw("     │ "),
                    Span::styled(text, style),
                ]));
            }
        }
        lines.push(Line::from(""));
    }

    // Streaming buffer
    if state.chat_streaming && !state.stream_buffer.is_empty() {
        lines.push(Line::from(vec![
            Span::styled("AGNT │ ", Style::default().fg(Color::Green)),
            Span::styled(
                format!("{}▊", state.stream_buffer.chars().take(area.width as usize - 12).collect::<String>()),
                Style::default().fg(Color::Green),
            ),
        ]));
    } else if state.chat_streaming {
        lines.push(Line::from(Span::styled("AGNT │ ▊", Style::default().fg(Color::DarkGray))));
    }

    // Auto-scroll to bottom
    let total_lines = lines.len();
    let visible = chunks[0].height as usize - 2;
    let offset = total_lines.saturating_sub(visible);

    let para = Paragraph::new(lines)
        .block(Block::bordered()
            .title(format!(" Chat — prima.cpp {} ", state.master_url))
            .border_style(Style::default().fg(Color::Cyan)))
        .scroll((offset as u16, 0));
    f.render_widget(para, chunks[0]);

    // Input box
    let cursor = if state.chat_streaming { "⏳" } else { "▌" };
    let input_para = Paragraph::new(Line::from(vec![
        Span::styled("❯ ", Style::default().fg(Color::Cyan).bold()),
        Span::raw(&state.chat_input),
        Span::styled(cursor, Style::default().fg(Color::Cyan)),
    ]))
    .block(Block::bordered()
        .title(" [Enter] send | [Tab] switch panel ")
        .border_style(if state.chat_streaming {
            Style::default().fg(Color::Yellow)
        } else {
            Style::default().fg(Color::Cyan)
        }));
    f.render_widget(input_para, chunks[1]);
}

// ─── Footer / Log Tail ────────────────────────────────────────────────────────

fn render_footer(f: &mut Frame, state: &AppState, area: Rect) {
    let last_log = state.log_lines.last()
        .map(|s| s.as_str())
        .unwrap_or("Waiting for data...");

    let online = state.nodes.iter().filter(|n| n.status == NodeStatus::Online).count();
    let n = state.nodes.len();

    let para = Paragraph::new(Line::from(vec![
        Span::styled("⚡ ", Style::default().fg(Color::Cyan)),
        Span::raw(last_log),
        Span::styled(
            format!("  [{}/{}] [b]bench [q]quit [Tab]switch", online, n),
            DIM,
        ),
    ]))
    .block(Block::bordered()
        .border_style(Style::default().fg(Color::DarkGray)));

    f.render_widget(para, area);
}
