"use client";

import { useParams, useRouter } from "next/navigation";
import useSWR from "swr";
import { api } from "@/lib/api";
import Dashboard from "@/components/Dashboard";

export default function ElectionRoute() {
  const params = useParams<{ slug: string }>();
  const router = useRouter();
  const slug = params.slug;
  const { data: elections, error, isLoading } = useSWR("elections", api.elections);
  const match = elections?.find((e) => e.slug === slug) ?? null;

  if (isLoading || (!match && !error)) {
    return (
      <main className="flex flex-col h-full w-full items-center justify-center gap-3 bg-[#0b0d12]">
        <span className="w-8 h-8 rounded-full border-2 border-white/15 border-t-white/80 animate-spin" />
        <p className="text-xs text-white/60">Učitavanje izbora…</p>
      </main>
    );
  }

  if (!match) {
    return (
      <main className="flex flex-col h-full w-full items-center justify-center gap-3 bg-[#0b0d12] px-5">
        <p className="text-base font-semibold text-white">Nepostojeći izborni ciklus: {slug}</p>
        <button
          onClick={() => router.push("/")}
          className="rounded-full bg-white/[0.06] border border-white/10 px-4 py-2 text-xs font-medium text-white hover:border-white/25 transition-colors"
        >
          ← Nazad na naslovnu
        </button>
      </main>
    );
  }

  return (
    <Dashboard
      electionId={match.id}
      onPickElection={(s) => router.push(`/${s}`)}
      onBack={() => router.push("/")}
    />
  );
}
