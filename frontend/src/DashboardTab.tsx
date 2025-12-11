import { useEffect, useMemo, useState } from "react";
import {
  Box,
  Flex,
  Stack,
  SimpleGrid,
  Heading,
  Text,
  Badge,
  Button,
  Card,
  HStack,
} from "@chakra-ui/react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
} from "recharts";
import { fetchPantryItems, type PantryItem as APIPantryItem } from "./api";

export type MealEvent = {
  id: number;
  date: string; // ISO date
  recipeTitle: string;
  moodAfter: number; // 0 to 2
  energyAfter: number; // 0 to 2
  calories: number;
  protein: number;
  fiber: number;
};

type ExpiringItem = {
  id: number;
  name: string;
  expiresOn: string;
};

type SummaryCardProps = {
  title: string;
  value: string;
  subtitle?: string;
};

type GoalRingProps = {
  label: string;
  value: number;
  goal: number;
  color: string;
};

const nutritionGoals = { calories: 1800, protein: 70, fiber: 25 };
const todayTotals = { calories: 1350, protein: 52, fiber: 18 };

const suggestedRecipes = [
  { title: "Miso Ginger Salmon", timeMinutes: 25, tags: ["High protein", "Light"], reason: "Energizing and protein-forward for training days." },
  { title: "Halloumi Grain Bowl", timeMinutes: 30, tags: ["Veg-friendly", "Fiber"], reason: "Balances fiber and protein to keep energy steady." },
  { title: "Chipotle Chicken Wrap", timeMinutes: 20, tags: ["Quick", "Meal prep"], reason: "Great for lunches; good macros and portable." },
];

const fallbackExpiring: ExpiringItem[] = [
  { id: 101, name: "Spinach", expiresOn: daysFromNowISO(2) },
  { id: 102, name: "Chicken breast", expiresOn: daysFromNowISO(3) },
  { id: 103, name: "Berries", expiresOn: daysFromNowISO(5) },
];

const mealHistory: MealEvent[] = [
  { id: 1, date: daysAgoISO(0), recipeTitle: "Lemon Garlic Salmon", moodAfter: 1.6, energyAfter: 1.4, calories: 620, protein: 42, fiber: 6 },
  { id: 2, date: daysAgoISO(1), recipeTitle: "Turkey Rice Skillet", moodAfter: 1.2, energyAfter: 1.3, calories: 540, protein: 38, fiber: 5 },
  { id: 3, date: daysAgoISO(1), recipeTitle: "Spinach Omelette", moodAfter: 1.4, energyAfter: 1.5, calories: 320, protein: 24, fiber: 3 },
  { id: 4, date: daysAgoISO(2), recipeTitle: "Chickpea Curry", moodAfter: 1.1, energyAfter: 1.0, calories: 580, protein: 22, fiber: 10 },
  { id: 5, date: daysAgoISO(3), recipeTitle: "Chicken Tacos", moodAfter: 1.5, energyAfter: 1.3, calories: 520, protein: 36, fiber: 7 },
  { id: 6, date: daysAgoISO(4), recipeTitle: "Greek Yogurt Bowl", moodAfter: 1.3, energyAfter: 1.5, calories: 350, protein: 28, fiber: 4 },
  { id: 7, date: daysAgoISO(5), recipeTitle: "Veggie Stir Fry", moodAfter: 1.0, energyAfter: 0.9, calories: 480, protein: 20, fiber: 8 },
  { id: 8, date: daysAgoISO(6), recipeTitle: "Overnight Oats", moodAfter: 1.2, energyAfter: 1.1, calories: 380, protein: 18, fiber: 6 },
];

function daysAgoISO(days: number) {
  const d = new Date();
  d.setDate(d.getDate() - days);
  return d.toISOString();
}

function daysFromNowISO(days: number) {
  const d = new Date();
  d.setDate(d.getDate() + days);
  return d.toISOString();
}

function shortDayLabel(dateStr: string) {
  return new Date(dateStr).toLocaleDateString(undefined, { weekday: "short" });
}

