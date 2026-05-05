import React, { useMemo, useState } from 'react';
import {
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Switch,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from 'react-native';
import { StatusBar } from 'expo-status-bar';

import { login, register, solve } from './src/api';

function Button({ title, onPress, disabled }) {
  return (
    <TouchableOpacity style={[styles.button, disabled && styles.buttonDisabled]} onPress={onPress} disabled={disabled}>
      <Text style={styles.buttonText}>{title}</Text>
    </TouchableOpacity>
  );
}

export default function App() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [inCompanyClass, setInCompanyClass] = useState(false);
  const [token, setToken] = useState('');
  const [entitlement, setEntitlement] = useState(null);

  const [question, setQuestion] = useState('');
  const [grade, setGrade] = useState('高一');
  const [answer, setAnswer] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const loggedIn = Boolean(token);

  const entitlementText = useMemo(() => {
    if (!entitlement) return '尚未登入';
    if (entitlement.plan === 'company_student_free') {
      return '方案：公司學生免費使用';
    }

    if (entitlement.is_active) {
      return `方案：一般試用（剩餘 ${entitlement.days_left} 天）`;
    }

    return `方案已失效：${entitlement.reason}`;
  }, [entitlement]);

  async function handleRegister() {
    setLoading(true);
    setError('');
    try {
      const data = await register({ email, password, name, in_company_class: inCompanyClass });
      setToken(data.token);
      setEntitlement(data.entitlement);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleLogin() {
    setLoading(true);
    setError('');
    try {
      const data = await login({ email, password });
      setToken(data.token);
      setEntitlement(data.entitlement);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleSolve() {
    setLoading(true);
    setError('');
    setAnswer('');
    try {
      const data = await solve(token, { question, grade });
      setAnswer(data.answer);
      setEntitlement(data.entitlement);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar style="dark" />
      <ScrollView contentContainerStyle={styles.content}>
        <Text style={styles.title}>AI 解題助教</Text>
        <Text style={styles.subtitle}>{entitlementText}</Text>

        <View style={styles.card}>
          <Text style={styles.sectionTitle}>1. 註冊 / 登入</Text>

          <TextInput style={styles.input} placeholder="姓名（註冊用）" value={name} onChangeText={setName} />
          <TextInput style={styles.input} placeholder="Email" autoCapitalize="none" value={email} onChangeText={setEmail} />
          <TextInput style={styles.input} placeholder="密碼" secureTextEntry value={password} onChangeText={setPassword} />

          <View style={styles.switchRow}>
            <Text style={styles.switchText}>是否為公司上課學生</Text>
            <Switch value={inCompanyClass} onValueChange={setInCompanyClass} />
          </View>

          <View style={styles.buttonRow}>
            <Button title="註冊" onPress={handleRegister} disabled={loading} />
            <Button title="登入" onPress={handleLogin} disabled={loading} />
          </View>
        </View>

        <View style={styles.card}>
          <Text style={styles.sectionTitle}>2. AI 解題</Text>
          <TextInput style={styles.input} placeholder="年級（例：高一）" value={grade} onChangeText={setGrade} />
          <TextInput
            style={[styles.input, styles.textArea]}
            placeholder="輸入你的題目..."
            multiline
            value={question}
            onChangeText={setQuestion}
          />
          <Button title={loggedIn ? '送出題目' : '請先登入'} onPress={handleSolve} disabled={loading || !loggedIn} />
        </View>

        {error ? (
          <View style={[styles.card, styles.errorCard]}>
            <Text style={styles.errorText}>{error}</Text>
          </View>
        ) : null}

        {answer ? (
          <View style={styles.card}>
            <Text style={styles.sectionTitle}>解題結果</Text>
            <Text style={styles.answerText}>{answer}</Text>
          </View>
        ) : null}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f8fafc',
  },
  content: {
    padding: 16,
    gap: 14,
  },
  title: {
    fontSize: 28,
    fontWeight: '700',
    color: '#0f172a',
  },
  subtitle: {
    fontSize: 14,
    color: '#334155',
  },
  card: {
    backgroundColor: '#ffffff',
    borderRadius: 12,
    padding: 14,
    gap: 10,
    shadowColor: '#0f172a',
    shadowOpacity: 0.06,
    shadowRadius: 8,
    elevation: 1,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#0f172a',
  },
  input: {
    borderWidth: 1,
    borderColor: '#cbd5e1',
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 10,
    backgroundColor: '#ffffff',
  },
  textArea: {
    minHeight: 120,
    textAlignVertical: 'top',
  },
  switchRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  switchText: {
    color: '#1e293b',
  },
  buttonRow: {
    flexDirection: 'row',
    gap: 10,
  },
  button: {
    flex: 1,
    backgroundColor: '#2563eb',
    borderRadius: 8,
    paddingVertical: 10,
    alignItems: 'center',
  },
  buttonDisabled: {
    opacity: 0.6,
  },
  buttonText: {
    color: '#ffffff',
    fontWeight: '600',
  },
  errorCard: {
    borderWidth: 1,
    borderColor: '#fca5a5',
    backgroundColor: '#fef2f2',
  },
  errorText: {
    color: '#b91c1c',
  },
  answerText: {
    color: '#1e293b',
    lineHeight: 21,
  },
});
