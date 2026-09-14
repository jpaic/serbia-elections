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