function moodEmoji(mood: number) {
  if (mood >= 1.5) return "😀";
  if (mood >= 1.1) return "🙂";
  if (mood >= 0.8) return "😐";
  return "😴";
}

function energyLabel(energy: number) {
  if (energy >= 1.4) return "Energy: high";
  if (energy >= 1.0) return "Energy: medium";
  return "Energy: low";
}

function urgencyBadge(daysLeft: number) {
  if (daysLeft <= 2) return { label: "Urgent", bg: "#FEE2E2", color: "#991B1B" };
  if (daysLeft <= 5) return { label: "Soon", bg: "#FEF3C7", color: "#92400E" };
  return { label: "OK", bg: "#E5E7EB", color: "#374151" };
}

const macroColors = ["#3B82F6", "#F59E0B", "#10B981"];

function SummaryCard({ title, value, subtitle }: SummaryCardProps) {
  return (
    <Card.Root borderWidth="1px" borderColor="gray.200" bg="white" borderRadius="lg" shadow="sm" p={4}>
      <Card.Body>
        <Text fontSize="sm" color="gray.500" mb={1}>
          {title}
        </Text>
        <Heading size="lg" mb={1}>
          {value}
        </Heading>
        {subtitle && (
          <Text fontSize="sm" color="gray.600">
            {subtitle}
          </Text>
        )}
      </Card.Body>
    </Card.Root>
  );
}

function GoalRing({ label, value, goal, color }: GoalRingProps) {
  const pct = Math.min(100, (value / goal) * 100);
  const angle = (pct / 100) * 360;
  return (
    <Card.Root borderWidth="1px" borderRadius="lg" p={4} shadow="sm" bg="white" borderColor="gray.200">
      <Card.Body>
        <Flex align="center" justify="center" mb={3}>
          <Box
            position="relative"
            w="120px"
            h="120px"
            borderRadius="full"
            bg="gray.100"
            overflow="hidden"
          >
            <Box
              position="absolute"
              inset={0}
              bg={`conic-gradient(${color} ${angle}deg, #E5E7EB ${angle}deg)`}
            />
            <Flex
              position="absolute"
              inset="10%"
              borderRadius="full"
              bg="white"
              align="center"
              justify="center"
            >
              <Text fontWeight="bold" textAlign="center">
                {value}/{goal}
              </Text>
            </Flex>
          </Box>
        </Flex>
        <Stack gap={0} align="center">
          <Text fontWeight="semibold">{label}</Text>
          <Text fontSize="sm" color="gray.500">
            Today
          </Text>
        </Stack>
      </Card.Body>
    </Card.Root>
  );
}

function GoalsRingsSection({ caloriesPct, proteinPct, fiberPct }: { caloriesPct: number; proteinPct: number; fiberPct: number }) {
  const goals = [
    { label: "Calories", value: todayTotals.calories, goal: nutritionGoals.calories, pct: caloriesPct, color: "#0EA5E9" },
    { label: "Protein", value: todayTotals.protein, goal: nutritionGoals.protein, pct: proteinPct, color: "#10B981" },
    { label: "Fiber", value: todayTotals.fiber, goal: nutritionGoals.fiber, pct: fiberPct, color: "#F59E0B" },
  ];

  return (
    <Box>
      <Heading size="md" mb={3}>
        Daily goals
      </Heading>
      <SimpleGrid columns={{ base: 1, sm: 3 }} gap={4}>
        {goals.map((g) => (
          <GoalRing key={g.label} label={g.label} value={g.value} goal={g.goal} color={g.color} />
        ))}
      </SimpleGrid>
    </Box>
  );
}

