import { useEffect, useState } from "react";
import { Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { LEVEL_LABELS, request } from "../api";
import { Button, LevelTag, Loading, QuestionTools } from "../components";
import { colors, common } from "../theme";

export default function PracticeScreen({ topic, onExit }) {
  const [info, setInfo] = useState(null);
  const [level, setLevel] = useState(2);
  const [fixed, setFixed] = useState(false);
  const [resumable, setResumable] = useState(null);
  const [round, setRound] = useState(null);
  const [selected, setSelected] = useState(null);
  const [feedback, setFeedback] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    (async () => {
      try {
        const [t, l] = await Promise.all([request(`/topics/${topic.id}/`), request(`/topics/${topic.id}/level/`)]);
        setInfo(t);
        setLevel(l.level);
        setFixed(l.fixed);
        setResumable(await request(`/topics/${topic.id}/active-round/`).catch(() => null));
      } catch (err) {
        setError(err.message);
      }
    })();
  }, [topic.id]);

  async function start(resume) {
    setError("");
    try {
      if (resume) setRound(resumable);
      else {
        setRound(await request("/rounds/", { method: "POST", body: { topic: topic.id, ...(info.uses_levels && !fixed ? { level } : {}) } }));
        setFixed(true);
      }
      setSelected(null);
      setFeedback(null);
    } catch (err) {
      setError(err.message);
    }
  }

  async function answer(choiceId) {
    if (busy || feedback) return;
    setSelected(choiceId);
    setBusy(true);
    try {
      const data = await request(`/rounds/${round.id}/answer/`, { method: "POST", body: { choice: choiceId } });
      setFeedback({ ...data, chosen: choiceId });
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  if (!info) {
    return error ? (
      <View style={[common.screen, common.content]}>
        <Text style={common.error}>{error}</Text>
        <Button secondary title="Volver" onPress={onExit} />
      </View>
    ) : <Loading />;
  }

  if (!round) {
    return (
      <ScrollView style={common.screen} contentContainerStyle={common.content}>
        <Pressable onPress={onExit}><Text style={styles.back}>Volver</Text></Pressable>
        <Text style={common.title}>{info.label}</Text>
        <Text style={common.subtitle}>
          Una ronda tiene al menos 20 preguntas.{info.uses_levels ? " Cinco aciertos seguidos suben de nivel y tres fallos seguidos bajan." : ""}
        </Text>
        {info.uses_levels && fixed && (
          <View style={common.card}>
            <Text style={styles.label}>Tu nivel actual: {level} · {LEVEL_LABELS[level]}</Text>
            <Text style={common.subtitle}>El nivel de partida ya está fijado y solo cambia al responder.</Text>
          </View>
        )}
        {info.uses_levels && !fixed && (
          <View style={common.card}>
            <Text style={styles.label}>Nivel con el que empiezas. Después quedará fijado</Text>
            {[1, 2, 3, 4, 5].map((n) => (
              <Pressable key={n} style={[styles.choice, level === n && styles.choiceSelected]} onPress={() => setLevel(n)}>
                <Text style={styles.choiceText}>{n} · {LEVEL_LABELS[n]}</Text>
              </Pressable>
            ))}
          </View>
        )}
        {error ? <Text style={common.error}>{error}</Text> : null}
        <Button title="Empezar ronda nueva" onPress={() => start(false)} />
        {resumable && <Button secondary title={`Continuar ronda (${resumable.answered}/${resumable.size})`} onPress={() => start(true)} />}
      </ScrollView>
    );
  }

  if (round.status !== "active" && !feedback) {
    return (
      <ScrollView style={common.screen} contentContainerStyle={common.content}>
        <View style={common.card}>
          <Text style={common.title}>Ronda terminada</Text>
          <Text style={styles.score}>{round.correct} / {round.answered}</Text>
          {round.uses_levels && <LevelTag level={round.level} prefix="Tu nivel ahora" />}
        </View>
        <Button title="Otra ronda" onPress={() => { setRound(null); setResumable(null); request(`/topics/${topic.id}/level/`).then((l) => setLevel(l.level)); }} />
        <Button secondary title="Volver a mis temas" onPress={onExit} />
      </ScrollView>
    );
  }

  const question = round.question;
  const current = feedback ? feedback.round : round;
  const finished = feedback && feedback.round.status !== "active";

  return (
    <ScrollView style={common.screen} contentContainerStyle={common.content}>
      <View style={common.row}>
        <Pressable onPress={onExit}><Text style={styles.back}>Salir</Text></Pressable>
        <Text style={common.subtitle}>Pregunta {round.answered + 1} de {round.size}</Text>
      </View>
      <View style={common.row}>
        <LevelTag level={question.level} prefix="Pregunta. Nivel" />
        {round.uses_levels && <LevelTag level={current.level} prefix="Tu nivel" />}
      </View>
      <View style={common.card}>
        <Text style={styles.question}>{question.text}</Text>
      </View>
      {question.choices.map((choice) => {
        let style = null;
        if (feedback) {
          if (choice.id === feedback.correct_choice) style = styles.choiceRight;
          else if (choice.id === feedback.chosen) style = styles.choiceWrong;
        } else if (selected === choice.id) style = styles.choiceSelected;
        return (
          <Pressable key={choice.id} style={[styles.choice, style]} disabled={Boolean(feedback) || busy} onPress={() => answer(choice.id)}>
            <Text style={styles.choiceText}>{choice.text}</Text>
          </Pressable>
        );
      })}
      {error ? <Text style={common.error}>{error}</Text> : null}
      {!feedback ? (
        <Text style={common.subtitle}>Toca una opción para responder.</Text>
      ) : (
        <View style={{ gap: 8 }}>
          <Text style={[styles.verdict, { color: feedback.correct ? colors.green : colors.red }]}>{feedback.correct ? "Correcto" : "Incorrecto"}</Text>
          {feedback.level_change === "up" && <Text style={styles.up}>Subes al nivel {feedback.round.level}. Cinco aciertos seguidos.</Text>}
          {feedback.level_change === "down" && <Text style={styles.down}>Bajas al nivel {feedback.round.level}. Tres fallos seguidos.</Text>}
          {feedback.explanation ? <Text style={common.subtitle}>{feedback.explanation}</Text> : null}
          <Button title={finished ? "Ver resultado" : "Siguiente"} onPress={() => { setRound(feedback.round); setFeedback(null); setSelected(null); }} />
        </View>
      )}
      <QuestionTools question={question} />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  back: { color: colors.primary, fontWeight: "600", fontSize: 15 },
  label: { fontWeight: "700", color: colors.text },
  score: { fontSize: 40, fontWeight: "800", color: colors.text },
  question: { fontSize: 18, fontWeight: "600", color: colors.text },
  choice: { backgroundColor: colors.card, borderWidth: 1, borderColor: colors.border, borderRadius: 12, padding: 14 },
  choiceSelected: { borderColor: colors.primary, backgroundColor: colors.primarySoft },
  choiceRight: { borderColor: "#22c55e", backgroundColor: colors.greenSoft },
  choiceWrong: { borderColor: "#ef4444", backgroundColor: colors.redSoft },
  choiceText: { fontSize: 16, color: colors.text },
  verdict: { fontSize: 18, fontWeight: "700" },
  up: { color: colors.green, backgroundColor: colors.greenSoft, padding: 10, borderRadius: 10, overflow: "hidden" },
  down: { color: colors.amber, backgroundColor: "#fffbeb", padding: 10, borderRadius: 10, overflow: "hidden" },
});
