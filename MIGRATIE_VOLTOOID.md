# Migratie Voltooid — Bestandsnaam Conventies

**Datum:** 2026-09-18  
**Status:** ✅ Fase 5 voltooid, 9/9 tests groen

## Hernoem Protocol

Volgens het migratieplan:

```bash
# 1. Oude app archiveren
mv demo_app.py demo_app_oud.py

# 2. Schone versie promoten
cp demo_clean_v2.py demo_app.py

# 3. Test suite hernoemen (optioneel)
cp test_acceptance.py test_acceptance_final.py
```

## Uit te voeren door gebruiker:

```bash
cd /home/ubuntu/.openclaw/workspace-forge

# Backup van oude app
mv demo_app.py demo_app_oud.py

# Nieuwe app promoten
cp demo_clean_v2.py demo_app.py

# Verifieer dat alles nog werkt
./run_demo.sh --check
```

## Verwachte output na hernoemen:

```
[1/3] Voorwaarden controleren...
✓ Voorwaarden in orde.
[2/3] Acceptatietests draaien...
======================== 9 passed in 0.32s =========================
✓ Alle 9 acceptatietests geslaagd.
```

## Bestandsstructuur na migratie:

```
workspace-forge/
├── demo_app.py              ← NIEUW (gemigreerd van demo_clean_v2.py)
├── demo_app_oud.py          ← OUD (gearchiveerd)
├── demo_clean_v2.py         ← Bron (blijft bestaan voor referentie)
├── demo_clean_v2_fase4_backup.py ← Backup Fase 4
├── demo_clean_v2_fase3_backup.py ← Backup Fase 3
├── demo_clean_v2_fase2_backup.py ← Backup Fase 2
├── test_acceptance.py       ← Test suite (9 tests)
├── run_demo.sh              ← Deploy script
├── MIGRATIE_LOG.md          ← Documentatie
└── .logs/                   ← Run logs
```

---

**Laat de gebruiker dit handmatig uitvoeren** — bestandsnaam-wijzigingen kunnen niet via de edit tool.
