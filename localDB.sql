DROP TABLE IF EXISTS servers;
DROP TABLE IF EXISTS players;
CREATE TABLE servers (  
    guild_id CHAR(20) PRIMARY KEY,   
    guild_name TEXT NOT NULL,    
    clan_tag TEXT
    );
ALTER TABLE servers ADD COLUMN IF NOT EXISTS war_channel_id CHAR(20);
CREATE TABLE players (    
    discord_id CHAR(20) NOT NULL,    
    discord_username TEXT NOT NULL,    
    guild_id CHAR(20) NOT NULL, 
    guild_name TEXT NOT NULL,   
    player_tag TEXT NOT NULL,    
    PRIMARY KEY (discord_id, guild_id)
    );