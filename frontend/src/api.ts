// src/api.ts

// ---------------------------------------------
// Existing pantry item API
// ---------------------------------------------

export interface PantryItem {
  id: number;
  name: string;
  category?: string | null;
  quantity?: number | null;
  purchase_date?: string | null;
  expiration_date?: string | null;
  estimated_calories?: number | null;
  estimated_protein_g?: number | null;
  estimated_carbs_g?: number | null;
  estimated_fat_g?: number | null;
}

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export async function fetchPantryItems(): Promise<PantryItem[]> {
  const res = await fetch(`${API_URL}/items`);
  if (!res.ok) {
    throw new Error("Failed to fetch pantry items");
  }
  return res.json();
}

export interface CreatePantryItemInput {
  name: string;
  category?: string | null;
  quantity?: number | null;
  purchase_date?: string | null;
  expiration_date?: string | null;
  estimated_calories?: number | null;
  estimated_protein_g?: number | null;
  estimated_carbs_g?: number | null;
  estimated_fat_g?: number | null;
}

export async function createPantryItem(
  input: CreatePantryItemInput
): Promise<PantryItem> {
  const res = await fetch(`${API_URL}/items`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });

  if (!res.ok) {
    throw new Error("Failed to create pantry item");
  }

  return res.json();
}

export async function createPantryItemsBulk(
  input: CreatePantryItemInput[]
): Promise<PantryItem[]> {
  const res = await fetch(`${API_URL}/items/bulk`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });

  if (!res.ok) {
    throw new Error(`Failed to create pantry items (bulk): ${res.status}`);
  }

  return res.json();
}

export async function updatePantryItem(
  itemId: number,
  patch: Partial<CreatePantryItemInput>
): Promise<PantryItem> {
  const res = await fetch(`${API_URL}/items/${itemId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(patch),
  });

  if (!res.ok) {
    throw new Error(`Failed to update pantry item: ${res.status}`);
  }

  return res.json();
}

export async function deletePantryItem(itemId: number): Promise<void> {
  const res = await fetch(`${API_URL}/items/${itemId}`, {
    method: "DELETE",
  });

  if (!res.ok) {
    throw new Error(`Failed to delete pantry item: ${res.status}`);
  }
}

export async function consumePantryItem(
  itemId: number,
  amount: number
): Promise<PantryItem> {
  const res = await fetch(`${API_URL}/items/${itemId}/consume`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ amount }),
  });

  if (!res.ok) {
    throw new Error(`Failed to consume pantry item: ${res.status}`);
  }

  return res.json();
}

export async function restockPantryItem(
  itemId: number,
  amount: number
): Promise<PantryItem> {
  const res = await fetch(`${API_URL}/items/${itemId}/restock`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ amount }),
  });

  if (!res.ok) {
    throw new Error(`Failed to restock pantry item: ${res.status}`);
  }

  return res.json();
}

export async function sendChatMessage(message: string): Promise<string> {
  const resp = await fetch(`${API_URL}/chat`, {
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

export interface Recipe {
  id: number;
  title: string;
  time_minutes?: number | null;
  ingredients?: string[];
  cuisine?: string | null;
  diet?: string | null;
  avg_rating?: number | null;
  protein_g?: number | null;
  carbs_g?: number | null;
  fat_g?: number | null;
  calories?: number | null;
}

export async function fetchRecipes(): Promise<Recipe[]> {
  const res = await fetch(`${API_URL}/recipes`);
  if (!res.ok) {
    throw new Error("Failed to fetch recipes");
  }
  return res.json();
}

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
  const res = await fetch(`${API_URL}/recommend`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(constraints),
  });

  if (!res.ok) {
    throw new Error(`Failed to fetch recommendations: ${res.status}`);
  }

  return res.json();
}

// ---------------------------------------------
// NEW — Chat-based Recipe Endpoint
// ---------------------------------------------

export interface RecipeSuggestion {
  recipe_id: number;
  title: string;
  reason: string;
  time_minutes?: number | null;
  mood_effect?: string | null;
}

export interface ChatRecipesResponse {
  reply: string;
  recipes: RecipeSuggestion[];
}

export async function fetchRecipeChat(
  payload: any
): Promise<ChatRecipesResponse> {
  const res = await fetch(`${API_URL}/chat/recipes`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    throw new Error(
      `Failed to fetch recipe chat: ${res.status}`
    );
  }

  return res.json();
}

// ---------------------------------------------
// NEW — Feedback Endpoint
// ---------------------------------------------

export interface FeedbackRequest {
  recipe_id?: number | null;
  recipe_title: string;
  taste_rating?: number | null;
  liked_tags?: string[] | null;
  disliked_tags?: string[] | null;
  feel_after?: string | null;
  notes?: string | null;
}

export async function sendFeedback(
  feedback: FeedbackRequest
): Promise<{ message: string }> {
  const res = await fetch(`${API_URL}/chat/log`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(feedback),
  });

  if (!res.ok) {
    throw new Error(`Failed to send feedback: ${res.status}`);
  }

  return res.json();
}

export async function getFeedbackLogs(): Promise<any[]> {
  const res = await fetch(`${API_URL}/chat/logs`, {
    method: "GET",
    headers: { "Content-Type": "application/json" },
  });

  if (!res.ok) {
    throw new Error(`Failed to fetch feedback logs: ${res.status}`);
  }

  return res.json();
}
