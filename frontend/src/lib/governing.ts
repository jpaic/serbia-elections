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
