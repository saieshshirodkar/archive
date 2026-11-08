use ratatui::Frame;
use ratatui::layout::{Constraint, Layout, Position};
use ratatui::style::{Modifier, Style};
use ratatui::text::{Line, Span};
use ratatui::widgets::Paragraph;

use crate::app::App;
use crate::fields::{Field, normalise_rating};
use crate::theme::{ACCENT, BAD, CATS, FAINT, FG, GOLD, LABELS, MUTED};

pub fn draw(frame: &mut Frame, app: &App) {
    let chunks = Layout::vertical([
        Constraint::Length(1),
        Constraint::Min(0),
        Constraint::Length(1),
    ])
    .split(frame.area());
    frame.render_widget(
        Paragraph::new(Line::from(Span::styled(
            "archive",
            Style::default().fg(MUTED),
        ))),
        chunks[0],
    );
    let footer = if app.step == 0 {
        "↑↓ pick · Enter select · Ctrl+C quit"
    } else if app.step > app.order.len() {
        "Enter add · Esc back · Ctrl+C quit"
    } else {
        "Enter next · Esc back · Ctrl+C quit"
    };
    frame.render_widget(
        Paragraph::new(Line::from(Span::styled(footer, Style::default().fg(FAINT)))),
        chunks[2],
    );
    let body = chunks[1];
    if app.step == 0 {
        let mut lines = vec![Line::from(Span::styled(
            "Category",
            Style::default().fg(MUTED),
        ))];
        for (i, label) in LABELS.iter().enumerate() {
            if i == app.cat {
                lines.push(Line::from(Span::styled(
                    format!("> {label}"),
                    Style::default().fg(ACCENT).add_modifier(Modifier::BOLD),
                )));
            } else {
                lines.push(Line::from(Span::styled(
                    format!("  {label}"),
                    Style::default().fg(FAINT),
                )));
            }
        }
        frame.render_widget(Paragraph::new(lines), body);
        return;
    }
    if app.step <= app.order.len() {
        let mut lines = vec![
            Line::from(Span::styled(
                format!("Category: {}", CATS[app.cat]),
                Style::default().fg(MUTED),
            )),
            Line::from(""),
        ];
        for (i, f) in app.order.iter().enumerate() {
            let v = f.get(&app.fields);
            let seen = i < app.step;
            let label_style = if i + 1 == app.step {
                Style::default().fg(ACCENT)
            } else if seen {
                Style::default().fg(MUTED)
            } else {
                Style::default().fg(FAINT)
            };
            let value_style = if *f == Field::Rating && app.is_gold() {
                Style::default().fg(GOLD)
            } else if seen {
                Style::default().fg(FG)
            } else {
                Style::default().fg(FAINT)
            };
            lines.push(Line::from(vec![
                Span::styled(format!("{}: ", f.label()), label_style),
                Span::styled(v.to_string(), value_style),
            ]));
        }
        if !app.error.is_empty() {
            lines.push(Line::from(Span::styled(
                format!("! {}", app.error),
                Style::default().fg(BAD),
            )));
        }
        frame.render_widget(Paragraph::new(lines), body);
        if let Some(field) = app.current() {
            let label_len = field.label().len() + 2;
            let x = body
                .x
                .saturating_add((label_len + field.get(&app.fields).len()) as u16);
            let y = body.y.saturating_add((1 + app.step) as u16);
            frame.set_cursor_position(Position::new(x, y));
        }
        return;
    }
    let mut lines = vec![
        Line::from(Span::styled(
            format!("Category: {}", CATS[app.cat]),
            Style::default().fg(MUTED),
        )),
        Line::from(""),
    ];
    for f in &app.order {
        let mut v = f.get(&app.fields).to_string();
        if *f == Field::Date && v.trim().is_empty() {
            v = "today IST".into();
        }
        if *f == Field::Rating {
            v = normalise_rating(&v);
        }
        let style = if *f == Field::Rating && app.is_gold() {
            Style::default().fg(GOLD)
        } else {
            Style::default().fg(FG)
        };
        lines.push(Line::from(vec![
            Span::styled(format!("{}: ", f.label()), Style::default().fg(MUTED)),
            Span::styled(v, style),
        ]));
    }
    frame.render_widget(Paragraph::new(lines), body);
    frame.set_cursor_position(Position::new(body.x, body.y));
}
