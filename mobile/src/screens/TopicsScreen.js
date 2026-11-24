import { useEffect, useState } from "react";
import { Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { request } from "../api";
import { Button, LevelTag, Loading } from "../components";
import { colors, common } from "../theme";

export default function TopicsScreen({ onPractice, onChat }) {
  const [topics, setTopics] = useState(null);
  const [chats, setChats] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => {
    (async () => {
      try {
        setTopics(await request("/topics/mine/"));
        const enrollments = await request("/enrollments/");
        setChats(enrollments.filter((e) => e.status === "active"));
      } catch (err) {
        setError(err.message);
      }
    })();
  }, []);

  if (!topics) return error ? <Text style={[common.error, { padding: 16 }]}>{error}</Text> : <Loading />;
  return (
    <ScrollView style={common.screen} contentContainerStyle={common.content}>
      <Text style={common.title}>Mis temas</Text>
      {topics.length === 0 && <Text style={common.subtitle}>Todavía no tienes temas. Añádelos desde la versión web.</Text>}
      {topics.map((topic) => (
        <View key={topic.id} style={common.card}>
          <Text style={styles.name}>{topic.label}</Text>
          <View style={common.row}>
            <Text style={common.subtitle}>{topic.question_count} preguntas</Text>
            <LevelTag level={topic.level} />
          </View>
          <Button title="Practicar" onPress={() => onPractice(topic)} />
        </View>
      ))}
      <Text style={[common.title, { marginTop: 8 }]}>Chats con mentores</Text>
      {chats.length === 0 && <Text style={common.subtitle}>No tienes mentorías activas.</Text>}
      {chats.map((chat) => (
        <Pressable key={chat.id} style={common.card} onPress={() => onChat(chat)}>
          <Text style={styles.name}>{chat.as_role === "mentor" ? chat.student.username : chat.mentor.username}</Text>
          <Text style={{ color: colors.primary }}>Abrir chat</Text>
        </Pressable>
      ))}
    </ScrollView>
  );
}

const styles = StyleSheet.create({ name: { fontSize: 17, fontWeight: "700", color: colors.text } });
