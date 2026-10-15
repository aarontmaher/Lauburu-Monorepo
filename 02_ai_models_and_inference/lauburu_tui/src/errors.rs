use std::fmt;

/// Application-level error types for lauburu-tui
#[derive(Debug)]
pub enum AppError {
    Config(String),
    Io(std::io::Error),
    TomlDe(toml::de::Error),
    Json(serde_json::Error),
    Network(String),
    Validation(String),
    Persistence(String),
    Other(String),
}

impl fmt::Display for AppError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            AppError::Config(msg) => write!(f, "Configuration error: {msg}"),
            AppError::Io(err) => write!(f, "I/O error: {err}"),
            AppError::TomlDe(err) => write!(f, "TOML deserialization error: {err}"),
            AppError::Json(err) => write!(f, "JSON error: {err}"),
            AppError::Network(msg) => write!(f, "Network error: {msg}"),
            AppError::Validation(msg) => write!(f, "Validation error: {msg}"),
            AppError::Persistence(msg) => write!(f, "Persistence error: {msg}"),
            AppError::Other(msg) => write!(f, "Error: {msg}"),
        }
    }
}

impl std::error::Error for AppError {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        match self {
            AppError::Io(err) => Some(err),
            AppError::TomlDe(err) => Some(err),
            AppError::Json(err) => Some(err),
            _ => None,
        }
    }
}

impl From<std::io::Error> for AppError {
    fn from(err: std::io::Error) -> Self {
        AppError::Io(err)
    }
}

impl From<toml::de::Error> for AppError {
    fn from(err: toml::de::Error) -> Self {
        AppError::TomlDe(err)
    }
}

impl From<serde_json::Error> for AppError {
    fn from(err: serde_json::Error) -> Self {
        AppError::Json(err)
    }
}

impl From<reqwest::Error> for AppError {
    fn from(err: reqwest::Error) -> Self {
        AppError::Network(err.to_string())
    }
}
