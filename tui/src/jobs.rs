use std::path::Path;
use std::process::{Command, Stdio};

use crate::app::App;
use crate::fields::normalise_rating;
use crate::theme::CATS;

fn today_ist() -> String {
    let out = Command::new("date")
        .arg("+%d-%m-%Y")
        .env("TZ", "Asia/Kolkata")
        .output();
    match out {
        Ok(o) if o.status.success() => String::from_utf8_lossy(&o.stdout).trim().to_string(),
        _ => String::new(),
    }
}

pub fn run_cmds(root: &Path, app: &App, deploy: bool) -> i32 {
    let cat = CATS[app.cat];
    let rating = normalise_rating(&app.fields.rating);
    let date = if app.fields.date.trim().is_empty() {
        today_ist()
    } else {
        app.fields.date.trim().to_string()
    };
    let mut add = Command::new("uv");
    add.arg("run")
        .arg("python")
        .arg("scripts/add.py")
        .arg("--cat")
        .arg(cat)
        .arg("--title")
        .arg(app.fields.title.trim())
        .arg("--year")
        .arg(app.fields.year.trim())
        .arg("--rating")
        .arg(&rating)
        .arg("--cover-url")
        .arg(app.fields.cover.trim());
    match cat {
        "books" | "animanga" => {
            add.arg("--author").arg(app.fields.author.trim());
        }
        "movies" => {
            add.arg("--date").arg(&date);
        }
        _ => {}
    }
    println!("→ add {} — {}", cat, app.fields.title.trim());
    let st = match add
        .current_dir(root)
        .stdin(Stdio::inherit())
        .stdout(Stdio::inherit())
        .stderr(Stdio::inherit())
        .status()
    {
        Ok(s) => s,
        Err(e) => {
            println!("add failed to spawn: {e}");
            return 1;
        }
    };
    if !st.success() {
        println!("add failed.");
        return 1;
    }
    println!("→ check");
    let st = match Command::new("uv")
        .arg("run")
        .arg("python")
        .arg("scripts/check.py")
        .current_dir(root)
        .stdin(Stdio::inherit())
        .stdout(Stdio::inherit())
        .stderr(Stdio::inherit())
        .status()
    {
        Ok(s) => s,
        Err(e) => {
            println!("check failed to spawn: {e}");
            return 1;
        }
    };
    if !st.success() {
        println!("check failed.");
        return 1;
    }
    if !deploy {
        println!("done (deploy skipped)");
        return 0;
    }
    println!("→ vercel --prod");
    let st = match Command::new("vercel")
        .arg("--prod")
        .current_dir(root)
        .stdin(Stdio::inherit())
        .stdout(Stdio::inherit())
        .stderr(Stdio::inherit())
        .status()
    {
        Ok(s) => s,
        Err(e) => {
            println!("deploy failed to spawn: {e}");
            return 1;
        }
    };
    if !st.success() {
        println!("deploy failed.");
        return 1;
    }
    println!("done — live on archive.");
    0
}
