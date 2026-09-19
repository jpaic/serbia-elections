# -*- coding: utf-8 -*-
"""Konzistentne boje stranaka kroz sve izborne cikluse.
Izvori boja: Wikipedia infobox 'Colours' (SNS=Blue, SPS=Red, SRS=Blue,
DS=Yellow+Blue/'zuti', DSS/NDSS=Blue/dark blue flag, SVM=Green, LDP=Purple,
G17+=Blue and Grey, DJB=Orange, ZLF=Dark green, Zeleni=Green 059649,
Liberali Srbije=FF4F00), FOTW zastave (DSS tamnoplava, SPO svetloplava),
ostalo uobicajene brend boje.

Kljuc: (slug, ballot_number) -> hex. Liste bez unosa zadrzavaju postojecu boju.
VAZNO: SNS iz 2003 (Pavkoviceva Socijalisticka narodna stranka) NIJE SNS Vucic -
ostaje siva iz palete.
"""
COLORS = {
    # ---- 2000 ----
    ("parlamentarni-2000", 1): "#0B2A5B",  # SRS
    ("parlamentarni-2000", 2): "#6FA8DC",  # SPO
    ("parlamentarni-2000", 3): "#ED1C24",  # SPS
    ("parlamentarni-2000", 4): "#F2C200",  # DOS (DS-led, zuti)
    ("parlamentarni-2000", 5): "#5B9E4D",  # SSJ
    # ---- 2003 ----
    ("parlamentarni-2003", 1): "#4A7FB5",  # G17 Plus
    ("parlamentarni-2003", 2): "#0B2A5B",  # SRS
    ("parlamentarni-2003", 3): "#1F3A5F",  # DSS
    ("parlamentarni-2003", 5): "#F2C200",  # DS
    ("parlamentarni-2003", 6): "#6FA8DC",  # SPO-NS
    ("parlamentarni-2003", 9): "#ED1C24",  # SPS
    ("parlamentarni-2003", 13): "#FF4F00",  # Liberali Srbije
    # ---- 2007 ----
    ("parlamentarni-2007", 1): "#F2C200",  # DS
    ("parlamentarni-2007", 2): "#4A7FB5",  # G17 Plus
    ("parlamentarni-2007", 3): "#8E44AD",  # LDP
    ("parlamentarni-2007", 4): "#0B2A5B",  # SRS
    ("parlamentarni-2007", 5): "#1F3A5F",  # DSS-NS
    ("parlamentarni-2007", 7): "#6FA8DC",  # SPO
    ("parlamentarni-2007", 8): "#00A651",  # SVM
    ("parlamentarni-2007", 10): "#2E8B57",  # Lista za Sandzak (SDA)
    ("parlamentarni-2007", 11): "#ED1C24",  # SPS
    # ---- 2008 ----
    ("parlamentarni-2008", 1): "#F2C200",  # ZES (DS-led, zuti)
    ("parlamentarni-2008", 2): "#8E44AD",  # LDP
    ("parlamentarni-2008", 3): "#1F3A5F",  # DSS-NS
    ("parlamentarni-2008", 4): "#0B2A5B",  # SRS
    ("parlamentarni-2008", 5): "#ED1C24",  # SPS
    ("parlamentarni-2008", 6): "#2E8B57",  # Bosnjacka lista (SDA)
    ("parlamentarni-2008", 7): "#00A651",  # Madjarska koalicija (SVM)
    ("parlamentarni-2008", 17): "#D92626",  # KAPD
    # ---- 2012 ----
    ("parlamentarni-2012", 1): "#F2C200",  # DS-led
    ("parlamentarni-2012", 2): "#0B2A5B",  # SRS
    ("parlamentarni-2012", 3): "#E67E22",  # URS
    ("parlamentarni-2012", 4): "#8E44AD",  # Preokret (LDP)
    ("parlamentarni-2012", 5): "#0E4DA4",  # SNS
    ("parlamentarni-2012", 6): "#1F3A5F",  # DSS
    ("parlamentarni-2012", 7): "#ED1C24",  # SPS
    ("parlamentarni-2012", 8): "#B02A30",  # Dveri
    ("parlamentarni-2012", 9): "#00A651",  # SVM
    ("parlamentarni-2012", 11): "#2E8B57",  # SDA
    ("parlamentarni-2012", 14): "#2E8B57",  # Sve zajedno (BDZ)
    ("parlamentarni-2012", 15): "#D92626",  # KAPD
    ("parlamentarni-2012", 18): "#9AA0A6",  # NOPO
    # ---- 2014 ----
    ("parlamentarni-2014", 1): "#0E4DA4",  # SNS
    ("parlamentarni-2014", 2): "#ED1C24",  # SPS
    ("parlamentarni-2014", 3): "#1F3A5F",  # DSS
    ("parlamentarni-2014", 4): "#8E44AD",  # LDP
    ("parlamentarni-2014", 5): "#00A651",  # SVM
    ("parlamentarni-2014", 6): "#0B2A5B",  # SRS
    ("parlamentarni-2014", 7): "#E67E22",  # URS
    ("parlamentarni-2014", 8): "#F2C200",  # DS-led
    ("parlamentarni-2014", 9): "#B02A30",  # Dveri
    ("parlamentarni-2014", 10): "#2E8B57",  # SDA
    ("parlamentarni-2014", 11): "#16A085",  # NDS
    ("parlamentarni-2014", 15): "#F26522",  # DJB
    ("parlamentarni-2014", 18): "#4682B4",  # Ruska stranka
    ("parlamentarni-2014", 19): "#C0392B",  # PDD
    # ---- 2016 ----
    ("parlamentarni-2016", 1): "#0E4DA4",  # SNS
    ("parlamentarni-2016", 2): "#F2C200",  # DS-led
    ("parlamentarni-2016", 3): "#ED1C24",  # SPS
    ("parlamentarni-2016", 4): "#0B2A5B",  # SRS
    ("parlamentarni-2016", 5): "#B02A30",  # Dveri-DSS (Dveri-led)
    ("parlamentarni-2016", 6): "#00A651",  # SVM
    ("parlamentarni-2016", 7): "#E67E22",  # SDS (Tadic)
    ("parlamentarni-2016", 8): "#006B3F",  # BDZ (Zukorlic)
    ("parlamentarni-2016", 9): "#2E8B57",  # SDA
    ("parlamentarni-2016", 10): "#7B1E1E",  # Zavetnici
    ("parlamentarni-2016", 17): "#F26522",  # DJB
    ("parlamentarni-2016", 18): "#C0392B",  # PDD
    ("parlamentarni-2016", 19): "#27AE60",  # Zelena stranka
    # ---- 2020 ----
    ("parlamentarni-2020", 1): "#0E4DA4",  # SNS
    ("parlamentarni-2020", 2): "#ED1C24",  # SPS
    ("parlamentarni-2020", 3): "#0B2A5B",  # SRS
    ("parlamentarni-2020", 4): "#00A651",  # SVM
    ("parlamentarni-2020", 5): "#4A90D9",  # SPAS (Sapic)
    ("parlamentarni-2020", 6): "#7D3C98",  # POKS
    ("parlamentarni-2020", 8): "#006B3F",  # SPP
    ("parlamentarni-2020", 11): "#2E8B57",  # SDA
    ("parlamentarni-2020", 12): "#7B1E1E",  # Zavetnici
    ("parlamentarni-2020", 15): "#F26522",  # Suverenisti (DJB)
    ("parlamentarni-2020", 16): "#D92626",  # ADA
    ("parlamentarni-2020", 18): "#27AE60",  # Zelena stranka
    ("parlamentarni-2020", 19): "#4682B4",  # Ruska stranka
    ("parlamentarni-2020", 20): "#8E44AD",  # LDP
    # ---- 2022 ----
    ("parlamentarni-2022", 1): "#0E4DA4",  # SNS
    ("parlamentarni-2022", 2): "#ED1C24",  # SPS
    ("parlamentarni-2022", 3): "#00A651",  # SVM
    ("parlamentarni-2022", 4): "#0B2A5B",  # SRS
    ("parlamentarni-2022", 5): "#2471A3",  # UZP (SSP-led)
    ("parlamentarni-2022", 6): "#1F3A5F",  # NADA (NDSS)
    ("parlamentarni-2022", 7): "#7B1E1E",  # Zavetnici
    ("parlamentarni-2022", 8): "#006B3F",  # SPP
    ("parlamentarni-2022", 9): "#1B8C4A",  # Moramo (ZLF)
    ("parlamentarni-2022", 10): "#F26522",  # Suverenisti
    ("parlamentarni-2022", 11): "#B02A30",  # Dveri-POKS
    ("parlamentarni-2022", 13): "#2E8B57",  # SDA
    ("parlamentarni-2022", 16): "#D92626",  # KAD
    # ---- 2023 ----
    ("parlamentarni-2023", 1): "#0E4DA4",  # SNS
    ("parlamentarni-2023", 2): "#ED1C24",  # SPS
    ("parlamentarni-2023", 3): "#0B2A5B",  # SRS
    ("parlamentarni-2023", 4): "#B02A30",  # Zavetnici+Dveri
    ("parlamentarni-2023", 5): "#1F3A5F",  # NADA
    ("parlamentarni-2023", 6): "#00A651",  # SVM
    ("parlamentarni-2023", 7): "#2471A3",  # SPN (SSP-led)
    ("parlamentarni-2023", 8): "#006B3F",  # SPP
    ("parlamentarni-2023", 9): "#2E8B57",  # SDA
    ("parlamentarni-2023", 11): "#1B75BC",  # Narodna stranka
    ("parlamentarni-2023", 12): "#F26522",  # DJB
    ("parlamentarni-2023", 13): "#D92626",  # PBA
    ("parlamentarni-2023", 14): "#17A398",  # MI-Glas iz naroda
    ("parlamentarni-2023", 16): "#4682B4",  # Ruska stranka
    ("parlamentarni-2023", 17): "#8E44AD",  # LDP
    ("parlamentarni-2023", 18): "#D92626",  # ADA
    # ---- 2026 (privremeni redosled po datumu proglašenja RIK, do žreba) ----
    ("parlamentarni-2026", 1): "#0E4DA4",  # SNS / Vučić
    ("parlamentarni-2026", 2): "#ED1C24",  # SPS / Dačić
    ("parlamentarni-2026", 3): "#800020",  # Studentska lista
    ("parlamentarni-2026", 4): "#F26522",  # Ljajić (SDP)
    ("parlamentarni-2026", 5): "#00A651",  # SVM / Pásztor
    ("parlamentarni-2026", 6): "#006B3F",  # SPP / Zukorlić
    ("parlamentarni-2026", 7): "#4682B4",  # Ruska stranka – BRIKS
    ("parlamentarni-2026", 8): "#1F3A5F",  # Autentična desnica / NADA / Jovanović (Novi DSS)
    ("parlamentarni-2026", 9): "#2471A3",  # NPS/NLS/Eko – Aleksić/Parandilović/Ćuta
}

if __name__ == "__main__":
    import os
    import psycopg2
    from dotenv import load_dotenv

    load_dotenv(r"C:\Users\Jovan\Desktop\Jovanov folder\Projects\Serbia-Elections\backend\.env")
    c = psycopg2.connect(os.environ["DATABASE_URL"])
    c.autocommit = True
    cur = c.cursor()
    cur.execute("SELECT id, slug FROM elections")
    slugs = {slug: eid for eid, slug in cur.fetchall()}
    n = 0
    for (slug, bn), color in COLORS.items():
        cur.execute("UPDATE parties SET color_hex=%s WHERE election_id=%s AND ballot_number=%s",
                    (color, slugs[slug], bn))
        n += cur.rowcount
    print(f"azurirano boja: {n}")
