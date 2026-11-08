#[derive(Clone, Copy, PartialEq, Eq)]
pub enum Field {
    Title,
    Author,
    Year,
    Cover,
    Date,
    Rating,
}

#[derive(Default)]
pub struct Fields {
    pub title: String,
    pub author: String,
    pub year: String,
    pub cover: String,
    pub date: String,
    pub rating: String,
}

impl Field {
    pub fn order(cat: &str) -> Vec<Field> {
        match cat {
            "movies" => [
                Field::Title,
                Field::Year,
                Field::Cover,
                Field::Date,
                Field::Rating,
            ]
            .to_vec(),
            "shows" => [Field::Title, Field::Year, Field::Cover, Field::Rating].to_vec(),
            _ => [
                Field::Title,
                Field::Author,
                Field::Year,
                Field::Cover,
                Field::Rating,
            ]
            .to_vec(),
        }
    }

    pub fn label(self) -> &'static str {
        match self {
            Field::Title => "Title",
            Field::Author => "Author",
            Field::Year => "Year",
            Field::Cover => "Cover URL",
            Field::Date => "Date",
            Field::Rating => "Rating",
        }
    }

    pub fn get(self, f: &Fields) -> &str {
        match self {
            Field::Title => &f.title,
            Field::Author => &f.author,
            Field::Year => &f.year,
            Field::Cover => &f.cover,
            Field::Date => &f.date,
            Field::Rating => &f.rating,
        }
    }

    pub fn get_mut(self, f: &mut Fields) -> &mut String {
        match self {
            Field::Title => &mut f.title,
            Field::Author => &mut f.author,
            Field::Year => &mut f.year,
            Field::Cover => &mut f.cover,
            Field::Date => &mut f.date,
            Field::Rating => &mut f.rating,
        }
    }

    pub fn ok(self, v: &str) -> Result<(), String> {
        let t = v.trim();
        match self {
            Field::Title | Field::Author => {
                if t.is_empty() {
                    Err("required".into())
                } else {
                    Ok(())
                }
            }
            Field::Year => {
                let n: i64 = t.parse().map_err(|_| "year must be a number".to_string())?;
                if (1800..=2100).contains(&n) {
                    Ok(())
                } else {
                    Err("year 1800-2100".into())
                }
            }
            Field::Cover => {
                if t.starts_with("http://") || t.starts_with("https://") {
                    Ok(())
                } else {
                    Err("paste an http(s) url".into())
                }
            }
            Field::Date => {
                if t.is_empty() {
                    return Ok(());
                }
                if valid_date(t) {
                    Ok(())
                } else {
                    Err("use DD-MM-YYYY".into())
                }
            }
            Field::Rating => {
                if valid_rating(t) {
                    Ok(())
                } else {
                    Err("rating 0-10, e.g. 8.5".into())
                }
            }
        }
    }
}

fn valid_date(s: &str) -> bool {
    let b = s.as_bytes();
    if b.len() != 10 || b[2] != b'-' || b[5] != b'-' {
        return false;
    }
    for (i, &c) in b.iter().enumerate() {
        if i != 2 && i != 5 && !c.is_ascii_digit() {
            return false;
        }
    }
    let d: u32 = s[0..2].parse().unwrap_or(0);
    let m: u32 = s[3..5].parse().unwrap_or(0);
    let y: u32 = s[6..10].parse().unwrap_or(0);
    let leap = y.is_multiple_of(4) && (!y.is_multiple_of(100) || y.is_multiple_of(400));
    let dim = match m {
        1 | 3 | 5 | 7 | 8 | 10 | 12 => 31,
        4 | 6 | 9 | 11 => 30,
        2 => {
            if leap {
                29
            } else {
                28
            }
        }
        _ => 0,
    };
    dim != 0 && (1..=dim).contains(&d) && (1800..=2100).contains(&y)
}

fn valid_rating(s: &str) -> bool {
    let n = if let Some((num, den)) = s.split_once('/') {
        if den != "10" {
            return false;
        }
        num
    } else {
        s
    };
    let v: f64 = match n.parse() {
        Ok(v) => v,
        Err(_) => return false,
    };
    (0.0..=10.0).contains(&v)
}

pub fn normalise_rating(s: &str) -> String {
    let t = s.trim();
    if let Some((num, _)) = t.split_once('/')
        && let Ok(v) = num.parse::<f64>()
    {
        return if v.fract() == 0.0 {
            format!("{v:.0}/10")
        } else {
            format!("{v}/10")
        };
    }
    if let Ok(v) = t.parse::<f64>() {
        return if v.fract() == 0.0 {
            format!("{v:.0}/10")
        } else {
            format!("{v}/10")
        };
    }
    t.to_string()
}
