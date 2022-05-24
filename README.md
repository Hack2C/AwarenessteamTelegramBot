# AwarenessteamTelegramBot

## Description

Hallöchen. Der AwarenessTeamTelegramBot ist ein Bot für Telegram, der speziell für die Jusos-Halle geschrieben wurde. Es steht jedoch jedem frei diesen Code als Grundlage zu nutzen.

Er ermöglicht es Anonym, mit dem Awarenessteam zu kommunizieren.

## Installation
Die Idee ist, dass bereits ein öffentlich zugänglicher Server besteht, welcher eine mysql Datenbank bereithält. Es kann entweder eine ganz neue Datenbank erstellt werden, oder eine bestehende erweitert werden. Es wird lediglich der Zugriff auf eine einzelne Tabelle benötigt. Es empfiehlt sich die Konfigurationsdatei außerhalb des öffentlich zugänglichen Bereiches zu speichern, wie zum Beispiel in /etc/....

## Usage
Das Awarenessteam kommt mit dem Bot in eine Chatgruppe.
Das Awarenessteam fragt seine eigene Chat-ID ab, welche dann auf dem Server hinterlegt wird.

Jeder Telegram-Nutzer kann den Bot über die Suche finden.
Ihm wird automatisch ein Anonymes Pseudonym zugeordnet. 
Jede weitere Nachricht, die in dem Chat mit dem Bot geschrieben wird, wird direkt an die Gruppe des Awarenessteams weitergeleitet.

Über den Befehl "/answer <Pseudonym>" kann das Awarenessteam einer Einzelperson antworten.

Über den Befehl "/block <Pseudonym>" kann das Awarenessteam eine Einzelperson blockieren, zum Beispiel um einen Missbrauch zu verhindern.

Folgender Befehl soll noch hinzugefügt werden:
Über den Befehl "/delete <Pseudonym>" kann das Awarenessteam eine Art reset des Bots für diese Person initiieren.