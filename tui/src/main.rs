mod app;
mod fields;
mod jobs;
mod theme;
mod ui;

use std::env;
use std::io;
use std::path::PathBuf;

use crossterm::event::{self, Event, KeyEventKind};
use crossterm::execute;
use crossterm::terminal::{
    EnterAlternateScreen, LeaveAlternateScreen, disable_raw_mode, enable_raw_mode,
};
use ratatui::Terminal;
use ratatui::backend::CrosstermBackend;

use crate::app::App;

const USAGE: &str = "usage: archive-tui [--root=<dir>] [--no-deploy] [-h|--help]\n  wizard: pick category -> title -> year -> cover url -> date/author -> rating -> review\n  then runs scripts/add.py, scripts/check.py, vercel --prod (if all ok)\n";

fn setup() -> io::Result<Terminal<CrosstermBackend<io::Stdout>>> {
    enable_raw_mode()?;
    let mut stdout = io::stdout();
    execute!(stdout, EnterAlternateScreen)?;
    Terminal::new(CrosstermBackend::new(stdout))
}

fn run(term: &mut Terminal<CrosstermBackend<io::Stdout>>, app: &mut App) -> io::Result<()> {
    loop {
        term.draw(|f| ui::draw(f, app))?;
        if let Event::Key(key) = event::read()?
            && key.kind == KeyEventKind::Press
        {
            app.on_key(key.code, key.modifiers);
            if app.quit {
                break;
            }
        }
    }
    Ok(())
}

fn entry() -> i32 {
    std::panic::set_hook(Box::new(|_| {
        let _ = disable_raw_mode();
        let _ = execute!(io::stdout(), LeaveAlternateScreen);
    }));
    let mut root = PathBuf::from(".");
    let mut deploy = true;
    for a in env::args().skip(1) {
        if a == "--no-deploy" {
            deploy = false;
        } else if a == "-h" || a == "--help" {
            print!("{USAGE}");
            return 0;
        } else if let Some(v) = a.strip_prefix("--root=") {
            root = PathBuf::from(v);
        } else if a.starts_with('-') {
            eprint!("unknown flag: {a}\n{USAGE}");
            return 2;
        } else {
            root = PathBuf::from(a);
        }
    }
    if !root.join("scripts/add.py").exists() {
        eprintln!(
            "error: no scripts/add.py under {}; pass --root=<archive dir>",
            root.join("scripts/add.py").display()
        );
        return 1;
    }
    let mut term = match setup() {
        Ok(t) => t,
        Err(e) => {
            eprintln!("tui setup: {e}");
            return 1;
        }
    };
    let mut app = App::new();
    let res = run(&mut term, &mut app);
    let _ = disable_raw_mode();
    let _ = execute!(term.backend_mut(), LeaveAlternateScreen);
    let _ = term.show_cursor();
    if let Err(e) = res {
        eprintln!("tui: {e}");
        return 1;
    }
    if !app.submit {
        return 0;
    }
    jobs::run_cmds(&root, &app, deploy)
}

fn main() {
    std::process::exit(entry());
}
