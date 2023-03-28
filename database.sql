-- Create the database
CREATE DATABASE <<DB_NAME>>;

-- Create the user and grant privileges
CREATE USER '<<DB_USER>>'@'localhost' IDENTIFIED BY '<<DB_PASSWORD>>';
GRANT ALL PRIVILEGES ON <<DB_NAME>>.* TO '<<DB_USER>>'@'localhost';

USE <<DB_NAME>>;

CREATE TABLE <<DB_TABLE>> (
    id INT NOT NULL AUTO_INCREMENT,
    chat_id BIGINT,
    pseudo VARCHAR(255) NOT NULL,
    user_state VARCHAR(255),
    language_code VARCHAR(10),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE (pseudo)
);

CREATE TABLE messages (
    id INT NOT NULL AUTO_INCREMENT,
    chat_id BIGINT NOT NULL,
    message_id BIGINT NOT NULL,
    language_code VARCHAR(10) NOT NULL,
    message_role VARCHAR(255) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY `message_role_language_code` (`message_role`, `language_code`)
);