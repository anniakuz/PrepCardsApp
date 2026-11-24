import { useEffect, useRef, useState } from "react";
import { FlatList, KeyboardAvoidingView, Platform, Pressable, StyleSheet, Text, TextInput, View } from "react-native";
import { chatUrl, request } from "../api";
import { Button } from "../components";
import { colors, common } from "../theme";

export default function ChatScreen({ chat, userId, onExit }) {
  const [messages, setMessages] = useState([]);
  const [text, setText] = useState("");
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState("");
  const socket = useRef(null);
  const other = chat.as_role === "mentor" ? chat.student.username : chat.mentor.username;

  useEffect(() => {
    let closed = false;
    let retry = null;
    const append = (m) => setMessages((cur) => (cur.some((x) => x.id === m.id) ? cur : [...cur, m]));
    request(`/enrollments/${chat.id}/messages/`).then(setMessages).catch((err) => setError(err.message));

    async function connect() {
      try {
        const ws = new WebSocket(await chatUrl(chat.id));
        socket.current = ws;
        ws.onopen = () => setConnected(true);
        ws.onmessage = (event) => append(JSON.parse(event.data));
        ws.onclose = () => {
          setConnected(false);
          if (!closed) retry = setTimeout(connect, 3000);
        };
      } catch {
        if (!closed) retry = setTimeout(connect, 3000);
      }
    }
    connect();
    return () => {
      closed = true;
      clearTimeout(retry);
      socket.current?.close();
    };
  }, [chat.id]);

  async function send() {
    const value = text.trim();
    if (!value) return;
    setError("");
    if (socket.current?.readyState === 1) {
      socket.current.send(JSON.stringify({ text: value }));
    } else {
      try {
        const message = await request(`/enrollments/${chat.id}/messages/`, { method: "POST", body: { text: value } });
        setMessages((cur) => [...cur, message]);
      } catch (err) {
        setError(err.message);
        return;
      }
    }
    setText("");
  }

  return (
    <KeyboardAvoidingView style={common.screen} behavior={Platform.OS === "ios" ? "padding" : undefined}>
      <View style={styles.header}>
        <Pressable onPress={onExit}><Text style={styles.back}>Volver</Text></Pressable>
        <Text style={styles.title}>{other}</Text>
        <Text style={{ color: connected ? colors.green : colors.muted, fontSize: 12 }}>{connected ? "En línea" : "Conectando"}</Text>
      </View>
      <FlatList
        data={messages}
        keyExtractor={(m) => String(m.id)}
        contentContainerStyle={{ padding: 12, gap: 8 }}
        renderItem={({ item }) => (
          <View style={[styles.bubble, item.sender === userId ? styles.mine : styles.theirs]}>
            {item.text ? <Text style={{ color: item.sender === userId ? "#fff" : colors.text }}>{item.text}</Text> : null}
            {item.question ? <Text style={styles.attach}>Pregunta. {item.question.text}</Text> : null}
            {item.topic ? <Text style={styles.attach}>Tema privado. {item.topic.name}</Text> : null}
          </View>
        )}
      />
      {error ? <Text style={[common.error, { paddingHorizontal: 12 }]}>{error}</Text> : null}
      <View style={styles.compose}>
        <TextInput style={[common.input, { flex: 1 }]} placeholder="Mensaje" value={text} onChangeText={setText} onSubmitEditing={send} />
        <Button title="Enviar" onPress={send} />
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  header: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", padding: 12, backgroundColor: colors.card, borderBottomWidth: 1, borderBottomColor: colors.border },
  back: { color: colors.primary, fontWeight: "600" },
  title: { fontWeight: "700", fontSize: 16, color: colors.text },
  bubble: { maxWidth: "85%", padding: 10, borderRadius: 14, gap: 6 },
  mine: { alignSelf: "flex-end", backgroundColor: colors.primary },
  theirs: { alignSelf: "flex-start", backgroundColor: colors.card, borderWidth: 1, borderColor: colors.border },
  attach: { backgroundColor: "#fff", color: colors.text, padding: 8, borderRadius: 8, overflow: "hidden", fontSize: 13 },
  compose: { flexDirection: "row", gap: 8, padding: 12, backgroundColor: colors.card, borderTopWidth: 1, borderTopColor: colors.border },
});
