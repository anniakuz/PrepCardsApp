import { useState } from "react";
import { KeyboardAvoidingView, Platform, Pressable, StyleSheet, Text, TextInput, View } from "react-native";
import { login } from "../api";
import { colors, common } from "../theme";

export default function LoginScreen({ onLogin }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit() {
    setError("");
    setBusy(true);
    try {
      await login(username.trim(), password);
      await onLogin();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  const disabled = busy || !username.trim() || !password;

  return (
    <KeyboardAvoidingView
      style={[common.screen, styles.center]}
      behavior={Platform.OS === "ios" ? "padding" : undefined}
    >
      <View style={[common.card, styles.form]}>
        <Text style={styles.brand}>PrepCards</Text>
        <Text style={common.subtitle}>Practica preguntas de entrevista técnica</Text>
        <TextInput
          style={common.input}
          placeholder="Usuario"
          autoCapitalize="none"
          autoCorrect={false}
          value={username}
          onChangeText={setUsername}
        />
        <TextInput
          style={common.input}
          placeholder="Contraseña"
          secureTextEntry
          value={password}
          onChangeText={setPassword}
          onSubmitEditing={submit}
        />
        {error ? <Text style={common.error}>{error}</Text> : null}
        <Pressable style={[common.button, disabled && common.disabled]} onPress={submit} disabled={disabled}>
          <Text style={common.buttonText}>{busy ? "Entrando" : "Entrar"}</Text>
        </Pressable>
        <Text style={[common.subtitle, styles.note]}>El registro se hace desde la versión web.</Text>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  center: { justifyContent: "center", padding: 20 },
  form: { gap: 12 },
  brand: { fontSize: 28, fontWeight: "800", color: colors.primary },
  note: { textAlign: "center", fontSize: 12 },
});