function MoodEnergyChart({ data }: { data: { day: string; mood: number; energy: number }[] }) {
  return (
    <Card.Root borderWidth="1px" borderColor="gray.200" bg="white" borderRadius="lg" shadow="sm" p={4} minH="280px">
      <Card.Body>
        <Heading size="sm" mb={3}>
          Mood and energy after meals
        </Heading>
        <ResponsiveContainer width="100%" height={220}>
          <LineChart data={data} margin={{ left: 0, right: 8, top: 8, bottom: 0 }}>
            <XAxis dataKey="day" stroke="currentColor" fontSize={12} tickLine={false} axisLine={{ stroke: "#E5E7EB" }} />
            <YAxis stroke="currentColor" fontSize={12} tickLine={false} axisLine={{ stroke: "#E5E7EB" }} domain={[0, 2]} />
            <Tooltip />
            <Legend verticalAlign="top" height={24} />
            <Line type="monotone" dataKey="mood" stroke="#3B82F6" strokeWidth={2} dot={{ r: 3 }} name="Mood" />
            <Line type="monotone" dataKey="energy" stroke="#10B981" strokeWidth={2} dot={{ r: 3 }} name="Energy" />
          </LineChart>
        </ResponsiveContainer>
      </Card.Body>
    </Card.Root>
  );
}

function MacroChart({ data }: { data: { name: string; value: number }[] }) {
  const total = data.reduce((s, d) => s + d.value, 0) || 1;
  return (
    <Card.Root borderWidth="1px" borderColor="gray.200" bg="white" borderRadius="lg" shadow="sm" p={4} minH="280px">
      <Card.Body>
        <Heading size="sm" mb={3}>
          Weekly macro breakdown
        </Heading>
        <ResponsiveContainer width="100%" height={220}>
          <PieChart>
            <Pie data={data} dataKey="value" nameKey="name" innerRadius={50} outerRadius={80} paddingAngle={3}>
              {data.map((_, idx) => (
                <Cell key={idx} fill={macroColors[idx % macroColors.length]} />
              ))}
            </Pie>
            <Legend />
            <Tooltip formatter={(v: number, name: string) => [`${Math.round((v / total) * 100)}%`, name]} />
          </PieChart>
        </ResponsiveContainer>
      </Card.Body>
    </Card.Root>
  );
}

function ExpiringItemsPanel({ items }: { items: ExpiringItem[] }) {
  return (
    <Card.Root borderWidth="1px" borderColor="gray.200" bg="white" borderRadius="lg" shadow="sm" p={4}>
      <Card.Body>
        <Heading size="sm" mb={3}>
          Expiring soon
        </Heading>
        {items.length === 0 ? (
          <Text color="gray.500">No items expiring in the next week.</Text>
        ) : (
          <Stack gap={2} mb={4}>
            {items.map((item) => {
              const daysLeft = Math.max(0, Math.ceil((new Date(item.expiresOn).getTime() - Date.now()) / (1000 * 60 * 60 * 24)));
              const badge = urgencyBadge(daysLeft);
              return (
                <Flex key={item.id} align="center" justify="space-between">
                  <Box>
                    <Text fontWeight="semibold">{item.name}</Text>
                    <Text fontSize="sm" color="gray.500">
                      {daysLeft} days remaining
                    </Text>
                  </Box>
                  <Badge bg={badge.bg} color={badge.color} px={2} py={1} borderRadius="full">
                    {badge.label}
                  </Badge>
                </Flex>
              );
            })}
          </Stack>
        )}
        <Button
          size="sm"
          bg="blue.500"
          color="white"
          _hover={{ bg: "blue.600" }}
          onClick={() => alert("Feature coming soon: recipe suggestions for expiring items")}
        >
          See recipes using these
        </Button>
      </Card.Body>
    </Card.Root>
  );
}

