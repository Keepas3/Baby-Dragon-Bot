DROP TABLE IF EXISTS servers;
DROP TABLE IF EXISTS players;


CREATE TABLE IF NOT EXISTS servers (
    guild_id VARCHAR(20) PRIMARY KEY,
    guild_name VARCHAR(255) NOT NULL,
    clan_tag VARCHAR(15),
    war_channel_id VARCHAR(20),
    raid_channel_id VARCHAR(20),
    last_war_reminder VARCHAR(20) DEFAULT NULL,
    last_raid_reminder VARCHAR(20) DEFAULT NULL
);
DROP TABLE IF EXISTS players;

CREATE TABLE IF NOT EXISTS players (
    discord_id VARCHAR(20) PRIMARY KEY, -- One Discord user = One CoC main account
    discord_username VARCHAR(255) NOT NULL,
    player_tag VARCHAR(15) NOT NULL,
    is_premium BOOLEAN NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS coc_sessions (
    player_tag VARCHAR(15) PRIMARY KEY, -- Supports unlimited alts!
    discord_id VARCHAR(20) NOT NULL,     -- Links back to the owner
    cookies_json TEXT NOT NULL,         -- The clean JSON array of browser cookies
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);