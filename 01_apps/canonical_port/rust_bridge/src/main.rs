use ratatui::{
    backend::{Backend, CrosstermBackend, TestBackend},
    layout::{Constraint, Direction, Layout},
    style::{Color, Modifier, Style},
    text::{Line, Span},
    widgets::{Block, Borders, Paragraph, Row, Table},
    Frame, Terminal,
};
use crossterm::{
    event::{self, DisableMouseCapture, EnableMouseCapture, Event, KeyCode},
    execute,
    terminal::{disable_raw_mode, enable_raw_mode, EnterAlternateScreen, LeaveAlternateScreen},
};
use std::{
    error::Error,
    io::{self, Write},
    panic,
    time::{Duration, Instant},
};

fn setup_panic_hook() {
    panic::set_hook(Box::new(|info| {
        let _ = disable_raw_mode();
        let _ = execute!(
            io::stdout(),
            LeaveAlternateScreen,
            crossterm::cursor::Show
        );
        eprintln!("Panic: {}", info);
    }));
}

fn main() -> Result<(), Box<dyn Error>> {
    setup_panic_hook();

    let stdout = io::stdout();
    let is_tty = std::io::IsTerminal::is_terminal(&stdout);

    if is_tty {
        enable_raw_mode()?;
        let mut stdout = io::stdout();
        execute!(stdout, EnterAlternateScreen, EnableMouseCapture)?;
        
        let backend = CrosstermBackend::new(stdout);
        let mut terminal = Terminal::new(backend)?;
        
        let tick_rate = Duration::from_millis(16); // ~60fps
        let res = run_app_crossterm(&mut terminal, tick_rate);

        disable_raw_mode()?;
        execute!(
            terminal.backend_mut(),
            LeaveAlternateScreen,
            DisableMouseCapture
        )?;
        terminal.show_cursor()?;

        if let Err(err) = res {
            eprintln!("{:?}", err);
        }
    } else {
        // Not a TTY, pipe mode using TestBackend
        let backend = TestBackend::new(100, 30);
        let mut terminal = Terminal::new(backend)?;
        
        let tick_rate = Duration::from_millis(32); // ~30fps for pipe
        let res = run_app_pipe(&mut terminal, tick_rate);
        
        if let Err(err) = res {
            eprintln!("{:?}", err);
        }
    }

    Ok(())
}

fn run_app_crossterm<B: Backend>(terminal: &mut Terminal<B>, tick_rate: Duration) -> io::Result<()> {
    let mut last_tick = Instant::now();
    let mut iter_count = 0;

    loop {
        terminal.draw(|f| ui(f, iter_count))?;

        let timeout = tick_rate
            .checked_sub(last_tick.elapsed())
            .unwrap_or_else(|| Duration::from_secs(0));

        if event::poll(timeout)? {
            if let Event::Key(key) = event::read()? {
                if let KeyCode::Char('q') = key.code {
                    return Ok(());
                }
            }
        }

        if last_tick.elapsed() >= tick_rate {
            iter_count += 1;
            last_tick = Instant::now();
        }
    }
}

fn color_to_ansi(color: Color, is_bg: bool) -> String {
    let base = if is_bg { 48 } else { 38 };
    match color {
        Color::Reset => String::from(if is_bg { "\x1b[49m" } else { "\x1b[39m" }),
        Color::Black => String::from(if is_bg { "\x1b[40m" } else { "\x1b[30m" }),
        Color::Red => String::from(if is_bg { "\x1b[41m" } else { "\x1b[31m" }),
        Color::Green => String::from(if is_bg { "\x1b[42m" } else { "\x1b[32m" }),
        Color::Yellow => String::from(if is_bg { "\x1b[43m" } else { "\x1b[33m" }),
        Color::Blue => String::from(if is_bg { "\x1b[44m" } else { "\x1b[34m" }),
        Color::Magenta => String::from(if is_bg { "\x1b[45m" } else { "\x1b[35m" }),
        Color::Cyan => String::from(if is_bg { "\x1b[46m" } else { "\x1b[36m" }),
        Color::Gray => String::from(if is_bg { "\x1b[47m" } else { "\x1b[37m" }),
        Color::DarkGray => String::from(if is_bg { "\x1b[100m" } else { "\x1b[90m" }),
        Color::LightRed => String::from(if is_bg { "\x1b[101m" } else { "\x1b[91m" }),
        Color::LightGreen => String::from(if is_bg { "\x1b[102m" } else { "\x1b[92m" }),
        Color::LightYellow => String::from(if is_bg { "\x1b[103m" } else { "\x1b[93m" }),
        Color::LightBlue => String::from(if is_bg { "\x1b[104m" } else { "\x1b[94m" }),
        Color::LightMagenta => String::from(if is_bg { "\x1b[105m" } else { "\x1b[95m" }),
        Color::LightCyan => String::from(if is_bg { "\x1b[106m" } else { "\x1b[96m" }),
        Color::White => String::from(if is_bg { "\x1b[107m" } else { "\x1b[97m" }),
        Color::Rgb(r, g, b) => format!("\x1b[{};2;{};{};{}m", base, r, g, b),
        Color::Indexed(i) => format!("\x1b[{};5;{}m", base, i),
    }
}

