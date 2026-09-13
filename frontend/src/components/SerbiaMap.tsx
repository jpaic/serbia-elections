"use client";

import { useState } from "react";
import { ComposableMap, Geographies, Geography } from "react-simple-maps";
import { processedColor } from "@/lib/colorScale";
import type { MunicipalityRow } from "@/lib/types";

const GEO_URL = "/data/serbia-okruzi.geojson";

// Region u geojson-u je nivo upravnog okruga (30 jedinica). Opštine (municipalities)
// iz baze pripadaju regionu preko kolone `region` — ona MORA da se popuni tekstom
// koji se tačno poklapa sa `name` iz geojson-a (npr. "Nišavski okrug", "Grad Beograd",
// "Sremski", "Zaječarski") da bi agregacija ispod radila. Ako RZS šifre ne dolaze u
// ovom obliku, ovde treba dodati mapping tabelu pre agregacije.
function regionProcessedPct(regionName: string, municipalities: MunicipalityRow[]): number | null {
  const inRegion = municipalities.filter((m) => m.region === regionName);
  if (inRegion.length === 0) return null;
  const totalStations = inRegion.reduce((s, m) => s + m.total_stations, 0);
  const processed = inRegion.reduce((s, m) => s + m.processed_stations, 0);
  if (totalStations === 0) return 0;
  return (100 * processed) / totalStations;
}

export default function SerbiaMap({
  municipalities,
  onSelectRegion,
  selectedRegion,
}: {
  municipalities: MunicipalityRow[];
  onSelectRegion: (regionName: string) => void;
  selectedRegion: string | null;
}) {
  const [hovered, setHovered] = useState<string | null>(null);

  return (
    <div style={{ width: "100%" }}>
      <ComposableMap
        projection="geoMercator"
        projectionConfig={{ center: [20.9, 44.2], scale: 3200 }}
        style={{ width: "100%", height: "auto" }}
      >
        <Geographies geography={GEO_URL}>
          {({ geographies }) =>
            geographies.map((geo) => {
              const name = (geo.properties as { name?: string } | undefined)?.name ?? "";
              const pct = regionProcessedPct(name, municipalities);
              const isSelected = selectedRegion === name;
              const isHovered = hovered === name;
              const baseFill = pct === null ? "#E6E5DD" : processedColor(pct);
              return (
                <Geography
                  key={geo.rsmKey}
                  geography={geo}
                  onMouseEnter={() => setHovered(name)}
                  onMouseLeave={() => setHovered(null)}
                  onClick={() => onSelectRegion(name)}
                  fill={baseFill}
                  stroke="#ffffff"
                  strokeWidth={isSelected ? 1.5 : 0.5}
                  opacity={isHovered ? 0.85 : 1}
                  style={{ outline: "none", cursor: "pointer" }}
                />
              );
            })
          }
        </Geographies>
      </ComposableMap>
      {hovered && (
        <p style={{ fontSize: 13, color: "var(--text-secondary, #666)", marginTop: 4 }}>
          {hovered}
        </p>
      )}
    </div>
  );
}
