"use client";

import { useRouter } from "next/navigation";
import useSWR from "swr";
import { api } from "@/lib/api";
import ElectionPicker from "@/components/ElectionPicker";

export default function Landing() {
  const router = useRouter();
  const { data: elections, error, isLoading } = useSWR("elections", api.elections);

  return (
    <main className="flex flex-col h-full w-full">
      <ElectionPicker
        elections={elections}
        isLoading={isLoading && !error}
        onPick={(id) => {
          const slug = elections?.find((e) => e.id === id)?.slug;
          if (slug) router.push(`/${slug}`);
        }}
      />
    </main>
  );
}
