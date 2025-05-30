DROP TABLE IF EXISTS servers;
DROP TABLE IF EXISTS players;
CREATE TABLE servers (  
    guild_id CHAR(20) PRIMARY KEY,   
    guild_name TEXT NOT NULL,    
    clan_tag TEXT
    );
CREATE TABLE players (    
    discord_id CHAR(20) NOT NULL,    
    discord_username TEXT NOT NULL,    
    guild_id CHAR(20) NOT NULL,    
    player_tag TEXT,    
    PRIMARY KEY (discord_id, guild_id)
    );