function SuggestedRecipesPanel() {
  return (
    <Card.Root borderWidth="1px" borderColor="gray.200" bg="white" borderRadius="lg" shadow="sm" p={4}>
      <Card.Body>
        <Heading size="sm" mb={3}>
          Suggested recipes this week
        </Heading>
        <Stack gap={3}>
          {suggestedRecipes.map((r, idx) => (
            <Box key={idx} borderWidth="1px" borderColor="gray.200" borderRadius="md" p={3}>
              <HStack justify="space-between" align="start" mb={2}>
                <Heading size="sm">{r.title}</Heading>
                <Badge bg="#E0F2FE" color="#075985" borderRadius="full" px={2} py={1}>
                  {r.timeMinutes} min
                </Badge>
              </HStack>
              <HStack gap={2} flexWrap="wrap" mb={2}>
                {r.tags.map((t) => (
                  <Badge key={t} bg="#EEF2FF" color="#3730A3" borderRadius="full" px={2} py={1}>
                    {t}
                  </Badge>
                ))}
              </HStack>
              <Text fontSize="sm" color="gray.600">{r.reason}</Text>
            </Box>
          ))}
        </Stack>
      </Card.Body>
    </Card.Root>
  );
}

function RecentMealsPanel({ meals }: { meals: MealEvent[] }) {
  return (
    <Card.Root borderWidth="1px" borderColor="gray.200" bg="white" borderRadius="lg" shadow="sm" p={4}>
      <Card.Body>
        <Heading size="sm" mb={3}>
          Recent meals
        </Heading>
        <Stack gap={3}>
          {meals.map((m) => (
            <Flex key={m.id} align="center" justify="space-between" borderWidth="1px" borderColor="gray.200" borderRadius="md" p={3}>
              <Box>
                <Text fontSize="sm" color="gray.500">
                  {new Date(m.date).toLocaleDateString(undefined, { month: "short", day: "numeric" })}
                </Text>
                <Text fontWeight="semibold">{m.recipeTitle}</Text>
                <Text fontSize="sm" color="gray.600">
                  {energyLabel(m.energyAfter)}
                </Text>
              </Box>
              <Text fontSize="2xl" aria-label="mood icon">
                {moodEmoji(m.moodAfter)}
              </Text>
            </Flex>
          ))}
        </Stack>
      </Card.Body>
    </Card.Root>
  );
}

function computeWeeklyStats(history: MealEvent[]) {
  const sevenDaysAgo = new Date();
  sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 6);
  const lastWeek = history.filter((h) => new Date(h.date).getTime() >= sevenDaysAgo.getTime());

  const mealsThisWeek = lastWeek.length;
  const avgMoodAfter = mealsThisWeek
    ? lastWeek.reduce((s, m) => s + m.moodAfter, 0) / mealsThisWeek
    : 0;
  const avgEnergyAfter = mealsThisWeek
    ? lastWeek.reduce((s, m) => s + m.energyAfter, 0) / mealsThisWeek
    : 0;

  const totalCalories = lastWeek.reduce((s, m) => s + m.calories, 0);
  const totalProtein = lastWeek.reduce((s, m) => s + m.protein, 0);
  const totalFiber = lastWeek.reduce((s, m) => s + m.fiber, 0);

  const avgDailyCalories = totalCalories / 7;
  const avgDailyProtein = totalProtein / 7;
  const avgDailyFiber = totalFiber / 7;

  return {
    lastWeek,
    mealsThisWeek,
    avgMoodAfter,
    avgEnergyAfter,
    avgDailyCalories,
    avgDailyProtein,
    avgDailyFiber,
    totalCalories,
    totalProtein,
    totalFiber,
  };
}

function buildTrendData(history: MealEvent[]) {
  const map = new Map<string, { moodSum: number; energySum: number; count: number }>();
  for (let i = 0; i < 7; i++) {
    const date = daysAgoISO(i).split("T")[0];
    map.set(date, { moodSum: 0, energySum: 0, count: 0 });
  }
  history.forEach((m) => {
    const key = m.date.split("T")[0];
    if (map.has(key)) {
      const entry = map.get(key)!;
      entry.moodSum += m.moodAfter;
      entry.energySum += m.energyAfter;
      entry.count += 1;
    }
  });

  const ordered = Array.from(map.entries())
    .sort((a, b) => (a[0] > b[0] ? 1 : -1))
    .map(([date, val]) => ({
      day: shortDayLabel(date),
      mood: val.count ? +(val.moodSum / val.count).toFixed(2) : 0,
      energy: val.count ? +(val.energySum / val.count).toFixed(2) : 0,
    }));
  return ordered;
}

