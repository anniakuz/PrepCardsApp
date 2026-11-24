import { StatusBar } from "expo-status-bar";
import { useCallback, useEffect, useState } from "react";
import { ActivityIndicator, Pressable, StyleSheet, Text, View } from "react-native";
import { SafeAreaProvider, SafeAreaView } from "react-native-safe-area-context";
import { loadSession, logout, request, setSessionExpiredHandler } from "./src/api";
import ChatScreen from "./src/screens/ChatScreen";
import LoginScreen from "./src/screens/LoginScreen";
import PracticeScreen from "./src/screens/PracticeScreen";
import StatsScreen from "./src/screens/StatsScreen";
import TopicsScreen from "./src/screens/TopicsScreen";
import { colors, common } from "./src/theme";

const TABS = [
  ["topics", "Mis temas"],
  ["stats", "Estadísticas"],
];

export default function App() {
  const [loading, setLoading] = useState(true);
  const [user, setUser] = useState(null);
  const [tab, setTab] = useState("topics");
  const [practice, setPractice] = useState(null);
  const [chat, setChat] = useState(null);

  const loadUser = useCallback(async () => {
    setUser(await request("/auth/me/"));
  }, []);

  useEffect(() => {
    setSessionExpiredHandler(() => setUser(null));
    (async () => {
      try {
        if (await loadSession()) await loadUser();
      } catch {
        // sin sesión válida se muestra el login
      } finally {
        setLoading(false);
      }
    })();
  }, [loadUser]);

  async function exit() {
    await logout();
    setPractice(null);
    setChat(null);
    setTab("topics");
    setUser(null);
  }

  let body;
  if (loading) {
    body = (
      <View style={[common.screen, styles.center]}>
        <ActivityIndicator color={colors.primary} />
      </View>
    );
  } else if (!user) {
    body = <LoginScreen onLogin={loadUser} />;
  } else if (practice) {
    body = <PracticeScreen topic={practice} onExit={() => setPractice(null)} />;
  } else if (chat) {
    body = <ChatScreen chat={chat} userId={user.id} onExit={() => setChat(null)} />;
  } else {
    body = (
      <>
        <View style={styles.header}>
          <Text style={styles.brand}>PrepCards</Text>
          <Pressable onPress={exit} hitSlop={10}>
            <Text style={styles.logout}>Salir</Text>
          </Pressable>
        </View>
        {tab === "topics" ? (
          <TopicsScreen onPractice={setPractice} onChat={setChat} />
        ) : (
          <StatsScreen />
        )}
        <View style={styles.tabs}>
          {TABS.map(([name, label]) => (
            <Pressable key={name} style={styles.tab} onPress={() => setTab(name)}>
              <Text style={[styles.tabText, tab === name && styles.tabTextActive]}>{label}</Text>
            </Pressable>
          ))}
        </View>
      </>
    );
  }

  return (
    <SafeAreaProvider>
      <SafeAreaView style={common.screen}>
        {body}
        <StatusBar style="dark" />
      </SafeAreaView>
    </SafeAreaProvider>
  );
}

const styles = StyleSheet.create({
  center: { justifyContent: "center", alignItems: "center" },
  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingHorizontal: 16,
    paddingVertical: 12,
    backgroundColor: colors.card,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  brand: { fontSize: 20, fontWeight: "800", color: colors.primary },
  logout: { color: colors.muted, fontSize: 14 },
  tabs: {
    flexDirection: "row",
    backgroundColor: colors.card,
    borderTopWidth: 1,
    borderTopColor: colors.border,
  },
  tab: { flex: 1, alignItems: "center", paddingVertical: 14 },
  tabText: { fontSize: 15, color: colors.muted, fontWeight: "600" },
  tabTextActive: { color: colors.primary },
});
