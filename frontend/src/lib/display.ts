// RIK nazivi regiona su ćirilica, stari demo podaci latinica — prihvati oba
export function isDiasporaRegion(name: string | null | undefined): boolean {
  return name === "Inostranstvo" || name === "Иностранство";
}
export function isZavodiRegion(name: string | null | undefined): boolean {
  return (
    name === "Zavodi za izvršenje krivičnih sankcija" ||
    name === "Заводи за извршење кривичних санкција"
  );
}

// Glagol pobednika: sadašnje vreme dok traju, prošlo za završene izbore
export function leaderVerb(status?: string, capitalized = false): string {
  const past = status === "closed";
  if (capitalized) return past ? "Pobedio" : "Vodi";
  return past ? "pobedio" : "vodi";
}

// "ПАЛИЛУЛА" -> "Палилула", "ПЕТРОВАЦ НА МЛАВИ" -> "Петровац на Млави"
const SMALL_WORDS = new Set(["на", "у", "и", "са", "с", "из", "од", "до", "за", "по", "о", "а"]);
export function formatPlaceName(name: string): string {
  const words = name.toLowerCase().split(/\s+/);
  return words
    .map((w, i) =>
      i > 0 && SMALL_WORDS.has(w)
        ? w
        : w
            .split("-")
            .map((p) => (p.length > 0 ? p.charAt(0).toUpperCase() + p.slice(1) : p))
            .join("-")
    )
    .join(" ");
}
