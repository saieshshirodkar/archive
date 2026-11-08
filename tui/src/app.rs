use crossterm::event::{KeyCode, KeyModifiers};

use crate::fields::{Field, Fields};
use crate::theme::CATS;

pub struct App {
    pub cat: usize,
    pub step: usize,
    pub fields: Fields,
    pub order: Vec<Field>,
    pub error: String,
    pub quit: bool,
    pub submit: bool,
}

impl App {
    pub fn new() -> Self {
        Self {
            cat: 2,
            step: 0,
            fields: Fields::default(),
            order: Vec::new(),
            error: String::new(),
            quit: false,
            submit: false,
        }
    }

    pub fn current(&self) -> Option<Field> {
        if self.step == 0 || self.step > self.order.len() {
            None
        } else {
            self.order.get(self.step - 1).copied()
        }
    }

    pub fn on_key(&mut self, code: KeyCode, mods: KeyModifiers) {
        if mods.contains(KeyModifiers::CONTROL) {
            if code == KeyCode::Char('c') {
                self.quit = true;
            }
            return;
        }
        if self.step == 0 {
            match code {
                KeyCode::Up | KeyCode::Char('k') => self.cat = self.cat.saturating_sub(1),
                KeyCode::Down | KeyCode::Char('j') => self.cat = (self.cat + 1).min(CATS.len() - 1),
                KeyCode::Char('1') => self.cat = 0,
                KeyCode::Char('2') => self.cat = 1,
                KeyCode::Char('3') => self.cat = 2,
                KeyCode::Char('4') => self.cat = 3,
                KeyCode::Enter => {
                    self.order = Field::order(CATS[self.cat]);
                    self.step = 1;
                    self.error.clear();
                }
                KeyCode::Esc => self.quit = true,
                _ => {}
            }
            return;
        }
        if self.step <= self.order.len() {
            let field = self.order[self.step - 1];
            match code {
                KeyCode::Esc => self.step = self.step.saturating_sub(1),
                KeyCode::Enter => {
                    let v = field.get(&self.fields).to_string();
                    match field.ok(&v) {
                        Ok(()) => {
                            self.error.clear();
                            self.step += 1;
                        }
                        Err(e) => self.error = e,
                    }
                }
                KeyCode::Backspace => {
                    field.get_mut(&mut self.fields).pop();
                }
                KeyCode::Char(c) => {
                    let slot = field.get_mut(&mut self.fields);
                    if slot.len() < 220 {
                        slot.push(c);
                    }
                }
                _ => {}
            }
            return;
        }
        match code {
            KeyCode::Enter => {
                self.submit = true;
                self.quit = true;
            }
            KeyCode::Esc => self.step = self.order.len(),
            _ => {}
        }
    }

    pub fn is_gold(&self) -> bool {
        self.fields.rating.trim() == "10" || self.fields.rating.trim() == "10/10"
    }
}