fn run_app_pipe(terminal: &mut Terminal<TestBackend>, tick_rate: Duration) -> io::Result<()> {
    let mut iter_count = 0;
    
    loop {
        let start = Instant::now();
        terminal.draw(|f| ui(f, iter_count))?;
        
        let buffer = terminal.backend().buffer();
        let mut out = String::new();
        out.push_str("---FRAME---\n");
        
        for y in 0..buffer.area.height {
            let mut last_fg = Color::Reset;
            let mut last_bg = Color::Reset;
            let mut last_mod = ratatui::style::Modifier::empty();
            
            for x in 0..buffer.area.width {
                let cell = buffer.cell((x, y)).unwrap();
                
                let mut style_changed = false;
                
                if cell.fg != last_fg || cell.bg != last_bg || cell.modifier != last_mod {
                    style_changed = true;
                    last_fg = cell.fg;
                    last_bg = cell.bg;
                    last_mod = cell.modifier;
                }
                
                if style_changed {
                    out.push_str("\x1b[0m"); // reset first
                    if last_fg != Color::Reset {
                        out.push_str(&color_to_ansi(last_fg, false));
                    }
                    if last_bg != Color::Reset {
                        out.push_str(&color_to_ansi(last_bg, true));
                    }
                    if last_mod.contains(ratatui::style::Modifier::BOLD) {
                        out.push_str("\x1b[1m");
                    }
                    if last_mod.contains(ratatui::style::Modifier::ITALIC) {
                        out.push_str("\x1b[3m");
                    }
                    if last_mod.contains(ratatui::style::Modifier::UNDERLINED) {
                        out.push_str("\x1b[4m");
                    }
                }
                
                out.push_str(cell.symbol());
            }
            out.push_str("\x1b[0m\n");
        }
        
        print!("{}", out);
        io::stdout().flush()?;
        
        iter_count += 1;
        
        let elapsed = start.elapsed();
        if elapsed < tick_rate {
            std::thread::sleep(tick_rate - elapsed);
        }
        
        // Stop after 200 frames for headless tests
        if iter_count > 200 {
            break;
        }
    }
    
    Ok(())
}

fn ui(f: &mut Frame, iter_count: u64) {
    let size = f.area();
    
    if size.width < 10 || size.height < 5 {
        let block = Block::default().borders(Borders::ALL).title("Error");
        let p = Paragraph::new("Screen too small").block(block);
        f.render_widget(p, size);
        return;
    }

    let chunks = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Length(3),
            Constraint::Min(0),
        ])
        .split(size);

    let title_block = Block::default()
        .borders(Borders::ALL)
        .style(Style::default().fg(Color::Cyan));
    let title = Paragraph::new(Line::from(vec![
        Span::styled(" Lauburu Polyglot TUI Bridge ", Style::default().add_modifier(Modifier::BOLD)),
        Span::raw(format!("| FPS: ~60 | Frame: {} ", iter_count)),
    ]))
    .block(title_block);
    f.render_widget(title, chunks[0]);

    let mesh_chunks = Layout::default()
        .direction(Direction::Horizontal)
        .constraints([Constraint::Percentage(50), Constraint::Percentage(50)])
        .split(chunks[1]);

    let mesh_stats = vec![
        Row::new(vec!["L1", "Mac_Node", "192.168.8.230", "24.0 GB", "--"]),
        Row::new(vec!["L2", "MacBook_Pro", "192.168.8.127", "16.0 GB", "[DISCONNECTED]"]),
        Row::new(vec!["L3", "Linux_Mini", "192.168.8.224", "16.0 GB", "Active"]),
        Row::new(vec!["L4", "Linux_Tablet", "DHCP", "8.0 GB", "--"]),
    ];

    let table = Table::new(
        mesh_stats,
        [
            Constraint::Length(4),
            Constraint::Length(15),
            Constraint::Length(15),
            Constraint::Length(10),
            Constraint::Length(15),
        ],
    )
    .header(Row::new(vec!["Layer", "Node", "IP", "RAM", "Status"]).style(Style::default().fg(Color::Yellow)))
    .block(Block::default().borders(Borders::ALL).title(" Mesh Topology "));
    
    f.render_widget(table, mesh_chunks[0]);

    let system_stats = Paragraph::new(vec![
        Line::from(Span::raw("System Stats Rendering Region")),
        Line::from(Span::raw("-----------------------------")),
        Line::from(Span::raw(format!("Tick Count: {}", iter_count))),
        Line::from(Span::raw("Waiting for telemetry: --")),
        Line::from(Span::styled("[DISCONNECTED]", Style::default().fg(Color::Red))),
    ])
    .block(Block::default().borders(Borders::ALL).title(" Telemetry "));

    f.render_widget(system_stats, mesh_chunks[1]);
}
