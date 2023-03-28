# AwarenessteamTelegramBot

## Description

Hallöchen. Der AwarenessTeamTelegramBot ist ein Bot für Telegram, der speziell für die Jusos-Halle geschrieben wurde. Es steht jedoch jedem frei diesen Code als Grundlage zu nutzen.

Er ermöglicht es Anonym, mit dem Awarenessteam zu kommunizieren.

Er basiert auf python.

## Installation

### Erstellen der DB/TABLE
Als Hilfsmittel kann die database.sql verwendet werden um eine passende DB/Tabelle zu erstellen.

Example:

```
mysql -uroot
```

```
CREATE DATABASE botdb;

-- Create the user and grant privileges
CREATE USER 'botdbuser'@'localhost' IDENTIFIED BY 'YOURPASSWORD';
GRANT ALL PRIVILEGES ON botdb.* TO 'botdbuser'@'localhost';

USE botdb;

CREATE TABLE user (
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
```
### Editieren der .env Datei

Es ist vollkommen Egal wo der Bot gespeichert ist. Das .env File muss im selben Verzeichnis liegen, gemeinsam mit der requirements.txt.
Das .env File muss dem Einzelfall entsprechend Angepasst werden. Das Feld "AT_CHATID" wird beim ersten ausführen leer gelassen.

Der bot wird mit dem Befehl
~~~
python3 bot.py
~~~
gestartet.

Danach erstellt man eine Gruppe bei Telegram, in welche man den Bot einlädt und zum Administrator macht, damit dieser Zugriff auf die Nachrichten hat.

Das Awarenessteam kann mit dem Befehl /chatid die Chat-ID der Gruppe herausfinden.

Diese Chat-ID wird im .env File als AT-CHATID eingetragen.

### Registrieren als Service bei systemd

Damit der Bot dauerhaft läuft und Bootfest ist, bietet es sich an ihn mit systemd als service zu managen.

Editiere den Inhalt des bot.service Files

```
nano bot.service
```

Kopiere die bot.service Datei in den Ordner der Systemd Services und registriere den Service

```
cp bot.service /etc/systemd/system/telegrambot.service
systemctl daemon-reload
systemctl enable telegrambot.service
systemctl start telegrambot.service
```
Der Bot sollte nun Laufen.

### DB Scheme

```
DB_NAME
+-----------------------+
| Tables_in_pythonbot   |
+-----------------------+
| DB_TABLE              |
+-----------------------+

DB_TABLE
+----------------------------+
| Field        | Type        |
+----------------------------+
| id           | INT         |
| chat_id      | BIGINT      |
| pseudo       | VARCHAR(255)|
| user_state   | VARCHAR(255)|
| language_code| VARCHAR(10) |
| created_at   | TIMESTAMP   |
| updated_at   | TIMESTAMP   |
+----------------------------+
  PK: id
```

## Usage
Das Awarenessteam kommt mit dem Bot in eine Chatgruppe.
Das Awarenessteam fragt seine eigene Chat-ID ab, welche dann auf dem Server hinterlegt wird.

Jeder Telegram-Nutzer kann den Bot über die Suche finden.

Ihm wird automatisch ein Anonymes Pseudonym zugeordnet.

Damit das Pseudonym wirklich Anonym ist, wird es in der Form "AnonymousXY" generiert, wobei XY eine Zahl zwischen 10 und 100 entspricht. Die Pseudonyme werden als Unique gespeichert. Ein einmal verwendetes Pseudonym kann nicht wieder verwendet werden.



Jede weitere Nachricht, die in dem Chat mit dem Bot geschrieben wird, wird direkt an die Gruppe des Awarenessteams weitergeleitet.