// src/api.ts

// ---------------------------------------------
// Existing pantry item API
// ---------------------------------------------

export interface PantryItem {
  id: number;
  name: string;
  category?: string | null;
  quantity?: number | null;
}

const API_BASE = "http://127.0.0.1:8000";

export async function fetchPantryItems(): Promise<PantryItem[]> {
  const res = await fetch(`${API_BASE}/items`);
  if (!res.ok) {
    throw new Error("Failed to fetch pantry items");
  }
  return res.json();
}

export interface CreatePantryItemInput {
  name: string;
  category?: string | null;
  quantity?: number | null;
}

export async function createPantryItem(
  input: CreatePantryItemInput
): Promise<PantryItem> {
  const res = await fetch(`${API_BASE}/items`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });

  if (!res.ok) {
    throw new Error("Failed to create pantry item");
  }

  return res.json();
}

export async function sendChatMessage(message: string): Promise<string> {
  const resp = await fetch("http://localhost:8000/chat", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ message }),
  });

  if (!resp.ok) {
    throw new Error("Chat request failed");
  }

  const data = await resp.json();
  return data.reply as string;
}

// ---------------------------------------------
// NEW — Recommendation API
// ---------------------------------------------

export interface UserConstraints {
  cuisine?: string[] | null;
  mood?: string | null;
  energy_level?: string | null;

  diet_types?: string[] | null;
  include_ingredients?: string[] | null;
  exclude_ingredients?: string[] | null;
  prioritize_ingredient?: string | null;

  max_time_minutes?: number | null;
}

export interface Recommendation {
  title: string;
  missing_ingredients: string[];
  cuisine: string | null;
  avg_rating: number | null;

  // If you want to display metadata from your DB:
  id?: number;
  time_minutes?: number | null;
  diet?: string | null;
}

export async function recommendRecipes(
  constraints: UserConstraints
): Promise<Recommendation[]> {
  const res = await fetch(`${API_BASE}/recommend`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(constraints),
  });

  if (!res.ok) {
    throw new Error(`Failed to fetch recommendations: ${res.status}`);
  }

  return res.json();
}
