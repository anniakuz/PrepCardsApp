import { useEffect, useRef, useState } from "react";
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from "react-native";
import { LEVEL_LABELS, request } from "./api";
import { colors, common } from "./theme";

export function Button({ title, onPress, secondary, disabled }) {
  return (
    <Pressable style={[secondary ? common.buttonSecondary : common.button, disabled && common.disabled]} onPress={onPress} disabled={disabled}>
      <Text style={secondary ? common.buttonSecondaryText : common.buttonText}>{title}</Text>
    </Pressable>
  );
}

export function LevelTag({ level, prefix = "Nivel" }) {
  if (!level) return null;
  return <Text style={[common.badge, styles.level]}>{prefix} {level} · {LEVEL_LABELS[level]}</Text>;
}

export function Loading() {
  return (
    <View style={[common.screen, { justifyContent: "center", alignItems: "center" }]}>
      <ActivityIndicator color={colors.primary} />
    </View>
  );
}

/** Chatbot con Claude para dudas sobre una pregunta, con límite diario. */
export function Assistant({ questionId }) {
  const [messages, setMessages] = useState([]);
  const [usage, setUsage] = useState(null);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    request(`/questions/${questionId}/assistant/`)
      .then((data) => {
        setMessages(data.messages);
        setUsage(data);
      })
      .catch((err) => setError(err.message));
  }, [questionId]);

  async function send() {
    const value = text.trim();
    if (!value || busy) return;
    setBusy(true);
    setError("");
    setMessages((m) => [...m, { id: `t${Date.now()}`, role: "user", text: value }]);
    setText("");
    try {
      const data = await request(`/questions/${questionId}/assistant/`, { method: "POST", body: { text: value } });
      setMessages((m) => [...m, data.message]);
      setUsage(data);
    } catch (err) {
      setError(err.message);
      setMessages((m) => m.slice(0, -1));
      setText(value);
    } finally {
      setBusy(false);
    }
  }

  return (
    <View style={[common.card, styles.panel]}>
      <Text style={styles.panelTitle}>Chatbot {usage ? `· hoy ${usage.remaining_today}/${usage.limit} · semana ${usage.remaining_week}/${usage.weekly_limit}` : ""}</Text>
      {messages.length === 0 && <Text style={common.subtitle}>Pregunta lo que no entiendas.</Text>}
      {messages.map((m) => (
        <Text key={m.id} style={[styles.bubble, m.role === "user" ? styles.mine : styles.theirs]}>{m.text}</Text>
      ))}
      {busy && <Text style={common.subtitle}>Escribiendo</Text>}
      {error ? <Text style={common.error}>{error}</Text> : null}
      <TextInput style={common.input} placeholder="Escribe tu duda" value={text} onChangeText={setText} maxLength={1000} onSubmitEditing={send} />
      <Button title="Enviar" onPress={send} disabled={busy || !text.trim()} />
    </View>
  );
}

/** Envía la pregunta al chat de uno de los mentores del estudiante. */
export function SendToMentor({ questionId }) {
  const [mentors, setMentors] = useState(null);
  const [message, setMessage] = useState("");

  useEffect(() => {
    request("/enrollments/").then((data) => setMentors(data.filter((e) => e.status === "active" && e.as_role === "student")));
  }, []);

  async function send(enrollment) {
    setMessage("");
    try {
      await request(`/enrollments/${enrollment.id}/messages/`, { method: "POST", body: { question: questionId } });
      setMessage(`Enviada a ${enrollment.mentor.username}`);
    } catch (err) {
      setMessage(err.message);
    }
  }

  return (
    <View style={[common.card, styles.panel]}>
      <Text style={styles.panelTitle}>Enviar a mi mentor</Text>
      {mentors === null ? <ActivityIndicator color={colors.primary} /> : null}
      {mentors && mentors.length === 0 && <Text style={common.subtitle}>Todavía no tienes mentores. Pídelos desde la web.</Text>}
      {(mentors || []).map((e) => (
        <Button key={e.id} secondary title={e.mentor.username} onPress={() => send(e)} />
      ))}
      {message ? <Text style={common.subtitle}>{message}</Text> : null}
    </View>
  );
}

/** Acciones de una pregunta. Guardar, chatbot y enviar al mentor. */
export function QuestionTools({ question }) {
  const [saved, setSaved] = useState(question.saved);
  const [panel, setPanel] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    setSaved(question.saved);
    setPanel(null);
    setError("");
  }, [question.id]);

  async function toggleSave() {
    try {
      if (saved) await request(`/saved/${question.id}/`, { method: "DELETE" });
      else await request("/saved/", { method: "POST", body: { question: question.id } });
      setSaved(!saved);
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <View style={{ gap: 8 }}>
      <View style={common.row}>
        <View style={{ flex: 1 }}><Button secondary title={saved ? "Guardada" : "Guardar"} onPress={toggleSave} /></View>
        <View style={{ flex: 1 }}><Button secondary title="Chatbot" onPress={() => setPanel(panel === "bot" ? null : "bot")} /></View>
        <View style={{ flex: 1 }}><Button secondary title="Mentor" onPress={() => setPanel(panel === "mentor" ? null : "mentor")} /></View>
      </View>
      {error ? <Text style={common.error}>{error}</Text> : null}
      {panel === "bot" && <Assistant questionId={question.id} />}
      {panel === "mentor" && <SendToMentor questionId={question.id} />}
    </View>
  );
}

export { ScrollView };

const styles = StyleSheet.create({
  level: { backgroundColor: colors.primarySoft, color: colors.primary },
  panel: { backgroundColor: colors.primarySoft, borderColor: "#c7d2fe" },
  panelTitle: { fontWeight: "700", color: colors.primary },
  bubble: { padding: 10, borderRadius: 12, fontSize: 14, overflow: "hidden", maxWidth: "90%" },
  mine: { alignSelf: "flex-end", backgroundColor: colors.primary, color: "#fff" },
  theirs: { alignSelf: "flex-start", backgroundColor: "#fff", color: colors.text },
});
