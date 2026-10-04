# Morsetrainer

A CW trainer for everyone from beginners to contesters, developed by **DL4YM**.

From learning single characters with the Koch method up to running your own
contest pile-up under realistic HF conditions – alone at your own computer
or together at a club evening on the local network.

**Language:** the program starts in German. Switch to English under
„▸ Weitere Optionen“ → „Sprache / Language“; it takes effect after a
restart. The screenshots show the German interface.

![Groups tab: copying at Koch speed 20/10, “Richtig: ESJ” (correct)](docs/bilder/gruppen.png)

## What it does

- **Koch method** with the lessons of lcwo.net and Koch speed 20/10: hear
  characters as a sound pattern instead of counting dits and dahs. The
  next lesson is offered once you get 90 %.
- **Daily practice (10 min):** puts together what is due today – warm-up,
  main part, cool-down – with three stars a day and a weekly goal.
- **Exercises:** single characters with time limit, groups, words and Q
  codes, real callsigns (also as a RufZ run), continuous copying, listen &
  say without a keyboard (also as MP3), complete QSOs and contest operation
  as the running station, as in Morse Runner.
- **Band conditions:** noise, QRN, QSB, chirp, SSB babble and CW QRM, each
  adjustable.
- **Statistics:** per character, spaced repetition over days, most frequent
  confusions to practise specifically, printable awards in bronze, silver
  and gold, lifeline.
- **Network:** class or club evening on the local network. The trainer
  sets the pace, everyone hears the same sequence and types along, the
  trainer sees live who typed what. Also with a fixed pace for pencil and
  paper.

![Club evening: the trainer's table with four participants](docs/bilder/netzwerk.png)

## Download

Ready-to-run programs are on the
[Releases](https://github.com/tilde1970/Morsetrainer/releases) page; no
Python installation is needed:

- **Linux:** download `Morsetrainer-x86_64.AppImage`, make it executable
  (`chmod +x Morsetrainer-x86_64.AppImage`) and run it.
- **Windows:** download and run `Morsetrainer.exe`. The file is not signed,
  so Windows SmartScreen warns on first start (“More info” → “Run anyway”).
- **macOS (Apple silicon):** download `Morsetrainer-macOS.zip`, unpack it
  and drag `Morsetrainer.app` into Applications. The app is not signed, so
  you have to approve it on first start – see the
  [manual](docs/Anleitung.en.md#macos), which also covers Intel Macs.

From version 2.30 on, `SHA256SUMS.txt` with the checksums sits next to the
programs. To verify, on Linux run `sha256sum -c --ignore-missing
SHA256SUMS.txt`; on Windows run `Get-FileHash Morsetrainer.exe` in
PowerShell and compare with the line in `SHA256SUMS.txt`.

## First steps

1. Set **Koch lesson 1** at the top (K and M); “▶ listen” plays the new
   character.
2. Get to know the characters in the **Characters** tab, then copy in the
   **Groups** tab while the audio plays.
3. Or simply press **▶ Daily practice (10 min)** (F12) – it switches the
   tabs by itself.
4. Enter your callsign and name under “▸ More options”; they appear on the
   awards.

Everything else is in the [manual](docs/Anleitung.en.md), also in the
program under **Help**.

## Security

- **Updates:** on start the Morsetrainer asks when there is a newer
  release and, if you agree, replaces the exe or AppImage. Downloads come
  only from this repository over HTTPS, and the file has to match the
  checksum in `SHA256SUMS.txt`. This catches damaged downloads but is no
  substitute for a signature: whoever can replace the release can replace
  the checksum too.
- **Network mode:** unencrypted over TCP. Meant for a club or home
  network, not for public Wi-Fi. After 5 wrong PINs a computer is locked
  for a minute, and the trainer can remove strangers. The trainer does not
  pass on updates, it only tells its version number.

## More

- [Manual](docs/Anleitung.en.md): all tabs, daily practice, awards,
  network, keyboard shortcuts, data and backup
- [Changes](CHANGELOG.en.md) per version
- [Development](docs/Entwicklung.en.md): running from source, tests,
  project structure, release

## License

MIT, see [LICENSE](LICENSE). © 2026 DL4YM

---

73 de DL4YM