function buildMacroData(totalCalories: number, totalProtein: number) {
  const weeklyCarbs = (totalCalories * 0.45) / 4;
  const weeklyFat = (totalCalories * 0.3) / 9;
  const weeklyProtein = totalProtein;
  return [
    { name: "Protein", value: Math.max(0, weeklyProtein) },
    { name: "Carbs", value: Math.max(0, weeklyCarbs) },
    { name: "Fat", value: Math.max(0, weeklyFat) },
  ];
}

function DashboardTab() {
  const [expiringItems, setExpiringItems] = useState<ExpiringItem[]>([]);
  const [expiringError, setExpiringError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    async function load() {
      try {
        const data = await fetchPantryItems();
        if (!mounted) return;
        const soon = data
          .filter((item: APIPantryItem) => item.expiration_date)
          .map((item) => ({
            id: item.id,
            name: item.name,
            expiresOn: item.expiration_date as string,
          }))
          .sort((a, b) => new Date(a.expiresOn).getTime() - new Date(b.expiresOn).getTime())
          .slice(0, 3);
        setExpiringItems(soon);
      } catch (err) {
        console.error("Failed to load pantry items", err);
        setExpiringError("Using sample data");
        if (mounted) setExpiringItems(fallbackExpiring);
      }
    }
    load();
    return () => {
      mounted = false;
    };
  }, []);

  const stats = useMemo(() => computeWeeklyStats(mealHistory), []);
  const trendData = useMemo(() => buildTrendData(stats.lastWeek), [stats.lastWeek]);
  const macroData = useMemo(
    () => buildMacroData(stats.totalCalories, stats.totalProtein),
    [stats.totalCalories, stats.totalProtein]
  );

  const caloriesPct = (todayTotals.calories / nutritionGoals.calories) * 100;
  const proteinPct = (todayTotals.protein / nutritionGoals.protein) * 100;
  const fiberPct = (todayTotals.fiber / nutritionGoals.fiber) * 100;

  const summarySubtitleMood = "Up 12% from last week";
  const summarySubtitleNutrition = "Meeting 2 of 3 goals";

  const recentMeals = [...stats.lastWeek]
    .sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime())
    .slice(0, 4);

  return (
    <Box maxW="960px" mx="auto" px={{ base: 4, md: 6 }} py={{ base: 4, md: 6 }}>
      <Heading size="lg" mb={4}>
        Dashboard
      </Heading>

      <SimpleGrid columns={{ base: 1, md: 3 }} gap={4} mb={6}>
        <SummaryCard title="Meals logged" value={`${stats.mealsThisWeek}`} subtitle="New recipes tried: 3" />
        <SummaryCard
          title="Average mood after meals"
          value={`${moodEmoji(stats.avgMoodAfter)} ${stats.avgMoodAfter.toFixed(2)}`}
          subtitle={summarySubtitleMood}
        />
        <SummaryCard
          title="Nutrition snapshot"
          value={`${Math.round(stats.avgDailyCalories)} kcal / ${Math.round(stats.avgDailyProtein)}g protein`}
          subtitle={summarySubtitleNutrition}
        />
      </SimpleGrid>

      <GoalsRingsSection caloriesPct={caloriesPct} proteinPct={proteinPct} fiberPct={fiberPct} />

      <Box borderBottom="1px solid #E5E7EB" my={6} />

      <SimpleGrid columns={{ base: 1, md: 2 }} gap={4} mb={6}>
        <MoodEnergyChart data={trendData} />
        <MacroChart data={macroData} />
      </SimpleGrid>

      <SimpleGrid columns={{ base: 1, lg: 3 }} gap={4}>
        <ExpiringItemsPanel items={expiringItems} />
        <SuggestedRecipesPanel />
        <RecentMealsPanel meals={recentMeals} />
      </SimpleGrid>

      {expiringError && (
        <Text mt={4} fontSize="sm" color="orange.500">
          {expiringError}
        </Text>
      )}
    </Box>
  );
}

export default DashboardTab;
