/**
 * SafeErrorBoundary — local, non-fatal error boundary.
 *
 * Wraps a subtree so a render-phase crash renders an inline error card
 * with the exact message + stack instead of blowing the whole screen
 * to Expo Router's generic "Something went wrong" boundary. Designed
 * for Health tab / integration cards where testers need to read the
 * failure text directly.
 */
import { Component, type ReactNode } from 'react';
import { StyleSheet } from 'react-native';
import { Text, View } from '@/components/Themed';

interface Props {
  label: string;
  children: ReactNode;
}

interface State {
  error: Error | null;
}

export class SafeErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: unknown): void {
    // eslint-disable-next-line no-console
    console.error(`[SafeErrorBoundary:${this.props.label}]`, error, info);
  }

  render(): ReactNode {
    if (this.state.error) {
      const msg = this.state.error.message || String(this.state.error);
      const stack = this.state.error.stack ?? '';
      return (
        <View style={styles.card}>
          <Text style={styles.title}>
            {this.props.label} failed to render
          </Text>
          <Text style={styles.msg}>{msg}</Text>
          {stack && (
            <Text style={styles.stack} numberOfLines={10}>
              {stack.split('\n').slice(0, 8).join('\n')}
            </Text>
          )}
          <Text style={styles.hint}>
            Everything below this card still works. Paste the message line into Tester feedback.
          </Text>
        </View>
      );
    }
    return this.props.children;
  }
}

const styles = StyleSheet.create({
  card: {
    padding: 14,
    borderRadius: 12,
    backgroundColor: 'rgba(255,107,107,0.08)',
    borderWidth: 1,
    borderColor: '#ff6b6b',
    gap: 6,
  },
  title: { fontSize: 14, fontWeight: '700', color: '#ff6b6b' },
  msg: { fontSize: 13, fontFamily: 'SpaceMono', color: '#ff6b6b' },
  stack: { fontSize: 10, opacity: 0.55, fontFamily: 'SpaceMono' },
  hint: { fontSize: 11, opacity: 0.55 },
});
