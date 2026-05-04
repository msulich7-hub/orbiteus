"use client";

import { useState } from "react";
import {
  Anchor,
  Box,
  Button,
  Card,
  Container,
  Group,
  Stack,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import { api } from "@/lib/api";

/**
 * Public password-reset request page (DoD §3.4).
 *
 * The endpoint always returns 200 — we therefore always show the same
 * confirmation copy, regardless of whether the email exists, to avoid
 * leaking enumeration data through the UI.
 */
export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await api.post("/auth/password/request", { email });
      setSubmitted(true);
    } catch (err: unknown) {
      // Even on transient failure we keep the same message.
      setSubmitted(true);
      if (err instanceof Error) {
        console.warn("password.request.transient_error", err.message);
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <Box bg="gray.0" mih="100vh" w="100%">
      <Container size="sm" py="xl">
        <Card shadow="sm" padding="xl" radius="md" withBorder>
          <Stack gap="md">
            <Title order={2}>Reset your password</Title>
            {submitted ? (
              <Stack gap="sm">
                <Text>
                  If an account exists for that address, an email is on its
                  way with a link to reset the password. The link expires in
                  30 minutes.
                </Text>
                <Text size="sm" c="dimmed">
                  Didn’t receive anything? Check your spam folder, then
                  request again in a minute.
                </Text>
                <Group>
                  <Anchor href="/login" size="sm">
                    Back to sign in
                  </Anchor>
                </Group>
              </Stack>
            ) : (
              <form onSubmit={handleSubmit}>
                <Stack gap="sm">
                  <Text>
                    Enter the email associated with your Orbiteus account.
                    We’ll send you a link to set a new password.
                  </Text>
                  <TextInput
                    label="Email"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    autoFocus
                  />
                  {error ? (
                    <Text c="red" size="sm">
                      {error}
                    </Text>
                  ) : null}
                  <Group justify="space-between" mt="xs">
                    <Anchor href="/login" size="sm" c="dark">
                      Back to sign in
                    </Anchor>
                    <Button type="submit" loading={loading} color="dark">
                      Send reset link
                    </Button>
                  </Group>
                </Stack>
              </form>
            )}
          </Stack>
        </Card>
      </Container>
    </Box>
  );
}
