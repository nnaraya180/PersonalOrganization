import React, { useState, useEffect } from "react";
import "./App.css";
import {
  fetchPantryItems,
  createPantryItem,
  recommendRecipes,
  sendChatMessage,
} from "./api";
import type { PantryItem, Recommendation, UserConstraints } from "./api";

type Tab = "dashboard" | "chat" | "pantry";
type Theme = "light" | "dark";

function DashboardTab() {
  const [items, setItems] = useState<PantryItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    fetchPantryItems()
      .then(setItems)
      .catch((err) => {
        console.error(err);
        setError("Could not load pantry summary.");
      })
      .finally(() => setLoading(false));
  }, []);

  const totalItems = items.length;
  const totalQuantity = items.reduce(
    (sum, it) => sum + (it.quantity ?? 0),
    0
  );
  const distinctCategories = new Set(
    items
      .map((it) => (it.category ?? "").trim())
      .filter((c) => c.length > 0)
  ).size;

  return (
    <div className="panel">
      <h2 className="panel-title">Pantry Overview</h2>
      <p className="panel-subtitle">
        High-level snapshot of what&apos;s in your pantry based on live data.
      </p>

      {loading && <p className="card-text">Loading pantry summary…</p>}
      {error && (
        <p className="card-text" style={{ color: "#b91c1c" }}>
          {error}
        </p>
      )}

      {/* Stat cards */}
      <div className="stat-grid">
        <div className="card">
          <div className="stat-label">Total items</div>
          <div className="stat-number">{totalItems}</div>
          <div className="stat-help">
            Count of distinct rows in your Item table.
          </div>
        </div>
        <div className="card">
          <div className="stat-label">Total quantity</div>
          <div className="stat-number">{totalQuantity}</div>
          <div className="stat-help">
            Sum of the quantity field across all items.
          </div>
        </div>
        <div className="card">
          <div className="stat-label">Categories</div>
          <div className="stat-number">{distinctCategories}</div>
          <div className="stat-help">
            Number of distinct item categories in your pantry.
          </div>
        </div>
      </div>

      <div className="split-grid">
        {/* Data viz card with actual images */}
        <div className="card">
          <h3 className="card-title">Data Visualization</h3>
          <p className="card-text">
            These charts show how meals cluster together based on their
            underlying data (like nutrition). They&apos;re a preview of how
            Pantry AI can group foods into patterns that drive smarter
            recommendations on this dashboard.
          </p>

          <div className="viz-placeholder">
            <div>
              <img
                src="/kmeans_pca_scatter.png"
                alt="K-means clusters in PCA space"
                className="viz-image"
              />
              <p className="viz-caption">
                K-means clusters in a 2D space after PCA. Each dot is a meal;
                colors show which cluster it belongs to.
              </p>
            </div>

            <div>
              <img
                src="/kmeans_pca_clusters_k3.png"
                alt="K-means clustering with 3 clusters"
                className="viz-image"
              />
              <p className="viz-caption">
                The same data grouped into 3 broader clusters. This helps us see
                high-level patterns in how meals are organized.
              </p>
            </div>
          </div>
        </div>

        {/* Highlights / insights card */}
        <div className="card">
          <h3 className="card-title">Highlights</h3>
          <ul className="highlights">
            <li>
              Total items: <strong>{totalItems}</strong>
            </li>
            <li>
              Total quantity across items: <strong>{totalQuantity}</strong>
            </li>
            <li>
              Distinct categories: <strong>{distinctCategories}</strong>
            </li>
          </ul>
          <p className="card-text">
            These highlights are now driven directly by your pantry data, while
            the charts on the left show how we can cluster meals to power future
            recommendations.
          </p>
        </div>
      </div>
    </div>
  );
}

type ChatMessage = {
  sender: "user" | "assistant";
  text: string;
};

