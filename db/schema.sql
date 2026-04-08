CREATE DATABASE IF NOT EXISTS smartlab
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;
USE smartlab;
CREATE TABLE IF NOT EXISTS telemetry (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    device VARCHAR(32) NOT NULL,
    topic VARCHAR(255) NOT NULL,
    value DOUBLE NULL,
    unit VARCHAR(16) NULL,
    payload TEXT NULL,
    ts_utc TIMESTAMP NOT NULL,
    INDEX idx_telemetry_device_ts (device, ts_utc)
);
CREATE TABLE IF NOT EXISTS events (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    device VARCHAR(32) NOT NULL,
    topic VARCHAR(255) NOT NULL,
    payload TEXT NOT NULL,
    ts_utc TIMESTAMP NOT NULL,
    INDEX idx_events_device_ts (device, ts_utc)
);