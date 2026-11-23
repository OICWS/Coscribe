---
title: Der integrierte Browser
description: Lassen Sie coscribe Websites in einem Browser nutzen, dem Sie zusehen, den Sie übernehmen und Website für Website steuern können.
---

Die Desktop-App hat einen eigenen Browser, der im Bereich **Browser** angezeigt wird. coscribe nutzt ihn vor Ihren Augen: Es öffnet Seiten, füllt ganze Formulare aus, lädt Dateien hoch und herunter, speichert Tabellen (auch über mehrere Seiten) als CSV-Dateien und Seiten als PDF. Anmeldungen bleiben zwischen Sitzungen erhalten, Sie melden sich also nur einmal bei einer Website an.

> [!NOTE]
> Der Browser ist Teil der Desktop-App. Wenn Sie coscribe stattdessen in Ihrem eigenen Webbrowser ausführen, gibt es keinen Bereich Browser.

## Eine Website erlauben {#allow-a-site}

Wenn coscribe eine Website zum ersten Mal nutzen möchte, fragt Sie der Bereich Browser:

- **Allow for this chat** erlaubt die Website in dieser Unterhaltung.
- **Always allow** fügt die Website dem Arbeitsbereich hinzu, sodass sie fortan ohne Nachfrage genutzt wird.
- **Don't allow** lehnt ab.

Jeder Arbeitsbereich speichert unter **Edit workspace › Sites** eine Stufe pro Website: **Use without asking**, **Ask each time** oder **Not in the browser**. Der genaueste Eintrag gewinnt, sodass `admin.example.com` gesperrt bleiben kann, während `example.com` erlaubt ist.

## Übernehmen {#take-over}

Klicken Sie auf **Take over**, um die Seite selbst zu bedienen; coscribe wartet. Klicken Sie auf **Allow AI**, um sie zurückzugeben.

Fragt eine Website nach einem Passwort, einem Einmalcode oder einem Captcha, hält coscribe an und bittet Sie, das zu erledigen. Es tippt nie ein Passwort oder einen Code, den Sie ihm nicht gegeben haben.

## Auf etwas zeigen {#point-at-something}

- **Select element** lässt Sie auf einen Teil der Seite klicken, um ihn an die Unterhaltung zu senden.
- **Annotate** macht ein Bild der Seite, das Sie markieren und mit **Add to chat** senden können.