function ChatTab() {
  // dropdown + text state
  const [mood, setMood] = useState<string>("");
  const [maxTime, setMaxTime] = useState<string>(""); // "<15", "<30", "<45", or ""
  const [diet, setDiet] = useState<string>("any");
  const [includeText, setIncludeText] = useState<string>("");
  const [excludeText, setExcludeText] = useState<string>("");

  // recommendation API state
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // LLM chat state
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([
    {
      sender: "assistant",
      text: "Hi! I'm your Pantry AI assistant. Ask me about recipes, meal ideas, or how to use what you have at home.",
    },
  ]);
  const [chatInput, setChatInput] = useState("");
  const [chatLoading, setChatLoading] = useState(false);
  const [chatError, setChatError] = useState<string | null>(null);

  async function handleGetRecommendations() {
    setLoading(true);
    setError(null);

    // map dropdown to minutes
    const max_time_minutes =
      maxTime === ""
        ? null
        : maxTime === "<15"
        ? 15
        : maxTime === "<30"
        ? 30
        : maxTime === "<45"
        ? 45
        : null;

    const diet_types = diet && diet !== "any" ? [diet.toLowerCase()] : null;

    const include_ingredients =
      includeText.trim().length > 0
        ? includeText
            .split(",")
            .map((s) => s.trim())
            .filter((s) => s.length > 0)
        : null;

    const exclude_ingredients =
      excludeText.trim().length > 0
        ? excludeText
            .split(",")
            .map((s) => s.trim())
            .filter((s) => s.length > 0)
        : null;

    const constraints: UserConstraints = {
      mood: mood || null,
      cuisine: null,
      energy_level: null,
      diet_types,
      include_ingredients,
      exclude_ingredients,
      prioritize_ingredient: null,
      max_time_minutes,
    };

    try {
      const recs = await recommendRecipes(constraints);
      setRecommendations(recs);
    } catch (err) {
      console.error(err);
      setError("Something went wrong fetching recommendations.");
    } finally {
      setLoading(false);
    }
  }

  async function handleSendChat(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = chatInput.trim();
    if (!trimmed || chatLoading) return;

    const userMsg: ChatMessage = { sender: "user", text: trimmed };
    setChatMessages((prev) => [...prev, userMsg]);
    setChatInput("");
    setChatError(null);
    setChatLoading(true);

    try {
      // this calls your backend /chat via sendChatMessage in api.ts
      const reply = await sendChatMessage(trimmed);
      const assistantMsg: ChatMessage = { sender: "assistant", text: reply };
      setChatMessages((prev) => [...prev, assistantMsg]);
    } catch (err) {
      console.error(err);
      setChatError("Something went wrong talking to the assistant.");
    } finally {
      setChatLoading(false);
    }
  }

  return (
    <div className="panel">
      <h2 className="panel-title">Pantry Chat (Constraints + LLM)</h2>
      <p className="panel-subtitle">
        Set constraints to get structured recipe suggestions, or chat freely
        with the assistant about what to cook.
      </p>

      <div className="split-grid">
        {/* Left: constraint form */}
        <div className="card">
          <h3 className="card-title">Set your constraints</h3>

          <div className="form-grid">
            <label>
              <span>Mood</span>
              <select value={mood} onChange={(e) => setMood(e.target.value)}>
                <option value="">Any</option>
                <option value="comfort">Comfort</option>
                <option value="light">Light</option>
                <option value="focus">Focus</option>
                <option value="indulgent">Indulgent</option>
              </select>
            </label>

            <label>
              <span>Max cooking time</span>
              <select
                value={maxTime}
                onChange={(e) => setMaxTime(e.target.value)}
              >
                <option value="">Any</option>
                <option value="<15">Under 15 min</option>
                <option value="<30">Under 30 min</option>
                <option value="<45">Under 45 min</option>
              </select>
            </label>

            <label>
              <span>Diet type</span>
              <select value={diet} onChange={(e) => setDiet(e.target.value)}>
                <option value="any">Any</option>
                <option value="vegetarian">Vegetarian</option>
                <option value="pescatarian">Pescatarian</option>
                <option value="vegan">Vegan</option>
              </select>
            </label>

            <label>
              <span>Must include (comma-separated)</span>
              <input
                placeholder="e.g., spinach, eggs"
                value={includeText}
                onChange={(e) => setIncludeText(e.target.value)}
              />
            </label>

            <label>
              <span>Exclude (comma-separated)</span>
              <input
                placeholder="e.g., tuna, salmon"
                value={excludeText}
                onChange={(e) => setExcludeText(e.target.value)}
              />
            </label>
          </div>

          <div className="button-row">
            <button
              className="primary-button"
              type="button"
              onClick={handleGetRecommendations}
              disabled={loading}
            >
              {loading ? "Finding recipes…" : "Get recipe suggestions"}
            </button>
          </div>

          {error && (
            <p className="card-text small" style={{ color: "#b91c1c" }}>
              {error}
            </p>
          )}
          {!error && (
            <p className="card-text small">
              This form sends a structured JSON payload to the{" "}
              <code>/recommend</code> endpoint. The assistant chat on the right
              is powered by the LLM.
            </p>
          )}
        </div>

        {/* Right: recommendations + LLM chat */}
        <div className="card chat-card">
          <h3 className="card-title">Recommendations & Chat</h3>

          {loading && (
            <p className="card-text">Finding recipe suggestions…</p>
          )}

          {recommendations.length > 0 && (
            <div className="chat-recommendations">
              <h4 className="chat-subtitle">Based on your constraints</h4>
              {recommendations.map((rec, idx) => (
                <div className="chat-bubble bot" key={rec.title + idx}>
                  <div className="chat-label">Pantry AI</div>
                  <div>
                    <strong>{rec.title}</strong>
                    <div className="chat-recipe-meta">
                      {rec.time_minutes != null && (
                        <span>{rec.time_minutes} min</span>
                      )}
                      {rec.time_minutes != null && rec.diet && " · "}
                      {rec.diet && <span>{rec.diet}</span>}
                    </div>
                    {rec.missing_ingredients &&
                    rec.missing_ingredients.length > 0 ? (
                      <div className="chat-recipe-missing">
                        You&apos;re missing:{" "}
                        {rec.missing_ingredients.join(", ")}
                      </div>
                    ) : (
                      <div className="chat-recipe-missing">
                        You have everything you need for this recipe.
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}

          {recommendations.length === 0 && !loading && (
            <p className="card-text">
              No recipe suggestions yet. Choose some constraints on the left and
              click <strong>Get recipe suggestions</strong>, or just start
              chatting below.
            </p>
          )}

          <div className="chat-history">
            {chatMessages.map((m, idx) => (
              <div
                key={idx}
                className={`chat-bubble ${
                  m.sender === "user" ? "user" : "bot"
                }`}
              >
                <div className="chat-label">
                  {m.sender === "user" ? "You" : "Pantry AI"}
                </div>
                <div>{m.text}</div>
              </div>
            ))}
          </div>

          {chatError && (
            <p className="card-text small" style={{ color: "#b91c1c" }}>
              {chatError}
            </p>
          )}

          <form className="chat-input" onSubmit={handleSendChat}>
            <textarea
              placeholder='Ask something like: "What can I make with beans, rice, and spinach?"'
              rows={3}
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              disabled={chatLoading}
            />
            <div className="chat-footer">
              <span className="chat-note">
                This sends your message to the LLM-powered assistant on the
                backend.
              </span>
              <button
                className="primary-button"
                type="submit"
                disabled={chatLoading}
              >
                {chatLoading ? "Thinking…" : "Ask Pantry AI"}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}


function PantryTab() {
  const [items, setItems] = useState<PantryItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [name, setName] = useState("");
  const [category, setCategory] = useState("");
  const [quantity, setQuantity] = useState<string>("");
  const [saving, setSaving] = useState(false);

  // Load items on first render
  useEffect(() => {
    setLoading(true);
    fetchPantryItems()
      .then(setItems)
      .catch((err) => {
        console.error(err);
        setError("Could not load pantry items.");
      })
      .finally(() => setLoading(false));
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;

    setSaving(true);
    setError(null);

    try {
      const qtyNum =
        quantity.trim() === "" ? undefined : Number.parseInt(quantity, 10) || 0;

      const newItem = await createPantryItem({
        name: name.trim(),
        category: category.trim() || undefined,
        quantity: qtyNum,
      });

      setItems((prev) => [...prev, newItem]);

      // clear form
      setName("");
      setCategory("");
      setQuantity("");
    } catch (err) {
      console.error(err);
      setError("Could not save item.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="panel">
      <h2 className="panel-title">Pantry &amp; Recipes</h2>
      <p className="panel-subtitle">
        View and manage items and saved recipes. This is where CRUD will live.
      </p>

      <div className="split-grid">
        {/* Form side */}
        <div className="card">
          <h3 className="card-title">Add / Edit Pantry Item</h3>

          <form className="form-grid" onSubmit={handleSubmit}>
            <label>
              <span>Item name</span>
              <input
                placeholder="e.g., Black beans"
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </label>

            <label>
              <span>Category</span>
              <input
                placeholder="e.g., canned, produce, snack"
                value={category}
                onChange={(e) => setCategory(e.target.value)}
              />
            </label>

            <label>
              <span>Quantity</span>
              <input
                placeholder="e.g., 2"
                value={quantity}
                onChange={(e) => setQuantity(e.target.value)}
              />
            </label>

            <div className="button-row">
              <button className="primary-button" type="submit" disabled={saving}>
                {saving ? "Saving…" : "Save item"}
              </button>
              <button
                className="secondary-button danger"
                type="button"
                disabled
                title="Delete will be added later"
              >
                Delete (future)
              </button>
            </div>
          </form>

          {error && (
            <p className="card-text small" style={{ color: "#b91c1c" }}>
              {error}
            </p>
          )}
          {!error && (
            <p className="card-text small">
              For the MVP, this form talks to our FastAPI backend. Next
              iterations will add editing and deleting.
            </p>
          )}
        </div>

        {/* Items / recipes side */}
        <div className="card">
          <h3 className="card-title">Current Items</h3>

          {loading ? (
            <p className="card-text">Loading items…</p>
          ) : items.length === 0 ? (
            <p className="card-text">
              No items yet. Add your first item on the left.
            </p>
          ) : (
            items.map((item) => (
              <div className="item-row" key={item.id}>
                <div>
                  <div className="item-name">{item.name}</div>
                  <div className="item-meta">
                    {item.category && <span>{item.category}</span>}
                    {item.quantity !== null &&
                      item.quantity !== undefined && (
                        <span>
                          {item.category ? " • " : ""}
                          {item.quantity} unit
                          {item.quantity === 1 ? "" : "s"}
                        </span>
                      )}
                    {!item.category &&
                      (item.quantity === null ||
                        item.quantity === undefined) && (
                        <span>No metadata</span>
                      )}
                  </div>
                </div>
              </div>
            ))
          )}

          <hr className="divider" />

          <div className="recipes-block">
            <div className="recipes-title">Linked recipes (examples)</div>
            <ul>
              <li>Lemony Chickpea Pasta</li>
              <li>Creamy Spinach Pasta Bake</li>
            </ul>
          </div>

          <p className="card-text small">
            Future: this will be populated directly from the database using our
            real recipe tables.
          </p>
        </div>
      </div>
    </div>
  );
}

export default function App() {
  const [activeTab, setActiveTab] = useState<Tab>("dashboard");
  const [theme, setTheme] = useState<Theme>("dark"); // default to dark mode

  useEffect(() => {
    let buffer = "";

    const handleKeyDown = (e: KeyboardEvent) => {
      // Ignore if you're typing in an input/textarea/contenteditable
      const active = document.activeElement as HTMLElement | null;
      if (
        active &&
        (active.tagName === "INPUT" ||
          active.tagName === "TEXTAREA" ||
          active.isContentEditable)
      ) {
        return;
      }

      // Only care about letter keys
      const char = e.key.toLowerCase();
      if (!/^[a-z]$/.test(char)) return;

      // Keep the last 5 characters typed
      buffer = (buffer + char).slice(-5);

      if (buffer.endsWith("dark")) {
        setTheme("dark");
      } else if (buffer.endsWith("light")) {
        setTheme("light");
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, []);

  return (
    <div className={`app ${theme}-theme`}>
      <header className="top-bar">
        <div>
          <h1 className="app-title">Kitchen Pal</h1>
          {/* subheader removed */}
        </div>
        <span className="demo-pill">Demo build</span>
      </header>

      <main className="main">
        <div className="tabs">
          <button
            className={`tab ${activeTab === "dashboard" ? "active" : ""}`}
            onClick={() => setActiveTab("dashboard")}
          >
            Dashboard
          </button>
          <button
            className={`tab ${activeTab === "chat" ? "active" : ""}`}
            onClick={() => setActiveTab("chat")}
          >
            Chat
          </button>
          <button
            className={`tab ${activeTab === "pantry" ? "active" : ""}`}
            onClick={() => setActiveTab("pantry")}
          >
            Pantry &amp; Recipes
          </button>
        </div>

        <section className="tab-panel">
          {activeTab === "dashboard" && <DashboardTab />}
          {activeTab === "chat" && <ChatTab />}
          {activeTab === "pantry" && <PantryTab />}
        </section>
      </main>
    </div>
  );
}
