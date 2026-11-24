import { useEffect, useState } from "react";
import { ScrollView, StyleSheet, Text, View } from "react-native";
import { request } from "../api";
import { LevelTag, Loading } from "../components";
import { colors, common } from "../theme";

const percent = (c, t) => (t ? `${Math.round((c / t) * 100)}%` : "sin datos");

export default function StatsScreen() {
  const [stats, setStats] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    request("/stats/").then(setStats).catch((err) => setError(err.message));
  }, []);

  if (!stats) return error ? <Text style={[common.error, { padding: 16 }]}>{error}</Text> : <Loading />;
  const max = Math.max(1, ...stats.days.map((d) => d.total));
  return (
    <ScrollView style={common.screen} contentContainerStyle={common.content}>
      <Text style={common.title}>Estadísticas</Text>
      <View style={common.row}>
        <View style={[common.card, { flex: 1 }]}>
          <Text style={common.subtitle}>Respuestas</Text>
          <Text style={styles.big}>{stats.total}</Text>
        </View>
        <View style={[common.card, { flex: 1 }]}>
          <Text style={common.subtitle}>Acierto</Text>
          <Text style={styles.big}>{percent(stats.correct, stats.total)}</Text>
        </View>
      </View>
      <View style={common.card}>
        <Text style={styles.name}>Últimos 14 días</Text>
        <View style={styles.bars}>
          {stats.days.map((d) => (
            <View key={d.date} style={[styles.bar, { height: 4 + (d.total / max) * 60 }]} />
          ))}
        </View>
      </View>
      {stats.topics.map((t) => (
        <View key={t.id} style={common.card}>
          <Text style={styles.name}>{t.name}</Text>
          <Text style={common.subtitle}>{t.total} respuestas · acierto {percent(t.correct, t.total)}</Text>
          {t.uses_levels ? (
            <>
              <LevelTag level={t.level} prefix="Nivel actual" />
              <LevelTag level={t.max_level} prefix="Máximo alcanzado" />
              {t.evolution.length > 1 && (
                <View style={styles.evolution}>
                  {t.evolution.map((level, i) => (
                    <View key={i} style={[styles.dot, { bottom: (level - 1) * 12 }]} />
                  ))}
                </View>
              )}
            </>
          ) : null}
        </View>
      ))}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  big: { fontSize: 32, fontWeight: "800", color: colors.text },
  name: { fontSize: 16, fontWeight: "700", color: colors.text },
  bars: { flexDirection: "row", alignItems: "flex-end", gap: 4, height: 68 },
  bar: { flex: 1, backgroundColor: colors.primary, borderRadius: 3 },
  evolution: { flexDirection: "row", height: 56, alignItems: "flex-end", gap: 2, marginTop: 4 },
  dot: { flex: 1, height: 6, minWidth: 2, backgroundColor: colors.primary, borderRadius: 3, position: "relative" },
});
