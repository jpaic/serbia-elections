// Vladajuće koalicije po izborima: redni brojevi lista sa glasačkog listića
// koje su formirale Vladu posle izbora. Koristi se za crveni okvir u
// raspodeli mandata i podvlačenje u legendi.
export const GOVERNING_BALLOTS: Record<string, number[]> = {
  "parlamentarni-2000": [4], // DOS (Đinđić)
  "parlamentarni-2003": [3, 1, 6], // DSS + G17 Plus + SPO–NS (Koštunica, manjinska)
  "parlamentarni-2007": [1, 5, 2], // DS + DSS–NS + G17 Plus (Koštunica)
  "parlamentarni-2008": [1, 5], // ZES + SPS (Cvetković)
  "parlamentarni-2012": [5, 7, 3], // SNS + SPS + URS (Dačić)
  "parlamentarni-2014": [1, 2], // SNS + SPS (Vučić)
  "parlamentarni-2016": [1, 3], // SNS + SPS (Vučić)
  "parlamentarni-2020": [1, 2], // SNS + SPS (Brnabić)
  "parlamentarni-2022": [1, 2], // SNS + SPS (Brnabić)
  "parlamentarni-2023": [1, 2], // SNS + SPS (Vučević)
};

// Stranke na vlasti kratko (za header "Vlast: ..."), po slug-u
export const GOVERNING_PARTIES: Record<string, string> = {
  "parlamentarni-2000": "DOS",
  "parlamentarni-2003": "DSS + G17 Plus + SPO–NS",
  "parlamentarni-2007": "DS + DSS–NS + G17 Plus",
  "parlamentarni-2008": "DS + SPS",
  "parlamentarni-2012": "SNS + SPS + URS",
  "parlamentarni-2014": "SNS + SPS",
  "parlamentarni-2016": "SNS + SPS",
  "parlamentarni-2020": "SNS + SPS",
  "parlamentarni-2022": "SNS + SPS",
  "parlamentarni-2023": "SNS + SPS",
};

// Stranke na vlasti kao niz skracenica (za pil na naslovnoj), po slug-u
export const GOVERNING_LIST: Record<string, string[]> = {
  "parlamentarni-2000": ["DOS"],
  "parlamentarni-2003": ["DSS", "G17 Plus", "SPO–NS"],
  "parlamentarni-2007": ["DS", "DSS–NS", "G17 Plus"],
  "parlamentarni-2008": ["DS", "SPS"],
  "parlamentarni-2012": ["SNS", "SPS", "URS"],
  "parlamentarni-2014": ["SNS", "SPS"],
  "parlamentarni-2016": ["SNS", "SPS"],
  "parlamentarni-2020": ["SNS", "SPS"],
  "parlamentarni-2022": ["SNS", "SPS"],
  "parlamentarni-2023": ["SNS", "SPS"],
};

// Boje stranaka za pilove (iste kao brend boje na mapi)
export const PARTY_ABBR_COLORS: Record<string, string> = {
  SNS: "#0E4DA4",
  SPS: "#ED1C24",
  DS: "#F2C200",
  DSS: "#1F3A5F",
  "DSS–NS": "#1F3A5F",
  "G17 Plus": "#4A7FB5",
  "SPO–NS": "#6FA8DC",
  URS: "#E67E22",
  DOS: "#F2C200",
};

// Stranke iza lista (slug -> redni broj -> kratke oznake), za legendu mandata
export const LIST_PARTIES: Record<string, Record<number, string>> = {
  "parlamentarni-2000": { 1: "SRS", 2: "SPO", 3: "SPS", 4: "DOS", 5: "SSJ" },
  "parlamentarni-2003": {
    1: "G17 Plus", 2: "SRS", 3: "DSS", 4: "DA", 5: "DS", 6: "SPO–NS",
    7: "Otpor", 9: "SPS", 12: "ZZT", 15: "SNS (Pavković)",
  },
  "parlamentarni-2007": {
    1: "DS", 2: "G17 Plus", 3: "LDP", 4: "SRS", 5: "DSS–NS", 6: "PSS",
    7: "SPO", 8: "SVM", 9: "PUPS", 10: "LZ Sandžaka", 11: "SPS",
    14: "URS", 17: "KAPD", 20: "RP",
  },
  "parlamentarni-2008": {
    1: "DS-led", 2: "LDP", 3: "DSS–NS", 4: "SRS", 5: "SPS–PUPS–JS",
    6: "Bošnjačka", 7: "SVM", 17: "KAPD",
  },
  "parlamentarni-2012": {
    1: "DS", 2: "SRS", 3: "URS", 4: "LDP", 5: "SNS + NS", 6: "DSS",
    7: "SPS–PUPS–JS", 8: "Dveri", 9: "SVM", 11: "SDA", 14: "BDZ", 15: "KAPD", 18: "NOPO",
  },
  "parlamentarni-2014": {
    1: "SNS", 2: "SPS–PUPS–JS", 3: "DSS", 4: "LDP", 5: "SVM", 6: "SRS",
    7: "URS", 8: "DS", 9: "Dveri", 10: "SDA", 11: "NDS + LSV", 15: "DJB",
    18: "Ruska", 19: "PDD",
  },
  "parlamentarni-2016": {
    1: "SNS", 2: "DS", 3: "SPS–JS", 4: "SRS", 5: "Dveri–DSS", 6: "SVM",
    7: "SDS", 8: "BDZ", 9: "SDA", 10: "Zavetnici", 17: "DJB", 18: "PDD", 19: "Zeleni",
  },
  "parlamentarni-2020": {
    1: "SNS", 2: "SPS–JS", 3: "SRS", 4: "SVM", 5: "SPAS", 6: "POKS",
    8: "SPP", 11: "SDA", 12: "Zavetnici", 15: "DJB", 16: "ADA",
    18: "Zeleni", 19: "Ruska", 20: "LDP",
  },
  "parlamentarni-2022": {
    1: "SNS", 2: "SPS–JS", 3: "SVM", 4: "SRS", 5: "Ujedinjeni (SSP)",
    6: "NDSS–POKS", 7: "Zavetnici", 8: "SPP", 9: "Moramo (ZLF)",
    10: "DJB", 11: "Dveri–POKS", 12: "ZZV", 13: "SDA", 16: "KAD",
  },
  "parlamentarni-2023": {
    1: "SNS", 2: "SPS–JS", 3: "SRS", 4: "Zavetnici–Dveri", 5: "NDSS–POKS",
    6: "SVM", 7: "SPN (SSP)", 8: "SPP", 9: "SDA", 11: "Narodna",
    12: "DJB", 13: "PBA", 14: "MI (Nestorović)", 16: "Ruska", 17: "LDP", 18: "ADA",
  },
};
